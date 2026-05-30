"""Phase 8 — CLI tests. argparse + subcommand dispatch + JSON output + exit codes.

All synthesis paths mocked at module boundary; no real network."""
import io
import json
import sys
import types
from pathlib import Path

import pytest

import cli


def _run(argv, monkeypatch):
    """Invoke cli.main(argv) capturing stdout + stderr + exit code."""
    buf_out, buf_err = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf_out)
    monkeypatch.setattr(sys, "stderr", buf_err)
    code = cli.main(argv)
    return code, buf_out.getvalue(), buf_err.getvalue()


def _json_lines(text):
    """Parse stdout containing one JSON object per line."""
    return [json.loads(line) for line in text.splitlines() if line.strip()]


class TestListProviders:
    def test_human_output(self, monkeypatch):
        code, out, _ = _run(["list-providers"], monkeypatch)
        assert code == cli.EXIT_OK
        assert "OpenAI" in out
        assert "Kokoro" in out

    def test_json_output(self, monkeypatch):
        code, out, _ = _run(["--json", "list-providers"], monkeypatch)
        assert code == cli.EXIT_OK
        payload = json.loads(out.strip())
        assert "OpenAI" in payload["providers"]
        assert "Kokoro" in payload["providers"]


class TestListVoices:
    def test_kokoro_voices(self, monkeypatch):
        code, out, _ = _run(["--json", "list-voices", "--provider", "Kokoro"], monkeypatch)
        assert code == cli.EXIT_OK
        payload = json.loads(out.strip())
        assert payload["provider"] == "Kokoro"
        assert "af_heart" in payload["voices"]

    def test_unknown_provider_exits_1(self, monkeypatch):
        code, _out, err = _run(["list-voices", "--provider", "Mystery"], monkeypatch)
        assert code == cli.EXIT_INVALID_ARGS
        assert "unknown provider" in err.lower()


class TestListModels:
    def test_uses_discover_models(self, monkeypatch):
        from model_discovery import DiscoveryResult, Source
        captured = {"calls": []}

        def fake_discover(provider, **kwargs):
            captured["calls"].append((provider, kwargs))
            return DiscoveryResult(provider, ("tts-1", "tts-1-hd"), Source.LIVE, None)

        monkeypatch.setattr("model_discovery.discover_models", fake_discover)
        code, out, _ = _run(["--json", "list-models", "--provider", "OpenAI"], monkeypatch)
        assert code == cli.EXIT_OK
        payload = json.loads(out.strip())
        assert payload["models"] == ["tts-1", "tts-1-hd"]
        assert payload["source"] == "live"

    def test_refresh_flag_invalidates_cache(self, monkeypatch):
        from model_discovery import DiscoveryResult, Source
        invalidated = []
        monkeypatch.setattr("model_discovery.invalidate_cache", lambda p: invalidated.append(p))
        monkeypatch.setattr("model_discovery.discover_models",
                            lambda *a, **kw: DiscoveryResult("OpenAI", ("tts-1",), Source.LIVE, None))
        _run(["list-models", "--provider", "OpenAI", "--refresh"], monkeypatch)
        assert invalidated == ["OpenAI"]


class TestChunkPolicy:
    def test_default_human_output(self, monkeypatch):
        code, out, _ = _run(["chunk-policy"], monkeypatch)
        assert code == cli.EXIT_OK
        assert "OpenAI" in out and "3500" in out
        assert "Kokoro" in out and "2000" in out
        assert "Ollama" in out and "1000" in out

    def test_json_with_resolution(self, monkeypatch):
        code, out, _ = _run(
            ["--json", "chunk-policy", "--provider", "Kokoro", "--model", "kokoro-82m"],
            monkeypatch,
        )
        assert code == cli.EXIT_OK
        payload = json.loads(out.strip())
        assert payload["resolved"]["chunk_max"] == 2000

    def test_config_override_applied(self, monkeypatch):
        monkeypatch.setattr("settings.load_config",
                            lambda: {"chunk_overrides": {"OpenAI": 4000}})
        code, out, _ = _run(
            ["--json", "chunk-policy", "--provider", "OpenAI"],
            monkeypatch,
        )
        payload = json.loads(out.strip())
        assert payload["resolved"]["chunk_max"] == 4000
        assert payload["overrides"] == {"OpenAI": 4000}


