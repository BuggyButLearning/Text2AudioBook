"""Phase 6.2 — Kokoro synthesis tests.

All tests use monkeypatch on the lazy-imported modules (kokoro, soundfile, pydub)
so the suite passes whether or not those packages are actually installed.
"""
import subprocess
import sys
import types
from pathlib import Path

import pytest

import kokoro_synthesis


class TestKokoroAvailable:
    def test_returns_true_when_import_succeeds(self, monkeypatch):
        # Inject a fake kokoro module into sys.modules so `import kokoro` resolves.
        fake_kokoro = types.ModuleType("kokoro")
        monkeypatch.setitem(sys.modules, "kokoro", fake_kokoro)
        ok, reason = kokoro_synthesis.kokoro_available()
        assert ok is True
        assert reason is None

    def test_returns_false_when_import_fails(self, monkeypatch):
        # Force ImportError on `import kokoro`.
        monkeypatch.setitem(sys.modules, "kokoro", None)
        ok, reason = kokoro_synthesis.kokoro_available()
        assert ok is False
        assert "pip install" in (reason or "")
        assert "kokoro" in (reason or "")


class TestEspeakNgAvailable:
    def test_returns_true_on_zero_exit(self):
        def fake_runner(*_a, **_kw):
            return types.SimpleNamespace(returncode=0, stdout="espeak-ng 1.51")
        ok, reason = kokoro_synthesis.espeak_ng_available(runner=fake_runner)
        assert ok is True
        assert reason is None

    def test_returns_false_when_binary_missing(self):
        def fake_runner(*_a, **_kw):
            raise FileNotFoundError("espeak-ng not found")
        ok, reason = kokoro_synthesis.espeak_ng_available(runner=fake_runner)
        assert ok is False
        assert "espeak-ng" in (reason or "")
        assert "Install" in (reason or "")

    def test_returns_false_on_nonzero_exit(self):
        def fake_runner(*_a, **_kw):
            raise subprocess.CalledProcessError(1, "espeak-ng")
        ok, reason = kokoro_synthesis.espeak_ng_available(runner=fake_runner)
        assert ok is False
        assert "non-zero" in (reason or "")

    def test_returns_false_on_timeout(self):
        def fake_runner(*_a, **_kw):
            raise subprocess.TimeoutExpired("espeak-ng", 5)
        ok, reason = kokoro_synthesis.espeak_ng_available(runner=fake_runner)
        assert ok is False
        assert "probe failed" in (reason or "")


class TestKokoroReady:
    """kokoro_ready() == kokoro_available() only. espeak-ng is NOT a hard
    blocker for American-English synthesis (verified 2026-05-22 on Windows
    against kokoro 0.9.4 — see kokoro_synthesis.kokoro_ready docstring)."""

    def test_returns_true_when_lib_available(self, monkeypatch):
        monkeypatch.setattr(kokoro_synthesis, "kokoro_available", lambda: (True, None))
        ok, reason = kokoro_synthesis.kokoro_ready()
        assert ok is True
        assert reason is None

    def test_returns_false_when_lib_missing(self, monkeypatch):
        monkeypatch.setattr(kokoro_synthesis, "kokoro_available", lambda: (False, "kokoro missing"))
        ok, reason = kokoro_synthesis.kokoro_ready()
        assert ok is False
        assert "kokoro missing" in reason

    def test_does_NOT_block_on_espeak(self, monkeypatch):
        """Regression guard: previous version blocked synth if espeak missing.
        Real-world verification proved English synth works without espeak."""
        monkeypatch.setattr(kokoro_synthesis, "kokoro_available", lambda: (True, None))
        # Even if espeak probe would say False, kokoro_ready must still be True.
        monkeypatch.setattr(kokoro_synthesis, "espeak_ng_available", lambda: (False, "espeak missing"))
        ok, reason = kokoro_synthesis.kokoro_ready()
        assert ok is True
        assert reason is None


class TestPinnedRevision:
    def test_pulls_revision_from_registry(self):
        import providers
        revision = kokoro_synthesis._kokoro_pinned_revision()
        assert revision == providers.PROVIDER_REGISTRY["Kokoro"].hf_model_revision
        assert revision is not None  # registry guarantees a pinned value


