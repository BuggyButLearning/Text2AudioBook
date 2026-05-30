import dataclasses
import logging
import types

import pytest

import model_discovery
from model_discovery import DiscoveryResult, Source, discover_models, invalidate_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    invalidate_cache()
    yield
    invalidate_cache()


class TestDiscoveryResult:
    def test_is_frozen(self):
        r = DiscoveryResult("OpenAI", ("tts-1",), Source.LIVE, None)
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.models = ()  # type: ignore[misc]

    def test_unknown_provider_returns_empty(self):
        r = discover_models("Mystery")
        assert r == DiscoveryResult("Mystery", (), Source.EMPTY, "unknown provider")


class TestOpenAIDiscovery:
    def _client(self, model_ids):
        openai_mod = pytest.importorskip("openai")

        class FakeModels:
            def list(self_inner):
                return types.SimpleNamespace(
                    data=[types.SimpleNamespace(id=mid) for mid in model_ids]
                )

        class FakeClient:
            def __init__(self_inner, *_a, **_kw):
                self_inner.models = FakeModels()

        return openai_mod, FakeClient

    def test_live_filters_via_registry_pattern(self, monkeypatch):
        openai_mod, FakeClient = self._client(["gpt-4", "tts-1", "whisper-1", "tts-1-hd"])
        monkeypatch.setattr(openai_mod, "OpenAI", FakeClient)
        r = discover_models("OpenAI", api_key="sk-x")
        assert r.source == Source.LIVE
        assert r.models == ("tts-1", "tts-1-hd")
        assert r.error is None

    def test_exception_falls_back_to_registry(self, monkeypatch):
        openai_mod = pytest.importorskip("openai")

        class BoomClient:
            def __init__(self_inner, *_a, **_kw):
                raise RuntimeError("api down")

        monkeypatch.setattr(openai_mod, "OpenAI", BoomClient)
        from providers import PROVIDER_REGISTRY
        r = discover_models("OpenAI", api_key="sk-x")
        assert r.source == Source.FALLBACK
        assert r.models == PROVIDER_REGISTRY["OpenAI"].fallback_models
        assert "api down" in r.error

    def test_live_but_allowlist_empty_returns_empty_not_fallback(self, monkeypatch):
        """Audit S1: API responded OK but no id matched the allowlist.
        Source.EMPTY (with reason) -- NOT Source.FALLBACK.
        Phase 4 needs to distinguish 'OpenAI down' from 'account has no TTS models'."""
        openai_mod, FakeClient = self._client(["gpt-4", "whisper-1", "dall-e-3"])
        monkeypatch.setattr(openai_mod, "OpenAI", FakeClient)
        r = discover_models("OpenAI", api_key="sk-x")
        assert r.source == Source.EMPTY
        assert r.models == ()
        assert "allowlist" in (r.error or "")


class TestOllamaDiscovery:
    def _resp(self, payload):
        class FakeResp:
            def raise_for_status(self_inner):
                return None

            def json(self_inner):
                return payload

        return FakeResp()

    def test_live_filters_via_registry_pattern(self, monkeypatch):
        payload = {"models": [{"name": "bark"}, {"name": "kokoro"}, {"name": "llama3"}, {"name": "mistral"}]}
        monkeypatch.setattr(model_discovery.requests, "get", lambda *_a, **_kw: self._resp(payload))
        r = discover_models("Ollama", ollama_base_url="http://localhost:11434")
        assert r.source == Source.LIVE
        assert r.models == ("bark", "kokoro")

    def test_all_filtered_returns_empty_with_reason(self, monkeypatch):
        payload = {"models": [{"name": "llama3"}, {"name": "mistral"}]}
        monkeypatch.setattr(model_discovery.requests, "get", lambda *_a, **_kw: self._resp(payload))
        r = discover_models("Ollama", ollama_base_url="http://localhost:11434")
        assert r.source == Source.EMPTY
        assert r.models == ()
        assert "allowlist" in (r.error or "")

    def test_http_error_returns_empty(self, monkeypatch):
        def boom(*_a, **_kw):
            raise RuntimeError("connection refused")

        monkeypatch.setattr(model_discovery.requests, "get", boom)
        r = discover_models("Ollama", ollama_base_url="http://localhost:11434")
        assert r.source == Source.EMPTY
        assert "connection refused" in r.error


