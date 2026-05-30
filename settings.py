import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCRIPT_DIRECTORY = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIRECTORY / "config.json"
KEY_FILE = SCRIPT_DIRECTORY / "key.txt"
DEFAULT_OUTPUT_FOLDER = SCRIPT_DIRECTORY / "output"

OPENAI_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
QUALITY_PRESETS = {
    "Balanced": {"model": "tts-1", "speed": 1.0},
    "Best Quality": {"model": "tts-1-hd", "speed": 1.0},
    "Fast": {"model": "tts-1", "speed": 1.15},
}
OPENAI_FALLBACK_MODELS = ["tts-1", "tts-1-hd"]

HF_HOME_DEFAULT = Path.home() / ".cache" / "huggingface"


@dataclass
class RuntimeSettings:
    provider: str = "OpenAI"
    quality_preset: str = "Balanced"
    model: str = "tts-1"
    voice: str = "alloy"
    speed: float = 1.0
    output_folder: Path = DEFAULT_OUTPUT_FOLDER
    openai_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    max_concurrency: int = 2
    response_format: str = "mp3"
    chunk_max: int | None = None  # Phase 8: resolved via chunk_policy; None = use default


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except Exception as exc:
        logging.warning("Failed to load config.json: %s", exc)
        return {}


def save_config(config: dict[str, Any]) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)


def load_openai_api_key() -> str | None:
    env_key = os.getenv("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key

    if KEY_FILE.exists():
        try:
            with open(KEY_FILE, "r", encoding="utf-8") as file:
                key = file.readline().strip()
                return key or None
        except Exception as exc:
            logging.warning("Failed to read key.txt fallback: %s", exc)
    return None


def sanitize_output_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", value.strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:120]


def coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def coerce_int(value: Any, default: int, minimum: int = 1, maximum: int = 8) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def build_runtime_settings(
    provider: str | None = None,
    quality_preset: str | None = None,
    model: str | None = None,
    voice: str | None = None,
    output_folder: str | Path | None = None,
    chunk_max: int | None = None,
) -> RuntimeSettings:
    config = load_config()
    preset_name = quality_preset or config.get("default_quality_preset") or "Balanced"
    preset = QUALITY_PRESETS.get(preset_name, QUALITY_PRESETS["Balanced"])

    settings = RuntimeSettings(
        provider=provider or config.get("default_provider") or "OpenAI",
        quality_preset=preset_name,
        model=model or config.get("default_model") or preset["model"],
        voice=voice or config.get("default_voice") or "alloy",
        speed=coerce_float(config.get("default_speed"), preset["speed"]),
        output_folder=Path(output_folder or config.get("output_folder") or DEFAULT_OUTPUT_FOLDER),
        openai_api_key=load_openai_api_key(),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", config.get("ollama_base_url") or "http://localhost:11434"),
        max_concurrency=coerce_int(os.getenv("TTS_MAX_CONCURRENCY", config.get("max_concurrency")), 2),
        response_format=config.get("response_format") or "mp3",
    )

    if model:
        settings.model = model
    if voice:
        settings.voice = voice
    if quality_preset in QUALITY_PRESETS:
        settings.speed = QUALITY_PRESETS[quality_preset]["speed"]

    # Phase 8: resolve chunk_max from explicit arg -> config[chunk_overrides] -> built-in policy.
    if chunk_max is not None:
        settings.chunk_max = int(chunk_max)
    else:
        from chunk_policy import resolve_chunk_max
        settings.chunk_max = resolve_chunk_max(
            settings.provider, model=settings.model,
            overrides=config.get("chunk_overrides") or {},
        )
    return settings


def get_provider_capability(name):
    """Thin facade over providers.get_provider_capability — keep settings.py as the public config surface."""
    import providers
    return providers.get_provider_capability(name)


def _hf_model_revisions():
    import providers
    return {
        cap.hf_model_repo: cap.hf_model_revision
        for cap in providers.PROVIDER_REGISTRY.values()
        if cap.hf_model_repo and cap.hf_model_revision
    }


class _HFModelRevisionsView:
    def __getitem__(self, key):
        return _hf_model_revisions()[key]

    def get(self, key, default=None):
        return _hf_model_revisions().get(key, default)

    def __contains__(self, key):
        return key in _hf_model_revisions()

    def __iter__(self):
        return iter(_hf_model_revisions())

    def keys(self):
        return _hf_model_revisions().keys()

    def values(self):
        return _hf_model_revisions().values()

    def items(self):
        return _hf_model_revisions().items()

    def __len__(self):
        return len(_hf_model_revisions())

    def __repr__(self):
        return f"_HFModelRevisionsView({_hf_model_revisions()!r})"


HF_MODEL_REVISIONS = _HFModelRevisionsView()