class TestShowConfig:
    def test_includes_chunk_max_in_snapshot(self, monkeypatch):
        from settings import RuntimeSettings
        fake = RuntimeSettings(
            provider="Kokoro", model="kokoro-82m", voice="af_heart",
            chunk_max=2000, openai_api_key="sk-x",
        )
        monkeypatch.setattr("settings.build_runtime_settings", lambda **kw: fake)
        code, out, _ = _run(["--json", "show-config"], monkeypatch)
        payload = json.loads(out.strip())
        assert payload["chunk_max"] == 2000
        assert payload["provider"] == "Kokoro"
        assert payload["openai_api_key_present"] is True


class TestSynthesizeDryRun:
    def test_dry_run_exits_ok_without_synthesizing(self, monkeypatch, tmp_path):
        from settings import RuntimeSettings
        inp = tmp_path / "in.txt"
        inp.write_text("Hello.", encoding="utf-8")
        out_path = tmp_path / "out.mp3"

        called = {"convert": 0}
        monkeypatch.setattr("tts_conversion.convert_text_to_speech",
                            lambda *a, **kw: called.update(convert=called["convert"] + 1) or ["x"])
        monkeypatch.setattr("settings.build_runtime_settings",
                            lambda **kw: RuntimeSettings(
                                provider="OpenAI", model="tts-1", voice="alloy",
                                chunk_max=3500, openai_api_key="sk-x",
                                output_folder=tmp_path,
                            ))

        code, out, _ = _run([
            "--json", "synthesize",
            "--input", str(inp), "--output", str(out_path),
            "--provider", "OpenAI", "--dry-run",
        ], monkeypatch)
        assert code == cli.EXIT_OK
        assert called["convert"] == 0, "dry-run MUST NOT invoke synthesis"
        payload = json.loads(out.strip())
        assert payload["event"] == "dry-run"
        assert payload["provider"] == "OpenAI"
        assert payload["chunk_max"] == 3500


class TestSynthesizeErrorPaths:
    def test_missing_input_file_exits_4(self, monkeypatch, tmp_path):
        code, _out, err = _run([
            "synthesize",
            "--input", str(tmp_path / "nope.txt"),
            "--output", str(tmp_path / "out.mp3"),
        ], monkeypatch)
        assert code == cli.EXIT_INPUT_UNREADABLE
        assert "not found" in err.lower()

    def test_openai_without_key_exits_1(self, monkeypatch, tmp_path):
        from settings import RuntimeSettings
        inp = tmp_path / "in.txt"
        inp.write_text("Hi.", encoding="utf-8")
        monkeypatch.setattr("settings.build_runtime_settings",
                            lambda **kw: RuntimeSettings(
                                provider="OpenAI", model="tts-1", voice="alloy",
                                chunk_max=3500, openai_api_key=None,
                                output_folder=tmp_path,
                            ))
        code, _out, err = _run([
            "synthesize",
            "--input", str(inp), "--output", str(tmp_path / "out.mp3"),
            "--provider", "OpenAI",
        ], monkeypatch)
        assert code == cli.EXIT_INVALID_ARGS
        assert "api key" in err.lower()

    def test_kokoro_lib_missing_exits_3(self, monkeypatch, tmp_path):
        from settings import RuntimeSettings
        import kokoro_synthesis
        monkeypatch.setattr(kokoro_synthesis, "kokoro_available",
                            lambda: (False, "kokoro package not importable"))
        inp = tmp_path / "in.txt"
        inp.write_text("Hi.", encoding="utf-8")
        monkeypatch.setattr("settings.build_runtime_settings",
                            lambda **kw: RuntimeSettings(
                                provider="Kokoro", model="kokoro-82m", voice="af_heart",
                                chunk_max=2000, openai_api_key=None,
                                output_folder=tmp_path,
                            ))
        code, _out, err = _run([
            "synthesize",
            "--input", str(inp), "--output", str(tmp_path / "out.mp3"),
            "--provider", "Kokoro",
        ], monkeypatch)
        assert code == cli.EXIT_PROVIDER_NOT_READY
        assert "kokoro" in err.lower()

    def test_synthesis_partial_failure_exits_2(self, monkeypatch, tmp_path):
        from settings import RuntimeSettings
        inp = tmp_path / "in.txt"
        inp.write_text("Hello world. Foo bar. Baz qux.", encoding="utf-8")
        monkeypatch.setattr("settings.build_runtime_settings",
                            lambda **kw: RuntimeSettings(
                                provider="OpenAI", model="tts-1", voice="alloy",
                                chunk_max=3500, openai_api_key="sk-x",
                                output_folder=tmp_path,
                            ))
        # convert_text_to_speech returns FEWER files than chunks.
        monkeypatch.setattr("tts_conversion.convert_text_to_speech",
                            lambda chunks, *a, **kw: chunks[:0])
        monkeypatch.setattr("tts_conversion.concatenate_audio_files", lambda *a, **kw: None)
        code, _out, err = _run([
            "synthesize",
            "--input", str(inp), "--output", str(tmp_path / "out.mp3"),
            "--provider", "OpenAI",
        ], monkeypatch)
        assert code == cli.EXIT_SYNTHESIS_FAILED


