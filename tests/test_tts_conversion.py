import types

import pytest

import tts_conversion
from tts_conversion import (
    _filter_openai_tts_models,
    _validate_ollama_model_support,
    concatenate_audio_files,
    convert_text_chunk_to_speech,
    list_available_models,
    list_ollama_models,
)


class TestFilterOpenAITTSModels:
    def test_keeps_only_tts_models(self):
        result = _filter_openai_tts_models(["gpt-4", "tts-1", "whisper-1", "tts-1-hd"])
        assert result == ["tts-1", "tts-1-hd"]

    def test_dedupes_and_sorts(self):
        result = _filter_openai_tts_models(["tts-1-hd", "tts-1", "tts-1"])
        assert result == ["tts-1", "tts-1-hd"]

    def test_uppercase_tts_now_rejected(self):
        # CHARACTERIZED — Phase 2: registry pattern is anchored ^tts-... + case-sensitive
        from providers import PROVIDER_REGISTRY
        result = _filter_openai_tts_models(["TTS-MODEL-X"])
        assert result == list(PROVIDER_REGISTRY["OpenAI"].fallback_models)

    def test_falls_back_when_no_tts_models(self):
        # CHARACTERIZED — Phase 2: fallback now sourced from providers.PROVIDER_REGISTRY (single source of truth)
        from providers import PROVIDER_REGISTRY
        assert _filter_openai_tts_models(["gpt-4", "whisper-1"]) == list(PROVIDER_REGISTRY["OpenAI"].fallback_models)

    def test_fallback_consistency_settings_vs_registry(self):
        """Audit M1: settings.OPENAI_FALLBACK_MODELS and providers.PROVIDER_REGISTRY["OpenAI"].fallback_models
        MUST stay in sync — single source of truth invariant."""
        import settings
        from providers import PROVIDER_REGISTRY
        assert list(settings.OPENAI_FALLBACK_MODELS) == list(PROVIDER_REGISTRY["OpenAI"].fallback_models)


class TestValidateOllamaModelSupport:
    @pytest.mark.parametrize(
        "name", ["bark-small", "kokoro-82m", "tts-tiny", "speech-1", "TTS-FOO", "Bark"]
    )
    def test_returns_true_for_speech_keywords(self, name):
        assert _validate_ollama_model_support(name) is True

    @pytest.mark.parametrize("name", ["llama3", "mistral", "gpt-4", ""])
    def test_returns_false_otherwise(self, name):
        assert _validate_ollama_model_support(name) is False

    def test_handles_none(self):
        assert _validate_ollama_model_support(None) is False

    def test_uses_registry_pattern(self):
        from providers import PROVIDER_REGISTRY
        pattern = PROVIDER_REGISTRY["Ollama"].model_pattern
        assert "bark" in pattern and "kokoro" in pattern and "tts" in pattern and "speech" in pattern

    @pytest.mark.parametrize("bad_input", [123, 1.5, [], {}, object(), True])
    def test_non_string_inputs_return_false(self, bad_input):
        """Audit S4: explicit type guard means non-strings return False, not crash."""
        assert _validate_ollama_model_support(bad_input) is False


class TestListOllamaModels:
    def test_parses_models_from_api(self, monkeypatch):
        class FakeResp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"models": [{"name": "bark"}, {"name": "kokoro"}, {"name": "bark"}]}

        monkeypatch.setattr(tts_conversion.requests, "get", lambda *_a, **_kw: FakeResp())
        result = list_ollama_models("http://localhost:11434")
        assert result == ["bark", "kokoro"]

    def test_returns_empty_on_http_error(self, monkeypatch):
        def boom(*_a, **_kw):
            raise RuntimeError("connection refused")

        monkeypatch.setattr(tts_conversion.requests, "get", boom)
        assert list_ollama_models("http://localhost:11434") == []

    def test_skips_malformed_entries(self, monkeypatch):
        class FakeResp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"models": [{"name": "ok"}, "not-a-dict", {"no_name": "x"}]}

        monkeypatch.setattr(tts_conversion.requests, "get", lambda *_a, **_kw: FakeResp())
        assert list_ollama_models("http://localhost:11434") == ["ok"]


class TestListAvailableModels:
    def test_routes_to_ollama_when_provider_is_ollama(self, monkeypatch):
        called = {}

        def fake_ollama(base_url):
            called["url"] = base_url
            return ["bark"]

        monkeypatch.setattr(tts_conversion, "list_ollama_models", fake_ollama)
        result = list_available_models("Ollama", api_key=None, ollama_base_url="http://x:1")
        assert result == ["bark"]
        assert called["url"] == "http://x:1"

    def test_routes_to_openai_otherwise(self, monkeypatch):
        # AUDIT M2: deferred import; patch openai.OpenAI at source module.
        openai_mod = pytest.importorskip("openai")

        class FakeModels:
            def list(self):
                return types.SimpleNamespace(
                    data=[types.SimpleNamespace(id="tts-1"), types.SimpleNamespace(id="gpt-4")]
                )

        class FakeClient:
            def __init__(self, *_a, **_kw):
                self.models = FakeModels()

        monkeypatch.setattr(openai_mod, "OpenAI", FakeClient)
        result = list_available_models("OpenAI", api_key="sk-test")
        assert "tts-1" in result

    def test_openai_failure_falls_back(self, monkeypatch):
        openai_mod = pytest.importorskip("openai")

        class FakeClient:
            def __init__(self, *_a, **_kw):
                raise RuntimeError("API down")

        monkeypatch.setattr(openai_mod, "OpenAI", FakeClient)
        from settings import OPENAI_FALLBACK_MODELS
        assert list_available_models("OpenAI", api_key="sk-test") == OPENAI_FALLBACK_MODELS