class TestWriteKokoroSpeech:
    def test_invokes_kokoro_pipeline_and_writes_wav(self, monkeypatch, tmp_path):
        # Fake kokoro module
        captured = {"pipeline_calls": [], "pipeline_args": [], "soundfile_calls": []}

        class FakePipeline:
            def __init__(self_inner, lang_code):
                captured["pipeline_calls"].append(lang_code)

            def __call__(self_inner, chunk, voice, speed):
                captured["pipeline_args"].append((chunk, voice, speed))
                # Yield one segment of "audio" (a list of floats stands in for ndarray)
                yield ("graphemes", "phonemes", [0.0, 0.1, 0.2, 0.3])

        fake_kokoro = types.ModuleType("kokoro")
        fake_kokoro.KPipeline = FakePipeline
        monkeypatch.setitem(sys.modules, "kokoro", fake_kokoro)

        fake_soundfile = types.ModuleType("soundfile")
        fake_soundfile.write = lambda path, audio, sr: captured["soundfile_calls"].append((path, list(audio), sr))
        monkeypatch.setitem(sys.modules, "soundfile", fake_soundfile)

        wav_path = tmp_path / "chunk.wav"
        kokoro_synthesis._write_kokoro_speech(
            chunk="Hello world.",
            wav_path=wav_path,
            model="kokoro-82m",
            voice="af_heart",
            lang_code="a",
            speed=1.0,
        )
        assert captured["pipeline_calls"] == ["a"]
        assert captured["pipeline_args"] == [("Hello world.", "af_heart", 1.0)]
        assert len(captured["soundfile_calls"]) == 1
        wpath, audio, sr = captured["soundfile_calls"][0]
        assert wpath == str(wav_path)
        assert audio == [0.0, 0.1, 0.2, 0.3]
        assert sr == 24000

    def test_raises_on_empty_audio(self, monkeypatch, tmp_path):
        class EmptyPipeline:
            def __init__(self_inner, lang_code): pass

            def __call__(self_inner, *_a, **_kw):
                return iter([])  # no segments

        fake_kokoro = types.ModuleType("kokoro")
        fake_kokoro.KPipeline = EmptyPipeline
        monkeypatch.setitem(sys.modules, "kokoro", fake_kokoro)
        monkeypatch.setitem(sys.modules, "soundfile", types.ModuleType("soundfile"))

        with pytest.raises(RuntimeError, match="produced no audio"):
            kokoro_synthesis._write_kokoro_speech(
                chunk="x", wav_path=tmp_path / "out.wav",
                model="kokoro-82m", voice="af_heart",
            )


class TestConvertWavToMp3:
    def test_invokes_pydub_export(self, monkeypatch, tmp_path):
        captured = {"from_wav": [], "export": []}

        class FakeAudio:
            def export(self_inner, path, format):
                captured["export"].append((path, format))

        fake_pydub = types.ModuleType("pydub")
        fake_pydub.AudioSegment = types.SimpleNamespace(
            from_wav=lambda p: (captured["from_wav"].append(p), FakeAudio())[1]
        )
        monkeypatch.setitem(sys.modules, "pydub", fake_pydub)

        wav = tmp_path / "x.wav"
        mp3 = tmp_path / "x.mp3"
        kokoro_synthesis._convert_wav_to_mp3(wav, mp3)
        assert captured["from_wav"] == [str(wav)]
        assert captured["export"] == [(str(mp3), "mp3")]


class TestModelCached:
    def test_returns_true_when_snapshot_present(self, monkeypatch):
        # Inject a fake huggingface_hub that succeeds on local_files_only=True.
        fake_hf = types.ModuleType("huggingface_hub")
        fake_hf.snapshot_download = lambda repo_id, revision, local_files_only: "/cache/path"
        monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hf)
        assert kokoro_synthesis.model_cached() is True

    def test_returns_false_when_snapshot_missing(self, monkeypatch):
        fake_hf = types.ModuleType("huggingface_hub")

        def _raise(*_a, **_kw):
            raise FileNotFoundError("not in cache")
        fake_hf.snapshot_download = _raise
        monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hf)
        assert kokoro_synthesis.model_cached() is False

    def test_returns_false_when_hf_lib_missing(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "huggingface_hub", None)
        assert kokoro_synthesis.model_cached() is False