class TestOllamaReachable:
    """Phase 6: pre-flight reachability probe distinct from model discovery.
    Separates 'Ollama not running' (start `ollama serve`) from 'Ollama running
    but no TTS model' (pull a model)."""

    def test_returns_true_on_2xx(self):
        def fake_get(*_a, **_kw):
            return types.SimpleNamespace(status_code=200)
        ok, reason = model_discovery.ollama_reachable("http://localhost:11434", request_fn=fake_get)
        assert ok is True
        assert reason is None

    def test_returns_false_on_non_2xx(self):
        def fake_get(*_a, **_kw):
            return types.SimpleNamespace(status_code=500)
        ok, reason = model_discovery.ollama_reachable("http://localhost:11434", request_fn=fake_get)
        assert ok is False
        assert "500" in (reason or "")

    def test_returns_false_with_serve_hint_on_connection_refused(self):
        import requests as _req

        def fake_get(*_a, **_kw):
            raise _req.exceptions.ConnectionError("refused")
        ok, reason = model_discovery.ollama_reachable("http://localhost:11434", request_fn=fake_get)
        assert ok is False
        assert "ollama serve" in (reason or "")

    def test_returns_false_on_connect_timeout(self):
        import requests as _req

        def fake_get(*_a, **_kw):
            raise _req.exceptions.ConnectTimeout("slow")
        ok, reason = model_discovery.ollama_reachable("http://localhost:11434", request_fn=fake_get)
        assert ok is False
        assert "timed out" in (reason or "")

    def test_canonicalizes_url_before_probe(self):
        captured = {}

        def fake_get(url, *_a, **_kw):
            captured["url"] = url
            return types.SimpleNamespace(status_code=200)
        model_discovery.ollama_reachable("http://localhost:11434/", request_fn=fake_get)
        assert captured["url"] == "http://localhost:11434/api/version"

    def test_default_url_used_when_none(self):
        captured = {}

        def fake_get(url, *_a, **_kw):
            captured["url"] = url
            return types.SimpleNamespace(status_code=200)
        model_discovery.ollama_reachable(None, request_fn=fake_get)
        assert captured["url"] == "http://localhost:11434/api/version"


class TestOllamaConnectionRefinedError:
    """Phase 6: connection-refused branch surfaces the `ollama serve` hint
    in DiscoveryResult.error (separate from generic exception path)."""

    def test_connection_error_surfaces_serve_hint(self, monkeypatch):
        import requests as _req

        def boom(*_a, **_kw):
            raise _req.exceptions.ConnectionError("refused")
        monkeypatch.setattr(model_discovery.requests, "get", boom)
        r = discover_models("Ollama", ollama_base_url="http://localhost:11434")
        assert r.source == Source.EMPTY
        assert "ollama serve" in (r.error or "")


