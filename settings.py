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
    return settings
