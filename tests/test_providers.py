import ast
import dataclasses
import pathlib
import re

import pytest

import providers
from providers import (
    MILESTONE,
    PROVIDER_REGISTRY,
    ProviderCapability,
    get_provider_capability,
    list_providers,
)


PROVIDERS_PATH = pathlib.Path(providers.__file__)


class TestRegistryContents:
    def test_registry_has_exactly_three_entries(self):
        assert len(PROVIDER_REGISTRY) == 3

    def test_registry_keys_are_expected_set(self):
        assert set(PROVIDER_REGISTRY.keys()) == {"OpenAI", "Ollama", "Kokoro"}

    def test_vibevoice_not_in_v01_registry(self):
        assert "VibeVoice" not in PROVIDER_REGISTRY

    def test_list_providers_returns_display_order(self):
        assert list_providers() == ("OpenAI", "Ollama", "Kokoro")

    @pytest.mark.parametrize("name", list(PROVIDER_REGISTRY.keys()))
    def test_each_capability_is_available_in_v01(self, name):
        assert PROVIDER_REGISTRY[name].is_available_in_v01 is True


class TestOpenAICapability:
    @pytest.fixture
    def cap(self):
        return PROVIDER_REGISTRY["OpenAI"]

    def test_kind_is_hosted(self, cap):
        assert cap.kind == "hosted"

    def test_default_max_concurrency_at_least_two(self, cap):
        assert cap.default_max_concurrency >= 2

    def test_output_format_mp3(self, cap):
        assert cap.output_format == "mp3"

    def test_alloy_in_voices(self, cap):
        assert "alloy" in cap.voices

    def test_no_hf_revision(self, cap):
        assert cap.hf_model_repo is None
        assert cap.hf_model_revision is None


class TestOllamaCapability:
    @pytest.fixture
    def cap(self):
        return PROVIDER_REGISTRY["Ollama"]

    def test_kind_is_local_api(self, cap):
        assert cap.kind == "local-api"

    def test_default_max_concurrency_one(self, cap):
        assert cap.default_max_concurrency == 1

    def test_voices_empty(self, cap):
        assert cap.voices == ()

    def test_model_pattern_matches_speech_keywords(self, cap):
        regex = re.compile(cap.model_pattern)
        assert regex.match("bark-tts")
        assert regex.match("kokoro-local")
        assert not regex.match("llama3")


class TestKokoroCapability:
    @pytest.fixture
    def cap(self):
        return PROVIDER_REGISTRY["Kokoro"]

    def test_kind_is_local_hf(self, cap):
        assert cap.kind == "local-hf"

    def test_default_max_concurrency_one(self, cap):
        assert cap.default_max_concurrency == 1

    def test_output_format_wav(self, cap):
        assert cap.output_format == "wav"

    def test_af_heart_in_voices(self, cap):
        assert "af_heart" in cap.voices

    def test_hf_model_repo_set(self, cap):
        assert cap.hf_model_repo == "hexgrad/Kokoro-82M"

    def test_hf_model_revision_is_sha_or_tag(self, cap):
        rev = cap.hf_model_revision
        assert rev is not None
        # Git SHA is exactly 40 hex chars; broader 40-64 range let a 64-char fake
        # slip through and 404 against HF. Tightened to exact git SHA length.
        sha_match = re.fullmatch(r"[0-9a-f]{40}", rev)
        semver_match = re.fullmatch(r"v?\d+\.\d+\.\d+([+-][\w.]+)?", rev)
        literal_match = rev in {"main", "master"}
        assert sha_match or semver_match or literal_match, f"unexpected revision schema: {rev!r}"

    def test_hf_model_revision_is_exactly_40_hex_chars(self, cap):
        """Regression guard: 2026-05-22 the pinned revision was a 64-char
        SHA256-shaped fake that 404'd against HF (Revision Not Found).
        Git SHAs are exactly 40 hex chars."""
        rev = cap.hf_model_revision
        # Only enforce length-check on values that LOOK like a SHA (all-hex).
        if rev and all(c in "0123456789abcdef" for c in rev):
            assert len(rev) == 40, (
                f"git SHA must be exactly 40 hex chars; got {len(rev)} chars: {rev!r}. "
                "If you intended a different value (semver tag, branch literal), "
                "use that form instead of an all-hex non-40-char string."
            )

    def test_pinned_revision_is_the_known_good_value(self, cap):
        """Locks the specific SHA fetched from HF 2026-05-22. Bumping requires
        re-fetching from https://huggingface.co/api/models/hexgrad/Kokoro-82M
        and updating this assertion together with the registry value."""
        assert cap.hf_model_revision == "f3ff3571791e39611d31c381e3a41a3af07b4987"


