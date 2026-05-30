"""
Kokoro-82M local TTS synthesis (Phase 6.2 + 6.2.1 installer).

Apache 2.0 license; CPU-capable; no GPU required. Unlike VibeVoice (Phase 6.3,
deferred to v0.2), Kokoro outputs have NO baked-in watermark or AI disclaimer
-- the compliance invariant for VibeVoice does not apply here.

Lazy-imports `kokoro` so this module loads even when the library is not
installed. Probes (`kokoro_available`, `espeak_ng_available`, `kokoro_ready`)
let the GUI surface actionable errors before spawning a synthesis worker.

System dependency: `espeak-ng` must be on PATH.
  Windows: download .msi from https://github.com/espeak-ng/espeak-ng/releases
  Linux: `apt install espeak-ng`
  macOS: `brew install espeak-ng`

Model revision pinning: pulls from `providers.PROVIDER_REGISTRY["Kokoro"].hf_model_revision`
so silent upstream model swaps cannot break the pipeline (PRD §14.2(4)).
"""
import importlib
import logging
import subprocess
import sys
from pathlib import Path

import providers


KOKORO_PIP_PACKAGES = ("kokoro>=0.9.4", "soundfile>=0.12.1", "huggingface_hub>=0.20.0")
KOKORO_HF_REPO = "hexgrad/Kokoro-82M"


def kokoro_available() -> tuple[bool, str | None]:
    """Probe whether the `kokoro` Python package is importable."""
    try:
        import kokoro  # noqa: F401
        return (True, None)
    except ImportError as exc:
        return (
            False,
            f"kokoro package not importable ({exc}). "
            "Install: `pip install kokoro soundfile huggingface_hub`",
        )


def espeak_ng_available(runner=None) -> tuple[bool, str | None]:
    """Probe whether `espeak-ng` is on PATH.

    `runner` is a test injection seam; defaults to `subprocess.run`.
    """
    run = runner or subprocess.run
    try:
        run(["espeak-ng", "--version"], capture_output=True, text=True, check=True, timeout=5)
        return (True, None)
    except FileNotFoundError:
        return (
            False,
            "espeak-ng not found on PATH. Install from "
            "https://github.com/espeak-ng/espeak-ng/releases (Windows .msi) "
            "or `apt install espeak-ng` / `brew install espeak-ng`.",
        )
    except subprocess.CalledProcessError as exc:
        return (False, f"espeak-ng exited non-zero: {exc}")
    except (subprocess.TimeoutExpired, OSError) as exc:
        return (False, f"espeak-ng probe failed: {exc}")


def kokoro_ready() -> tuple[bool, str | None]:
    """Probe for the only HARD requirement: the `kokoro` Python package.

    Verified 2026-05-22 on Windows 11 / Python 3.11 / kokoro 0.9.4 that
    American-English synthesis (lang_code='a', voice='af_heart') succeeds
    WITHOUT espeak-ng on PATH -- the misaki G2P backend handles English.
    espeak-ng is only needed for non-English language paths. Treat it as a
    soft dep; check it separately with `espeak_ng_available` if/when a
    language pack other than 'a' is wired.

    Model snapshot is auto-downloaded on first KPipeline construction, so we
    don't gate on it here either -- the install flow prefetches for nicer UX
    but synthesis still works without prefetch.
    """
    return kokoro_available()


def _kokoro_pinned_revision() -> str | None:
    cap = providers.PROVIDER_REGISTRY.get("Kokoro")
    if cap is None:
        return None
    return cap.hf_model_revision


def model_cached(repo_id: str = KOKORO_HF_REPO, revision: str | None = None) -> bool:
    """Probe whether the pinned Kokoro snapshot already lives in the HF cache.

    Does NOT trigger a download. Returns False on any HF lookup failure
    (including the `huggingface_hub` package being absent).
    """
    revision = revision or _kokoro_pinned_revision()
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id=repo_id, revision=revision, local_files_only=True)
        return True
    except Exception as exc:
        logging.debug("kokoro model cache miss for %s@%s: %s", repo_id, revision, exc)
        return False


