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

    def test_case_insensitive_match(self):
        result = _filter_openai_tts_models(["TTS-MODEL-X"])
        assert "TTS-MODEL-X" in result

    def test_falls_back_when_no_tts_models(self):
        from settings import OPENAI_FALLBACK_MODELS
        assert _filter_openai_tts_models(["gpt-4", "whisper-1"]) == OPENAI_FALLBACK_MODELS


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
