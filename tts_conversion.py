import logging
import time
import requests
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor

from settings import OPENAI_FALLBACK_MODELS


def _filter_openai_tts_models(model_ids):
    valid = [model_id for model_id in model_ids if "tts" in model_id.lower()]
    return sorted(set(valid)) or OPENAI_FALLBACK_MODELS.copy()


def list_openai_models(api_key=None):
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key) if api_key else OpenAI()
        models = client.models.list()
        model_ids = [model.id for model in models.data]
        return _filter_openai_tts_models(model_ids)
    except Exception as exc:
        logging.warning("Falling back to built-in OpenAI model list: %s", exc)
        return OPENAI_FALLBACK_MODELS.copy()


def list_ollama_models(base_url):
    try:
        response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=10)
        response.raise_for_status()
        payload = response.json()
        models = payload.get("models", [])
        names = []
        for model in models:
            if isinstance(model, dict) and model.get("name"):
                names.append(model["name"])
        return sorted(set(names))
    except Exception as exc:
        logging.warning("Failed to load Ollama models: %s", exc)
        return []


def list_available_models(provider, api_key=None, ollama_base_url="http://localhost:11434"):
    if provider == "Ollama":
        return list_ollama_models(ollama_base_url)
    return list_openai_models(api_key)


def _write_openai_speech(chunk, file_path, api_key, model, voice, speed=1.0, response_format="mp3"):
    from openai import OpenAI

    client = OpenAI(api_key=api_key) if api_key else OpenAI()
    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=chunk,
        speed=speed,
        response_format=response_format,
    )
    response.stream_to_file(file_path)


def _validate_ollama_model_support(model_name):
    lowered = (model_name or "").lower()
    return any(token in lowered for token in ["bark", "kokoro", "tts", "speech"])


def convert_text_chunk_to_speech(chunk, index, settings, output_folder, timestamp, status_callback=None, retries=3):
    file_path = output_folder / f"chunk_part_{index + 1}_{timestamp}.{settings.response_format}"

    for attempt in range(1, retries + 1):
        try:
            if status_callback:
                status_callback(f"Converting chunk {index + 1} (attempt {attempt}/{retries})")

            if settings.provider == "Ollama":
                if not _validate_ollama_model_support(settings.model):
                    raise RuntimeError(
                        "Selected Ollama model does not appear to support speech generation. "
                        "Choose a local speech-capable model or switch provider to OpenAI."
                    )
                raise RuntimeError(
                    "Ollama model discovery is supported, but direct local speech synthesis is provider/model dependent and "
                    "not available through standard Ollama endpoints in this build."
                )

            _write_openai_speech(
                chunk=chunk,
                file_path=file_path,
                api_key=settings.openai_api_key,
                model=settings.model,
                voice=settings.voice,
                speed=settings.speed,
                response_format=settings.response_format,
            )
            logging.info("Chunk %s converted to speech and saved to %s.", index + 1, file_path)
            return file_path
        except Exception as exc:
            logging.error("Failed to convert chunk %s on attempt %s: %s", index + 1, attempt, exc)
            if attempt == retries:
                return None
            time.sleep(min(2 ** (attempt - 1), 4))


def convert_text_to_speech(text_chunks, settings, output_folder, timestamp, status_callback=None):
    audio_files = []
    max_workers = max(1, settings.max_concurrency)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(convert_text_chunk_to_speech, chunk, i, settings, output_folder, timestamp, status_callback)
            for i, chunk in enumerate(text_chunks)
        ]
        for future in futures:
            result = future.result()
            if result:
                audio_files.append(result)
    return audio_files

def concatenate_audio_files(audio_files, output_file_path):
    if not audio_files:
        raise ValueError("No audio files provided for concatenation.")

    combined = AudioSegment.empty()
    for file_path in audio_files:
        sound = AudioSegment.from_mp3(file_path)
        combined += sound
    combined.export(output_file_path, format="mp3")
    logging.info(f"All chunks concatenated into {output_file_path}")