class TestRevisionValidator:
    """Regression guards on providers._validate_revision so future fakes blow up
    at import time (not at first download)."""

    def test_64_char_hex_now_rejected(self):
        """Bug 2026-05-22: a 64-char SHA256-shaped value passed the old
        [40,64] regex and 404'd against HF. Now: 40 chars exact."""
        import providers
        with pytest.raises(ValueError, match="does not match accepted schema"):
            providers._validate_revision(
                "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4",
                repo="hexgrad/Kokoro-82M",
            )

    def test_40_char_git_sha_accepted(self):
        import providers
        providers._validate_revision("f3ff3571791e39611d31c381e3a41a3af07b4987", repo="x/y")

    def test_main_literal_accepted(self):
        import providers
        providers._validate_revision("main", repo="x/y")

    def test_semver_accepted(self):
        import providers
        providers._validate_revision("v1.2.3", repo="x/y")

    def test_none_accepted(self):
        import providers
        providers._validate_revision(None, repo="x/y")

    def test_39_chars_rejected(self):
        import providers
        with pytest.raises(ValueError):
            providers._validate_revision("a" * 39, repo="x/y")

    def test_41_chars_rejected(self):
        import providers
        with pytest.raises(ValueError):
            providers._validate_revision("a" * 41, repo="x/y")

    def test_uppercase_hex_rejected(self):
        """git SHAs are lowercase hex; uppercase indicates fabrication."""
        import providers
        with pytest.raises(ValueError):
            providers._validate_revision("F" * 40, repo="x/y")


class TestGetProviderCapability:
    def test_returns_capability_for_known_provider(self):
        assert get_provider_capability("OpenAI").name == "OpenAI"

    def test_case_sensitive_returns_none(self):
        assert get_provider_capability("openai") is None

    def test_unknown_returns_none(self):
        assert get_provider_capability("Nonexistent") is None

    def test_none_returns_none(self):
        assert get_provider_capability(None) is None

    def test_empty_string_returns_none(self):
        assert get_provider_capability("") is None

    def test_non_string_returns_none(self):
        assert get_provider_capability(123) is None


class TestRegistryImmutability:
    """Audit M3: PROVIDER_REGISTRY is MappingProxyType — mutation must fail."""

    def test_setitem_raises_type_error(self):
        with pytest.raises(TypeError):
            PROVIDER_REGISTRY["Fake"] = "anything"  # type: ignore[index]

    def test_delitem_raises_type_error(self):
        with pytest.raises(TypeError):
            del PROVIDER_REGISTRY["OpenAI"]  # type: ignore[attr-defined]


class TestCapabilityImmutability:
    """Audit S3: ProviderCapability is frozen — field mutation must raise FrozenInstanceError."""

    def test_field_mutation_raises(self):
        cap = PROVIDER_REGISTRY["OpenAI"]
        with pytest.raises(dataclasses.FrozenInstanceError):
            cap.name = "X"  # type: ignore[misc]

    def test_voices_tuple_unmutable(self):
        cap = PROVIDER_REGISTRY["OpenAI"]
        with pytest.raises(TypeError):
            cap.voices[0] = "X"  # type: ignore[index]


class TestMilestoneAndDocstring:
    """Audit S1: milestone constraint surfaced in code and docs."""

    def test_milestone_constant(self):
        assert MILESTONE == "v0.1"

    def test_docstring_mentions_vibevoice_omission(self):
        assert providers.__doc__ is not None
        assert "VibeVoice intentionally omitted" in providers.__doc__


class TestNoNewDependencies:
    """Audit S4: providers.py must use stdlib only."""

    ALLOWED_IMPORTS = {
        "dataclasses",
        "typing",
        "re",
        "types",
    }

    def test_top_level_imports_are_stdlib_only(self):
        source = PROVIDERS_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.add(node.module.split(".")[0])
        unexpected = imported - self.ALLOWED_IMPORTS
        assert not unexpected, f"providers.py introduced unexpected imports: {unexpected}"


class TestMonkeypatchPattern:
    """Audit S5: canonical pattern for injecting fake providers in tests."""

    def test_monkeypatch_get_provider_capability(self, monkeypatch):
        fake_cap = ProviderCapability(
            name="FakeProvider",
            kind="local-api",
            voices=(),
            model_pattern=r".*",
            fallback_models=(),
            output_format="mp3",
            default_max_concurrency=1,
        )

        def fake_lookup(name):
            if name == "FakeProvider":
                return fake_cap
            return None

        monkeypatch.setattr(providers, "get_provider_capability", fake_lookup)
        assert providers.get_provider_capability("FakeProvider").name == "FakeProvider"
        assert providers.get_provider_capability("OpenAI") is None  # real lookup masked