class TestConvertTextChunkOllamaBranch:
    def test_ollama_with_unsupported_model_returns_none_after_retries(self, tmp_path):
        s = types.SimpleNamespace(
            provider="Ollama",
            model="llama3",
            voice="alloy",
            speed=1.0,
            response_format="mp3",
            openai_api_key=None,
            max_concurrency=1,
        )
        result = convert_text_chunk_to_speech("hello", 0, s, tmp_path, "20260521_000000", retries=1)
        assert result is None

    def test_ollama_with_supported_model_still_unsupported_path(self, tmp_path):
        # Even when validate passes, current impl raises "not available through standard Ollama endpoints".
        s = types.SimpleNamespace(
            provider="Ollama",
            model="bark-tiny",
            voice="alloy",
            speed=1.0,
            response_format="mp3",
            openai_api_key=None,
            max_concurrency=1,
        )
        result = convert_text_chunk_to_speech("hello", 0, s, tmp_path, "20260521_000000", retries=1)
        assert result is None


class TestConcatenateAudioFiles:
    """
    concatenate_audio_files lives in tts_conversion.py per the source,
    even though plan AC-5 originally listed it under combine_and_convert.py.
    Tests moved here per actual source location (deviation flagged in SUMMARY).
    """

    def test_raises_on_empty_list(self, tmp_path):
        with pytest.raises(ValueError):
            concatenate_audio_files([], tmp_path / "out.mp3")

    def test_iterates_inputs_in_order(self, monkeypatch, tmp_path):
        calls = []

        class FakeSegment:
            def __init__(self, name="x"):
                self.name = name

            def __iadd__(self, other):
                calls.append(("iadd", other.name))
                return self

            def __add__(self, other):
                calls.append(("add", other.name))
                return self

            def export(self, path, format):  # noqa: A002
                calls.append(("export", str(path), format))
                return self

        monkeypatch.setattr(tts_conversion.AudioSegment, "empty", lambda: FakeSegment("empty"))
        monkeypatch.setattr(tts_conversion.AudioSegment, "from_mp3", lambda path: FakeSegment(str(path)))

        files = ["a.mp3", "b.mp3", "c.mp3"]
        concatenate_audio_files(files, tmp_path / "out.mp3")

        export_calls = [c for c in calls if c[0] == "export"]
        assert len(export_calls) == 1
        iadds = [c for c in calls if c[0] in ("iadd", "add")]
        assert [c[1] for c in iadds] == ["a.mp3", "b.mp3", "c.mp3"]


class TestConcurrencyClamp:
    def _make_settings(self, provider, max_concurrency):
        return types.SimpleNamespace(
            provider=provider,
            model="x",
            voice="alloy",
            speed=1.0,
            response_format="mp3",
            openai_api_key=None,
            max_concurrency=max_concurrency,
        )

    def _capturing_executor_cls(self, captured):
        class CapturingExecutor:
            def __init__(self, max_workers):
                captured["max_workers"] = max_workers

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

            def submit(self, *_a, **_kw):
                class Fut:
                    def result(self_):
                        return None
                return Fut()

        return CapturingExecutor

    def test_local_provider_capped_at_registry_max(self, monkeypatch, tmp_path):
        captured = {}
        monkeypatch.setattr(tts_conversion, "ThreadPoolExecutor", self._capturing_executor_cls(captured))
        s = self._make_settings("Ollama", max_concurrency=8)
        tts_conversion.convert_text_to_speech(["a", "b"], s, tmp_path, "20260521")
        assert captured["max_workers"] == 1

    def test_hosted_provider_uses_requested_concurrency(self, monkeypatch, tmp_path):
        captured = {}
        monkeypatch.setattr(tts_conversion, "ThreadPoolExecutor", self._capturing_executor_cls(captured))
        s = self._make_settings("OpenAI", max_concurrency=4)
        tts_conversion.convert_text_to_speech([], s, tmp_path, "20260521")
        assert captured["max_workers"] == 4

    def test_clamp_log_message_explicit(self, monkeypatch, tmp_path, caplog):
        import logging as _logging
        captured = {}
        monkeypatch.setattr(tts_conversion, "ThreadPoolExecutor", self._capturing_executor_cls(captured))
        s = self._make_settings("Ollama", max_concurrency=8)
        with caplog.at_level(_logging.INFO):
            tts_conversion.convert_text_to_speech([], s, tmp_path, "20260521")
        joined = " ".join(r.message for r in caplog.records)
        assert "clamped" in joined and "Ollama" in joined

    def test_hosted_uses_requested_log_message(self, monkeypatch, tmp_path, caplog):
        import logging as _logging
        captured = {}
        monkeypatch.setattr(tts_conversion, "ThreadPoolExecutor", self._capturing_executor_cls(captured))
        s = self._make_settings("OpenAI", max_concurrency=4)
        with caplog.at_level(_logging.INFO):
            tts_conversion.convert_text_to_speech([], s, tmp_path, "20260521")
        joined = " ".join(r.message for r in caplog.records)
        assert "using requested" in joined and "OpenAI" in joined