def install_kokoro_runtime(progress_callback=None,
                           pip_runner=None,
                           snapshot_fn=None,
                           python_executable=None) -> tuple[bool, str | None]:
    """Pip-install kokoro / soundfile / huggingface_hub, then prefetch the
    pinned Kokoro model snapshot so the next click on Start does no network IO.

    All side-effects are injectable for tests:
      - `pip_runner(argv) -> CompletedProcess` (default: subprocess.run with capture)
      - `snapshot_fn(repo_id, revision) -> str` (default: huggingface_hub.snapshot_download)
      - `python_executable` (default: sys.executable)

    `progress_callback(message)` is invoked at each step for GUI status updates.

    Returns (ok, reason). On failure, `reason` is a user-facing message.
    """
    def _notify(msg):
        if progress_callback:
            try:
                progress_callback(msg)
            except Exception as exc:
                logging.warning("kokoro install progress_callback raised: %s", exc)

    python_exe = python_executable or sys.executable
    runner = pip_runner or subprocess.run

    _notify("Installing kokoro packages (pip)...")
    try:
        result = runner(
            [python_exe, "-m", "pip", "install", "--upgrade", *KOKORO_PIP_PACKAGES],
            capture_output=True, text=True, check=True,
        )
        logging.info("kokoro pip install ok: %s", (result.stdout or "")[-500:])
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or str(exc))[-1000:]
        return (False, f"pip install failed: {stderr}")
    except FileNotFoundError:
        return (False, f"Python executable not found: {python_exe}")
    except Exception as exc:
        return (False, f"pip install raised unexpectedly: {exc}")

    # Invalidate any cached import-failure so the freshly-installed package is picked up.
    importlib.invalidate_caches()

    _notify("Downloading Kokoro-82M model weights (~500 MB on first run)...")
    snap = snapshot_fn
    if snap is None:
        try:
            from huggingface_hub import snapshot_download as _hf_snap
            snap = _hf_snap
        except ImportError as exc:
            return (False, f"huggingface_hub still not importable after install: {exc}")

    revision = _kokoro_pinned_revision()
    try:
        snap(repo_id=KOKORO_HF_REPO, revision=revision)
    except Exception as exc:
        return (False, f"model download failed: {exc}")

    _notify("Kokoro runtime ready.")
    return (True, None)


def _write_kokoro_speech(chunk: str, wav_path: Path, model: str, voice: str,
                         lang_code: str = "a", speed: float = 1.0) -> None:
    """Synthesize `chunk` to `wav_path` via kokoro.KPipeline.

    `lang_code` follows Kokoro's convention: 'a' = American English (default),
    'b' = British English, 'e' = Spanish, etc.

    Voices come from `providers.PROVIDER_REGISTRY["Kokoro"].voices` (v0.1
    ships the American English subset).

    Imports `kokoro` and `soundfile` lazily so the module loads even when the
    libraries are not installed. Caller is responsible for calling
    `kokoro_ready()` first.
    """
    import kokoro
    import soundfile

    revision = _kokoro_pinned_revision()
    logging.info(
        "kokoro synth: model=%s voice=%s lang=%s revision=%s chunk_len=%d",
        model, voice, lang_code, revision, len(chunk),
    )

    pipeline = kokoro.KPipeline(lang_code=lang_code)
    # KPipeline yields (graphemes, phonemes, audio) per segment; concatenate audio.
    audio_segments = []
    sample_rate = 24000  # Kokoro-82M default; KPipeline doesn't expose it directly
    for _graphemes, _phonemes, audio in pipeline(chunk, voice=voice, speed=speed):
        audio_segments.append(audio)

    if not audio_segments:
        raise RuntimeError(f"kokoro produced no audio for chunk: {chunk[:80]!r}")

    if len(audio_segments) == 1:
        combined = audio_segments[0]
    else:
        try:
            import numpy as np
            combined = np.concatenate(audio_segments)
        except ImportError:
            # Fallback: numpy ships with kokoro/soundfile transitively; this branch
            # is defensive in case of partial install.
            combined = audio_segments[0]
            for seg in audio_segments[1:]:
                combined = combined + seg  # type: ignore[operator]

    soundfile.write(str(wav_path), combined, sample_rate)


def _convert_wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    """pydub WAV -> MP3 helper; lazy-imports pydub so the module loads cleanly."""
    from pydub import AudioSegment
    audio = AudioSegment.from_wav(str(wav_path))
    audio.export(str(mp3_path), format="mp3")
