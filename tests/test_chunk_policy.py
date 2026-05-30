from chunk_policy import (
    DEFAULT_CHUNK_MAX_BY_PROVIDER,
    DEFAULT_CHUNK_MAX_FALLBACK,
    policy_snapshot,
    resolve_chunk_max,
)


class TestBuiltinDefaults:
    def test_openai_is_3500(self):
        assert DEFAULT_CHUNK_MAX_BY_PROVIDER["OpenAI"] == 3500

    def test_kokoro_is_2000(self):
        assert DEFAULT_CHUNK_MAX_BY_PROVIDER["Kokoro"] == 2000

    def test_ollama_is_1000(self):
        assert DEFAULT_CHUNK_MAX_BY_PROVIDER["Ollama"] == 1000

    def test_fallback_is_3500(self):
        assert DEFAULT_CHUNK_MAX_FALLBACK == 3500


class TestResolveChunkMax:
    def test_default_per_provider(self):
        assert resolve_chunk_max("OpenAI") == 3500
        assert resolve_chunk_max("Kokoro") == 2000
        assert resolve_chunk_max("Ollama") == 1000

    def test_unknown_provider_uses_fallback(self):
        assert resolve_chunk_max("Mystery") == 3500

    def test_provider_override_wins_over_default(self):
        assert resolve_chunk_max("OpenAI", overrides={"OpenAI": 4000}) == 4000

    def test_provider_model_override_wins_over_provider(self):
        ov = {"OpenAI": 4000, "OpenAI:tts-1-hd": 3800}
        assert resolve_chunk_max("OpenAI", model="tts-1-hd", overrides=ov) == 3800
        # Without matching model, provider-wide wins.
        assert resolve_chunk_max("OpenAI", model="tts-1", overrides=ov) == 4000

    def test_override_coerced_to_int(self):
        assert resolve_chunk_max("OpenAI", overrides={"OpenAI": "2500"}) == 2500

    def test_empty_overrides_treated_as_none(self):
        assert resolve_chunk_max("OpenAI", overrides={}) == 3500
        assert resolve_chunk_max("OpenAI", overrides=None) == 3500


class TestPolicySnapshot:
    def test_includes_built_in_policy(self):
        snap = policy_snapshot()
        assert snap["policy"]["OpenAI"] == 3500
        assert snap["policy"]["Kokoro"] == 2000
        assert snap["fallback"] == 3500

    def test_overrides_round_tripped(self):
        snap = policy_snapshot(overrides={"OpenAI": 4000})
        assert snap["overrides"] == {"OpenAI": 4000}

    def test_snapshot_is_a_copy_not_a_reference(self):
        snap = policy_snapshot()
        snap["policy"]["OpenAI"] = 1
        # Mutating the snapshot must not corrupt the module-level default.
        assert DEFAULT_CHUNK_MAX_BY_PROVIDER["OpenAI"] == 3500
