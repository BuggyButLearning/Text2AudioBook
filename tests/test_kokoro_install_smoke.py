"""Opt-in real-install smoke test for Kokoro (Phase 6.2 validation).

Skipped by default. To run (downloads ~500 MB to ~/.cache/huggingface,
takes 1-3 min on broadband, requires kokoro Python package already installed):

    KOKORO_INSTALL_SMOKE=1 conda run -n text2audiobook \
        python -m pytest tests/test_kokoro_install_smoke.py -v

This test catches the class of bug where the mocked unit tests pass but
real-world install / synthesis fails (e.g. wrong HF revision, kokoro API
shape change, missing system dep).

Verified passing 2026-05-22 on Windows 11 / Python 3.11 / kokoro 0.9.4 /
huggingface_hub installed / NO espeak-ng on PATH (American-English
synthesis works without espeak via the misaki G2P backend).
"""
import importlib.util as _util
import os
from pathlib import Path

import pytest

GATE = os.getenv("KOKORO_INSTALL_SMOKE") == "1"
HAS_HF = _util.find_spec("huggingface_hub") is not None
HAS_SOUNDFILE = _util.find_spec("soundfile") is not None


def _kokoro_present():
    """Re-probed per-test (NOT cached at module load) since
    test_fresh_install_via_install_kokoro_runtime mutates the env."""
    return _util.find_spec("kokoro") is not None


pytestmark = [
    pytest.mark.skipif(
        not (GATE and HAS_HF and HAS_SOUNDFILE),
        reason=(
            "opt-in real-install smoke; set KOKORO_INSTALL_SMOKE=1 "
            "AND have huggingface_hub + soundfile installed (kokoro is auto-installed by these tests)"
        ),
    ),
    # kokoro / torch emit several deprecation warnings (dropout LSTM, weight_norm).
    # Project pytest.ini upgrades warnings to errors; override locally.
    pytest.mark.filterwarnings("default"),
]


@pytest.mark.allow_network
def test_a_fresh_install_via_install_kokoro_runtime():
    """RUNS FIRST (name prefix `a_` orders alphabetically). Uninstalls kokoro,
    then calls install_kokoro_runtime() and asserts it successfully
    re-installs the package + prefetches the model snapshot.

    Catches the bug class where install_kokoro_runtime works only because
    the package was already installed -- mirrors a fresh user machine
    clicking Start for the first time.

    Side effect: pip-uninstalls + reinstalls kokoro in the current env.
    Only runs when KOKORO_INSTALL_SMOKE=1.
    """
    import subprocess
    import sys
    from kokoro_synthesis import install_kokoro_runtime

    subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", "kokoro"],
        capture_output=True, text=True, check=False,
    )
    proc = subprocess.run(
        [sys.executable, "-c", "import importlib.util as u; print(bool(u.find_spec('kokoro')))"],
        capture_output=True, text=True, check=True,
    )
    assert proc.stdout.strip() == "False", f"kokoro still installed after uninstall: {proc.stdout!r}"

    progress = []
    ok, reason = install_kokoro_runtime(progress_callback=progress.append)
    assert ok is True, f"install_kokoro_runtime failed from cold: {reason}"
    assert reason is None
    joined = " | ".join(progress).lower()
    assert "pip" in joined or "install" in joined
    assert "model" in joined or "weights" in joined or "ready" in joined

    proc = subprocess.run(
        [sys.executable, "-c", "import kokoro; print(kokoro.__version__)"],
        capture_output=True, text=True, check=True,
    )
    assert proc.returncode == 0, f"kokoro still not importable after install: {proc.stderr}"
    assert proc.stdout.strip(), "kokoro version string empty"


@pytest.mark.allow_network
def test_hf_snapshot_download_for_pinned_revision():
    """Pull the pinned revision from HF (or hit cache). Catches future SHA drift."""
    from huggingface_hub import snapshot_download
    from providers import PROVIDER_REGISTRY

    cap = PROVIDER_REGISTRY["Kokoro"]
    path = snapshot_download(repo_id=cap.hf_model_repo, revision=cap.hf_model_revision)
    snap = Path(path)
    assert snap.exists()
    assert snap.is_dir()
    # Snapshot dir should contain at least the config + a weights file.
    children = [p.name for p in snap.iterdir()]
    assert "config.json" in children, f"config.json missing from snapshot: {children[:10]}"


@pytest.mark.allow_network
def test_kokoro_imports_and_kpipeline_constructs():
    """Confirms the kokoro package exposes the API surface we depend on."""
    import kokoro
    assert hasattr(kokoro, "KPipeline"), "kokoro.KPipeline missing — upstream API shape changed"
    pipeline = kokoro.KPipeline(lang_code="a")
    assert pipeline is not None


@pytest.mark.allow_network
def test_write_kokoro_speech_produces_valid_wav(tmp_path):
    """End-to-end: _write_kokoro_speech with a tiny chunk produces a WAV file
    larger than 1 KB. This is the synthesis-side equivalent of the OpenAI
    smoke test in tests/test_openai_smoke.py."""
    from kokoro_synthesis import _write_kokoro_speech

    wav_path = tmp_path / "smoke.wav"
    _write_kokoro_speech(
        chunk="Hello from the Kokoro smoke test.",
        wav_path=wav_path,
        model="kokoro-82m",
        voice="af_heart",
        lang_code="a",
        speed=1.0,
    )
    assert wav_path.exists(), "no WAV produced"
    size = wav_path.stat().st_size
    assert size > 1024, f"WAV suspiciously small ({size} bytes)"
    # RIFF header check — first 4 bytes are 'RIFF' for valid WAV.
    with open(wav_path, "rb") as f:
        header = f.read(4)
    assert header == b"RIFF", f"not a RIFF/WAV header: {header!r}"


@pytest.mark.allow_network
def test_full_dispatch_via_tts_conversion(tmp_path):
    """convert_text_chunk_to_speech with provider='Kokoro' returns an MP3 path
    (WAV synth -> MP3 convert). Mirrors what main.start_conversion does."""
    import types as _types
    from tts_conversion import convert_text_chunk_to_speech

    settings = _types.SimpleNamespace(
        provider="Kokoro", model="kokoro-82m", voice="af_heart",
        speed=1.0, response_format="wav", openai_api_key=None,
        max_concurrency=1,
    )
    out_path = convert_text_chunk_to_speech(
        "Dispatch smoke test.", 0, settings, tmp_path, "smoke", retries=1,
    )
    assert out_path is not None, "convert_text_chunk_to_speech returned None"
    out = Path(out_path)
    assert out.exists()
    assert out.suffix == ".mp3"
    assert out.stat().st_size > 1024