class TestCacheBehavior:
    def test_cache_hit_skips_network(self, monkeypatch):
        openai_mod = pytest.importorskip("openai")
        calls = {"count": 0}

        class FakeModels:
            def list(self_inner):
                calls["count"] += 1
                return types.SimpleNamespace(data=[types.SimpleNamespace(id="tts-1")])

        class FakeClient:
            def __init__(self_inner, *_a, **_kw):
                self_inner.models = FakeModels()

        monkeypatch.setattr(openai_mod, "OpenAI", FakeClient)

        r1 = discover_models("OpenAI", api_key="sk-x")
        r2 = discover_models("OpenAI", api_key="sk-x")
        assert r1 == r2
        assert calls["count"] == 1

    def test_use_cache_false_forces_refetch(self, monkeypatch):
        openai_mod = pytest.importorskip("openai")
        calls = {"count": 0}

        class FakeModels:
            def list(self_inner):
                calls["count"] += 1
                return types.SimpleNamespace(data=[types.SimpleNamespace(id="tts-1")])

        class FakeClient:
            def __init__(self_inner, *_a, **_kw):
                self_inner.models = FakeModels()

        monkeypatch.setattr(openai_mod, "OpenAI", FakeClient)

        discover_models("OpenAI", api_key="sk-x")
        discover_models("OpenAI", api_key="sk-x", use_cache=False)
        assert calls["count"] == 2

    def test_invalidate_provider_drops_only_that_entry(self, monkeypatch):
        openai_mod = pytest.importorskip("openai")
        calls = {"openai": 0, "ollama": 0}

        class FakeModels:
            def list(self_inner):
                calls["openai"] += 1
                return types.SimpleNamespace(data=[types.SimpleNamespace(id="tts-1")])

        class FakeClient:
            def __init__(self_inner, *_a, **_kw):
                self_inner.models = FakeModels()

        class FakeResp:
            def raise_for_status(self_inner):
                return None

            def json(self_inner):
                calls["ollama"] += 1
                return {"models": [{"name": "bark"}]}

        monkeypatch.setattr(openai_mod, "OpenAI", FakeClient)
        monkeypatch.setattr(model_discovery.requests, "get", lambda *_a, **_kw: FakeResp())

        discover_models("OpenAI", api_key="sk-x")
        discover_models("Ollama", ollama_base_url="http://localhost:11434")
        assert calls == {"openai": 1, "ollama": 1}

        invalidate_cache("OpenAI")
        discover_models("OpenAI", api_key="sk-x")
        discover_models("Ollama", ollama_base_url="http://localhost:11434")
        assert calls == {"openai": 2, "ollama": 1}

    def test_different_api_keys_are_separate_cache_entries(self, monkeypatch):
        openai_mod = pytest.importorskip("openai")
        calls = {"count": 0}

        class FakeModels:
            def list(self_inner):
                calls["count"] += 1
                return types.SimpleNamespace(data=[types.SimpleNamespace(id="tts-1")])

        class FakeClient:
            def __init__(self_inner, *_a, **_kw):
                self_inner.models = FakeModels()

        monkeypatch.setattr(openai_mod, "OpenAI", FakeClient)

        discover_models("OpenAI", api_key="sk-A")
        discover_models("OpenAI", api_key="sk-B")
        assert calls["count"] == 2

    def test_invalidate_all_drops_everything(self, monkeypatch):
        openai_mod = pytest.importorskip("openai")
        calls = {"count": 0}

        class FakeModels:
            def list(self_inner):
                calls["count"] += 1
                return types.SimpleNamespace(data=[types.SimpleNamespace(id="tts-1")])

        class FakeClient:
            def __init__(self_inner, *_a, **_kw):
                self_inner.models = FakeModels()

        monkeypatch.setattr(openai_mod, "OpenAI", FakeClient)

        discover_models("OpenAI", api_key="sk-x")
        invalidate_cache()
        discover_models("OpenAI", api_key="sk-x")
        assert calls["count"] == 2

    def test_none_and_default_api_key_share_cache_entry(self, monkeypatch):
        """Audit S3: None and the default (which IS None) MUST share one cache entry;
        only different NON-None values get separate entries."""
        openai_mod = pytest.importorskip("openai")
        calls = {"count": 0}

        class FakeModels:
            def list(self_inner):
                calls["count"] += 1
                return types.SimpleNamespace(data=[types.SimpleNamespace(id="tts-1")])

        class FakeClient:
            def __init__(self_inner, *_a, **_kw):
                self_inner.models = FakeModels()

        monkeypatch.setattr(openai_mod, "OpenAI", FakeClient)
        discover_models("OpenAI")
        discover_models("OpenAI", api_key=None)
        assert calls["count"] == 1
        discover_models("OpenAI", api_key="sk-x")
        assert calls["count"] == 2

    def test_fallback_result_is_cached_until_invalidate(self, monkeypatch):
        """Audit S4: FALLBACK results stick -- a transient blip is not auto-retried.
        'Refresh Models' (invalidate) is the recovery path."""
        openai_mod = pytest.importorskip("openai")
        calls = {"count": 0}

        class BoomClient:
            def __init__(self_inner, *_a, **_kw):
                calls["count"] += 1
                raise RuntimeError("api down")

        monkeypatch.setattr(openai_mod, "OpenAI", BoomClient)
        r1 = discover_models("OpenAI", api_key="sk-x")
        r2 = discover_models("OpenAI", api_key="sk-x")
        assert r1.source == Source.FALLBACK
        assert r2.source == Source.FALLBACK
        assert calls["count"] == 1
        invalidate_cache("OpenAI")
        discover_models("OpenAI", api_key="sk-x")
        assert calls["count"] == 2

    def test_ollama_url_canonicalization_in_cache_key(self, monkeypatch):
        """Audit S2: None, 'http://localhost:11434', and 'http://localhost:11434/' must
        collapse to ONE cache entry."""
        calls = {"count": 0}

        class FakeResp:
            def raise_for_status(self_inner):
                return None

            def json(self_inner):
                calls["count"] += 1
                return {"models": [{"name": "bark"}]}

        monkeypatch.setattr(model_discovery.requests, "get", lambda *_a, **_kw: FakeResp())

        discover_models("Ollama", ollama_base_url=None)
        discover_models("Ollama", ollama_base_url="http://localhost:11434")
        discover_models("Ollama", ollama_base_url="http://localhost:11434/")
        assert calls["count"] == 1


class TestNoCredentialLeakage:
    """Audit M1: api_key value MUST NOT appear in logs or in DiscoveryResult.error.
    Phase 2 set this invariant for the synthesis path (TestChunkLogging);
    Phase 2.1 propagates it to the discovery path."""

    def test_api_key_not_in_discovery_logs(self, monkeypatch, caplog):
        openai_mod = pytest.importorskip("openai")
        leaked_key = "sk-LEAK-CHECK-123"

        class LeakyClient:
            def __init__(self_inner, *_a, **_kw):
                raise RuntimeError(
                    f"Auth failed for {leaked_key} at https://api.openai.com/v1/models"
                )

        monkeypatch.setattr(openai_mod, "OpenAI", LeakyClient)

        with caplog.at_level(logging.WARNING):
            result = discover_models("OpenAI", api_key=leaked_key)

        assert result.source == Source.FALLBACK
        assert leaked_key not in caplog.text, (
            f"api_key leaked into log output: {caplog.text}"
        )
        assert leaked_key not in (result.error or ""), (
            f"api_key leaked into DiscoveryResult.error: {result.error}"
        )
        assert "***REDACTED***" in (result.error or "")
