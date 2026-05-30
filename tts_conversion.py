import logging
import re
import time
import warnings  # noqa: F401  (kept for parity with deprecation-warning test scaffolding)
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor

import providers


_OPENAI_MODEL_RE = re.compile(providers.PROVIDER_REGISTRY["OpenAI"].model_pattern)
_OLLAMA_MODEL_RE = re.compile(providers.PROVIDER_REGISTRY["Ollama"].model_pattern, re.IGNORECASE)


def _filter_openai_tts_models(model_ids):
    cap = providers.PROVIDER_REGISTRY["OpenAI"]
    valid = sorted({mid for mid in model_ids if _OPENAI_MODEL_RE.match(mid)})
    return valid or list(cap.fallback_models)


def list_openai_models(api_key=None):
    from model_discovery import discover_models
    return list(discover_models("OpenAI", api_key=api_key).models)


def list_ollama_models(base_url):
    from model_discovery import discover_models
    return list(discover_models("Ollama", ollama_base_url=base_url).models)


def list_available_models(provider, api_key=None, ollama_base_url="http://localhost:11434"):
    from model_discovery import discover_models
    return list(discover_models(provider, api_key=api_key, ollama_base_url=ollama_base_url).models)


def _write_openai_speech(chunk, file_path, api_key, model, voice, speed=1.0, response_format="mp3"):
    from openai import OpenAI

    client = OpenAI(api_key=api_key) if api_key else OpenAI()
    with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice,
        input=chunk,
        speed=speed,
        response_format=response_format,
    ) as response:
        response.stream_to_file(file_path)


def _validate_ollama_model_support(model_name):
    if not isinstance(model_name, str) or not model_name:
        return False
    return _OLLAMA_MODEL_RE.search(model_name) is not None


def _safe_status_callback(callback, message):
    if callback is None:
        return
    try:
        callback(message)
    except Exception as exc:
        logging.warning("status_callback raised: %s", exc)


def convert_text_chunk_to_speech(chunk, index, settings, output_folder, timestamp, status_callback=None, retries=3):
    file_path = output_folder / f"chunk_part_{index + 1}_{timestamp}.{settings.response_format}"
    preview = (chunk[:80] + "...") if len(chunk) > 80 else chunk
    preview = preview.replace("\n", " ")

    for attempt in range(1, retries + 1):
        started = time.monotonic()
        try:
            _safe_status_callback(
                status_callback,
                f"Converting chunk {index + 1} (attempt {attempt}/{retries})",
            )
            logging.info(
                "chunk %d attempt %d/%d provider=%s model=%s voice=%s preview=%r",
                index + 1, attempt, retries, settings.provider, settings.model, settings.voice, preview,
            )

            if settings.provider == "Ollama":
                if not _validate_ollama_model_support(settings.model):
                    raise RuntimeError(
                        "Selected Ollama model does not appear to support speech generation. "
                        "Choose a local speech-capable model or switch provider to OpenAI."
                    )
                raise RuntimeError(
                    "Ollama model discovery is supported, but direct local speech synthesis is "
                    "provider/model dependent and not available through standard Ollama endpoints in "
                    "this build. For local synthesis, use the Kokoro provider."
                )

            if settings.provider == "Kokoro":
                # Phase 6.2: synthesize WAV via kokoro, convert to MP3 so the
                # downstream concatenation stays MP3-uniform.
                from kokoro_synthesis import _write_kokoro_speech, _convert_wav_to_mp3
                wav_path = file_path.with_suffix(".wav")
                mp3_path = file_path.with_suffix(".mp3")
                _write_kokoro_speech(
                    chunk=chunk,
                    wav_path=wav_path,
                    model=settings.model,
                    voice=settings.voice,
                    speed=settings.speed,
                )
                _convert_wav_to_mp3(wav_path, mp3_path)
                try:
                    wav_path.unlink()
                except OSError:
                    pass
                elapsed = time.monotonic() - started
                logging.info("kokoro chunk %d converted in %.2fs -> %s", index + 1, elapsed, mp3_path)
                return mp3_path

            _write_openai_speech(
                chunk=chunk,
                file_path=file_path,
                api_key=settings.openai_api_key,
                model=settings.model,
                voice=settings.voice,
                speed=settings.speed,
                response_format=settings.response_format,
            )
            elapsed = time.monotonic() - started
            logging.info("chunk %d converted in %.2fs -> %s", index + 1, elapsed, file_path)
            return file_path
        except Exception as exc:
            logging.error("chunk %d attempt %d failed: %s", index + 1, attempt, exc)
            if attempt == retries:
                logging.error("chunk %d exhausted retries; returning None", index + 1)
                return None
            time.sleep(min(2 ** (attempt - 1), 4))


def convert_text_to_speech(text_chunks, settings, output_folder, timestamp, status_callback=None):
    audio_files = []
    requested = max(1, settings.max_concurrency)
    cap = providers.get_provider_capability(settings.provider)
    if cap and cap.kind in ("local-api", "local-hf") and requested > cap.default_max_concurrency:
        max_workers = cap.default_max_concurrency
        logging.info(
            "clamped requested=%d to registry-default=%d for local provider %s (chunks=%d)",
            requested, max_workers, settings.provider, len(text_chunks),
        )
    elif cap and cap.kind in ("local-api", "local-hf"):
        max_workers = requested
        logging.info(
            "using requested concurrency=%d for local provider %s (under cap %d, chunks=%d)",
            max_workers, settings.provider, cap.default_max_concurrency, len(text_chunks),
        )
    else:
        max_workers = requested
        logging.info(
            "using requested concurrency=%d for provider %s (chunks=%d)",
            max_workers, settings.provider, len(text_chunks),
        )
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