class TestSynthesizeSuccess:
    def test_success_emits_complete_event(self, monkeypatch, tmp_path):
        from settings import RuntimeSettings
        inp = tmp_path / "in.txt"
        inp.write_text("Hello world.", encoding="utf-8")
        out_path = tmp_path / "out.mp3"

        monkeypatch.setattr("settings.build_runtime_settings",
                            lambda **kw: RuntimeSettings(
                                provider="OpenAI", model="tts-1", voice="alloy",
                                chunk_max=3500, openai_api_key="sk-x",
                                output_folder=tmp_path,
                            ))
        monkeypatch.setattr("tts_conversion.convert_text_to_speech",
                            lambda chunks, *a, **kw: [tmp_path / f"x{i}.mp3" for i in range(len(chunks))])
        monkeypatch.setattr("tts_conversion.concatenate_audio_files", lambda files, out: out_path.write_bytes(b"fake"))

        code, out, _ = _run([
            "--json", "synthesize",
            "--input", str(inp), "--output", str(out_path),
            "--provider", "OpenAI", "--quiet",
        ], monkeypatch)
        assert code == cli.EXIT_OK
        events = _json_lines(out)
        start_evts = [e for e in events if e["event"] == "start"]
        complete_evts = [e for e in events if e["event"] == "complete"]
        assert len(start_evts) == 1
        assert len(complete_evts) == 1
        assert complete_evts[0]["chunks"] == start_evts[0]["chunks"]


class TestChunkMaxFlagOverridesPolicy:
    def test_explicit_chunk_max_used_in_settings(self, monkeypatch, tmp_path):
        from settings import RuntimeSettings
        captured = {"chunk_max_seen": None}

        def fake_build(**kw):
            captured["chunk_max_seen"] = kw.get("chunk_max")
            return RuntimeSettings(
                provider="OpenAI", model="tts-1", voice="alloy",
                chunk_max=kw.get("chunk_max") or 3500, openai_api_key="sk-x",
                output_folder=tmp_path,
            )

        monkeypatch.setattr("settings.build_runtime_settings", fake_build)
        inp = tmp_path / "in.txt"
        inp.write_text("Hello.", encoding="utf-8")
        _run([
            "synthesize", "--input", str(inp), "--output", str(tmp_path / "out.mp3"),
            "--provider", "OpenAI", "--chunk-max", "2500", "--dry-run",
        ], monkeypatch)
        assert captured["chunk_max_seen"] == 2500