class TestInstallKokoroRuntime:
    def test_success_path_invokes_pip_then_snapshot(self):
        captured = {"pip_argv": None, "snapshot_args": None, "progress": []}

        def fake_pip(argv, capture_output, text, check):
            captured["pip_argv"] = argv
            return types.SimpleNamespace(stdout="installed kokoro", returncode=0)

        def fake_snap(repo_id, revision):
            captured["snapshot_args"] = (repo_id, revision)
            return "/cache/snap"

        ok, reason = kokoro_synthesis.install_kokoro_runtime(
            progress_callback=lambda m: captured["progress"].append(m),
            pip_runner=fake_pip,
            snapshot_fn=fake_snap,
            python_executable="/fake/python",
        )
        assert ok is True
        assert reason is None
        assert captured["pip_argv"][:3] == ["/fake/python", "-m", "pip"]
        assert "install" in captured["pip_argv"]
        assert any("kokoro" in a for a in captured["pip_argv"])
        # Snapshot uses the registry-pinned revision.
        assert captured["snapshot_args"][0] == "hexgrad/Kokoro-82M"
        assert captured["snapshot_args"][1] is not None
        # Progress callback fired for both phases.
        joined = " | ".join(captured["progress"])
        assert "pip" in joined.lower()
        assert "model" in joined.lower() or "weights" in joined.lower()

    def test_pip_failure_returns_actionable_reason(self):
        def fake_pip(argv, capture_output, text, check):
            raise subprocess.CalledProcessError(
                1, argv, output="", stderr="ERROR: could not find a version that satisfies kokoro",
            )

        ok, reason = kokoro_synthesis.install_kokoro_runtime(
            pip_runner=fake_pip,
            snapshot_fn=lambda **_kw: "should not be reached",
            python_executable="/fake/python",
        )
        assert ok is False
        assert "pip install failed" in reason

    def test_snapshot_failure_returns_reason(self):
        def fake_pip(argv, capture_output, text, check):
            return types.SimpleNamespace(stdout="ok", returncode=0)

        def fake_snap(repo_id, revision):
            raise RuntimeError("network down")

        ok, reason = kokoro_synthesis.install_kokoro_runtime(
            pip_runner=fake_pip,
            snapshot_fn=fake_snap,
            python_executable="/fake/python",
        )
        assert ok is False
        assert "model download failed" in reason
        assert "network down" in reason

    def test_python_not_found_returns_reason(self):
        def fake_pip(argv, capture_output, text, check):
            raise FileNotFoundError("python missing")

        ok, reason = kokoro_synthesis.install_kokoro_runtime(
            pip_runner=fake_pip,
            snapshot_fn=lambda **_kw: None,
            python_executable="/fake/python",
        )
        assert ok is False
        assert "Python executable not found" in reason


class TestKokoroDispatchInTtsConversion:
    """Phase 6.2 wired Kokoro into convert_text_chunk_to_speech.
    When settings.provider='Kokoro', _write_kokoro_speech is invoked (not _write_openai_speech)
    and the returned MP3 path is the post-conversion file."""

    def test_kokoro_branch_calls_write_kokoro_speech(self, monkeypatch, tmp_path):
        import tts_conversion
        captured = {"write_calls": [], "convert_calls": []}

        def fake_write(chunk, wav_path, model, voice, speed=1.0, **_kw):
            captured["write_calls"].append((chunk, str(wav_path), model, voice, speed))
            Path(wav_path).write_bytes(b"FAKE_WAV")

        def fake_convert(wav_path, mp3_path):
            captured["convert_calls"].append((str(wav_path), str(mp3_path)))
            Path(mp3_path).write_bytes(b"FAKE_MP3")

        # Patch into the lazy-import sites in tts_conversion's branch.
        import kokoro_synthesis as ks
        monkeypatch.setattr(ks, "_write_kokoro_speech", fake_write)
        monkeypatch.setattr(ks, "_convert_wav_to_mp3", fake_convert)

        settings = types.SimpleNamespace(
            provider="Kokoro", model="kokoro-82m", voice="af_heart",
            speed=1.0, response_format="wav", openai_api_key=None,
            max_concurrency=1,
        )
        result = tts_conversion.convert_text_chunk_to_speech(
            "Hello.", 0, settings, tmp_path, "20260522_120000", retries=1,
        )
        assert result is not None
        assert str(result).endswith(".mp3")
        assert len(captured["write_calls"]) == 1
        assert len(captured["convert_calls"]) == 1
        # Original chunk + model + voice flowed through unchanged
        chunk, _wav, model, voice, speed = captured["write_calls"][0]
        assert chunk == "Hello."
        assert model == "kokoro-82m"
        assert voice == "af_heart"
        assert speed == 1.0