class TestWithStreamingResponse:
    def _build_fake_client(self, calls):
        class FakeStream:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *_a):
                return False

            def stream_to_file(self_inner, path):
                calls.append(("stream_to_file", str(path)))
                from pathlib import Path
                Path(path).write_bytes(b"FAKE_AUDIO_PAYLOAD")

        class FakeWithStreamingResponse:
            def create(self_inner, **kwargs):
                calls.append(("create", kwargs))
                return FakeStream()

        class FakeSpeech:
            with_streaming_response = FakeWithStreamingResponse()

            def create(self_inner, **kwargs):
                calls.append(("DEPRECATED_create", kwargs))
                raise AssertionError("must not call non-streaming create()")

        class FakeAudio:
            speech = FakeSpeech()

        class FakeClient:
            def __init__(self_inner, *_a, **_kw):
                self_inner.audio = FakeAudio()

        return FakeClient

    def test_uses_with_streaming_response_context_manager(self, monkeypatch, tmp_path):
        openai_mod = pytest.importorskip("openai")
        calls = []
        monkeypatch.setattr(openai_mod, "OpenAI", self._build_fake_client(calls))

        from tts_conversion import _write_openai_speech
        out = tmp_path / "out.mp3"
        _write_openai_speech("hello", out, api_key="sk-x", model="tts-1", voice="alloy")

        assert ("create", {"model": "tts-1", "voice": "alloy", "input": "hello", "speed": 1.0, "response_format": "mp3"}) in calls
        assert any(c[0] == "stream_to_file" for c in calls)
        assert not any(c[0] == "DEPRECATED_create" for c in calls)
        assert out.read_bytes() == b"FAKE_AUDIO_PAYLOAD"

    def test_no_deprecation_warning_emitted(self, monkeypatch, tmp_path):
        """Audit S5: explicit catch_warnings proves the contract, independent of pytest.ini filter."""
        import warnings as _warnings
        openai_mod = pytest.importorskip("openai")
        calls = []
        monkeypatch.setattr(openai_mod, "OpenAI", self._build_fake_client(calls))

        from tts_conversion import _write_openai_speech
        out = tmp_path / "out.mp3"

        with _warnings.catch_warnings(record=True) as captured:
            _warnings.simplefilter("always")
            _write_openai_speech("hello", out, api_key="sk-x", model="tts-1", voice="alloy")

        deprecations = [w for w in captured if issubclass(w.category, DeprecationWarning)]
        assert deprecations == [], f"unexpected deprecation warnings: {[str(w.message) for w in deprecations]}"


class TestChunkLogging:
    def test_logs_include_provider_and_model(self, monkeypatch, tmp_path, caplog):
        def fake_write(**kwargs):
            return None

        monkeypatch.setattr(tts_conversion, "_write_openai_speech", fake_write)
        s = types.SimpleNamespace(
            provider="OpenAI", model="tts-1", voice="alloy",
            speed=1.0, response_format="mp3", openai_api_key="sk-SECRET-KEY-123",
            max_concurrency=1,
        )
        import logging as _logging
        with caplog.at_level(_logging.INFO):
            tts_conversion.convert_text_chunk_to_speech(
                "x" * 200, 0, s, tmp_path, "20260521", retries=1,
            )
        joined = " ".join(r.message for r in caplog.records)
        assert "provider=OpenAI" in joined
        assert "model=tts-1" in joined
        assert "sk-SECRET-KEY-123" not in joined
        assert "x" * 200 not in joined


class TestStatusCallbackIsolation:
    """Audit S2: a raising status_callback must NOT abort the chunk conversion."""

    def test_callback_exception_does_not_fail_chunk(self, monkeypatch, tmp_path, caplog):
        def fake_write(**kwargs):
            return None

        monkeypatch.setattr(tts_conversion, "_write_openai_speech", fake_write)

        def raising_callback(_message):
            raise RuntimeError("simulated GUI-closed Tkinter error")

        s = types.SimpleNamespace(
            provider="OpenAI", model="tts-1", voice="alloy",
            speed=1.0, response_format="mp3", openai_api_key="sk-x",
            max_concurrency=1,
        )

        import logging as _logging
        with caplog.at_level(_logging.WARNING):
            result = tts_conversion.convert_text_chunk_to_speech(
                "hello", 0, s, tmp_path, "20260521",
                status_callback=raising_callback, retries=1,
            )

        assert result is not None
        warnings_logged = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any("status_callback raised" in r.message for r in warnings_logged)
