import json

import pytest

import settings
from settings import (
    OPENAI_FALLBACK_MODELS,
    OPENAI_VOICES,
    QUALITY_PRESETS,
    build_runtime_settings,
    coerce_float,
    coerce_int,
    load_openai_api_key,
    sanitize_output_filename,
)


def test_quality_presets_have_expected_keys():
    assert set(QUALITY_PRESETS.keys()) == {"Balanced", "Best Quality", "Fast"}


def test_quality_presets_have_model_and_speed():
    for name, preset in QUALITY_PRESETS.items():
        assert "model" in preset
        assert "speed" in preset
        assert isinstance(preset["speed"], (int, float))


def test_openai_voices_non_empty_list():
    assert isinstance(OPENAI_VOICES, list)
    assert len(OPENAI_VOICES) > 0
    assert "alloy" in OPENAI_VOICES


def test_openai_fallback_models_non_empty_list():
    assert isinstance(OPENAI_FALLBACK_MODELS, list)
    assert len(OPENAI_FALLBACK_MODELS) > 0


class TestLoadOpenAIApiKey:
    def test_env_var_wins_over_file(self, clean_env, tmp_key_file, monkeypatch):
        tmp_key_file("from-file")
        monkeypatch.setenv("OPENAI_API_KEY", "from-env")
        assert load_openai_api_key() == "from-env"

    def test_falls_back_to_key_file(self, clean_env, tmp_key_file):
        tmp_key_file("sk-fallback-123")
        assert load_openai_api_key() == "sk-fallback-123"

    def test_returns_none_when_neither_present(self, clean_env, no_key_file):
        assert load_openai_api_key() is None

    def test_strips_whitespace_from_env(self, clean_env, no_key_file, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "   spaced-key   ")
        assert load_openai_api_key() == "spaced-key"

    def test_empty_env_falls_through_to_file(self, clean_env, tmp_key_file, monkeypatch):
        tmp_key_file("file-key")
        monkeypatch.setenv("OPENAI_API_KEY", "")
        assert load_openai_api_key() == "file-key"

    def test_empty_file_returns_none(self, clean_env, tmp_key_file):
        tmp_key_file("")
        assert load_openai_api_key() is None


class TestSanitizeOutputFilename:
    def test_strips_forbidden_chars(self):
        assert sanitize_output_filename('foo<>:"/\\|?*bar') == "foo_bar"

    def test_collapses_whitespace(self):
        assert sanitize_output_filename("foo   \t  bar") == "foo bar"

    def test_truncates_at_120(self):
        result = sanitize_output_filename("a" * 500)
        assert len(result) == 120

    def test_strips_leading_trailing_dots_and_spaces(self):
        assert sanitize_output_filename("  .foo.  ") == "foo"

    # CHARACTERIZED — adversarial inputs (audit S3).
    # Phase 1 may harden these; current behavior is locked.
    def test_null_byte_passes_through(self):
        result = sanitize_output_filename("foo\x00bar")
        assert "\x00" in result

    def test_path_traversal_slashes_replaced(self):
        result = sanitize_output_filename("../../etc/passwd")
        assert "/" not in result
        assert "\\" not in result
        assert "etc" in result and "passwd" in result

    @pytest.mark.parametrize("name", ["CON", "NUL", "AUX", "PRN", "COM1", "LPT1"])
    def test_windows_reserved_names_pass_through(self, name):
        assert sanitize_output_filename(name) == name

    def test_empty_string_returns_empty(self):
        assert sanitize_output_filename("") == ""

    def test_whitespace_only_returns_empty(self):
        assert sanitize_output_filename("   ") == ""

    def test_very_long_input_truncated(self):
        long = "ab" * 5000
        result = sanitize_output_filename(long)
        assert len(result) == 120


class TestCoerceFloat:
    def test_parses_numeric_string(self):
        assert coerce_float("1.25", default=99.0) == 1.25

    def test_parses_int_string(self):
        assert coerce_float("3", default=99.0) == 3.0

    def test_returns_default_on_non_numeric(self):
        assert coerce_float("not-a-number", default=2.5) == 2.5

    def test_returns_default_on_none(self):
        assert coerce_float(None, default=1.5) == 1.5

    def test_accepts_actual_float(self):
        assert coerce_float(2.71, default=0.0) == 2.71


class TestCoerceInt:
    def test_parses_valid_int(self):
        assert coerce_int("4", default=1, minimum=1, maximum=8) == 4

    def test_clamps_to_max(self):
        assert coerce_int("100", default=1, minimum=1, maximum=8) == 8

    def test_clamps_to_min(self):
        assert coerce_int("0", default=2, minimum=1, maximum=8) == 1

    def test_returns_default_on_garbage(self):
        assert coerce_int("garbage", default=3, minimum=1, maximum=8) == 3

    def test_returns_default_on_none(self):
        assert coerce_int(None, default=5, minimum=1, maximum=8) == 5


class TestBuildRuntimeSettings:
    def test_defaults_when_no_config_and_no_env(self, clean_env, no_key_file, isolated_config):
        s = build_runtime_settings()
        assert s.provider == "OpenAI"
        assert s.quality_preset == "Balanced"
        assert s.voice == "alloy"
        assert s.model == QUALITY_PRESETS["Balanced"]["model"]
        assert s.openai_api_key is None
        assert s.response_format == "mp3"
        assert s.max_concurrency >= 1

    def test_argument_wins_over_default(self, clean_env, no_key_file, isolated_config):
        s = build_runtime_settings(provider="Ollama", voice="echo", model="custom-model")
        assert s.provider == "Ollama"
        assert s.voice == "echo"
        assert s.model == "custom-model"

    def test_quality_preset_drives_speed(self, clean_env, no_key_file, isolated_config):
        s = build_runtime_settings(quality_preset="Fast")
        assert s.speed == QUALITY_PRESETS["Fast"]["speed"]

    def test_config_file_supplies_defaults(self, clean_env, no_key_file, isolated_config):
        isolated_config.write_text(
            json.dumps({"default_provider": "Ollama", "default_voice": "fable"}),
            encoding="utf-8",
        )
        s = build_runtime_settings()
        assert s.provider == "Ollama"
        assert s.voice == "fable"

    def test_env_overrides_max_concurrency(self, clean_env, no_key_file, isolated_config, monkeypatch):
        monkeypatch.setenv("TTS_MAX_CONCURRENCY", "5")
        s = build_runtime_settings()
        assert s.max_concurrency == 5

    def test_env_overrides_ollama_base_url(self, clean_env, no_key_file, isolated_config, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://1.2.3.4:9999")
        s = build_runtime_settings()
        assert s.ollama_base_url == "http://1.2.3.4:9999"

    def test_unknown_quality_preset_falls_back_to_balanced(self, clean_env, no_key_file, isolated_config):
        s = build_runtime_settings(quality_preset="Nonexistent")
        assert s.model == QUALITY_PRESETS["Balanced"]["model"]
