"""
Model-discovery module (Phase 2.1).

Owns OpenAI / Ollama TTS-model listing. Returns a frozen DiscoveryResult with
explicit source labeling (LIVE / FALLBACK / EMPTY) so callers (GUI, tests,
audit log) can distinguish "fresh from the network" from "registry fallback
because the network failed" from "responded but yielded nothing useful".

Discovery is decoupled from synthesis: tts_conversion.py keeps thin shim
functions that delegate here, so callers like main.py don't need to change
their imports.

The Ollama path applies the registry's model_pattern as a curated allowlist
(PRD 14.1(a)) -- Ollama servers commonly report non-TTS models (llama3,
mistral) that are not synthesis-capable and must not appear in the UI dropdown.

Cache is per-(provider, canonical-identity) and only invalidates on explicit
invalidate_cache() -- designed for a "Refresh Models" UI button (Phase 4).
FALLBACK and EMPTY results are cached identically to LIVE; sticky semantics
until invalidate.

v0.1 contract: called from the main GUI thread only (synthesis ThreadPoolExecutor
does not touch discovery). Phase 4 owns threading; this module is not lock-guarded.
"""
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

import requests

import providers


class Source(str, Enum):
    LIVE = "live"
    FALLBACK = "fallback"
    EMPTY = "empty"


@dataclass(frozen=True)
class DiscoveryResult:
    provider: str
    models: tuple[str, ...]
    source: Source
    error: str | None = None


_OPENAI_MODEL_RE = re.compile(providers.PROVIDER_REGISTRY["OpenAI"].model_pattern)
_OLLAMA_MODEL_RE = re.compile(providers.PROVIDER_REGISTRY["Ollama"].model_pattern, re.IGNORECASE)


_OLLAMA_DEFAULT_URL = "http://localhost:11434"


_CACHE: dict[tuple[str, str | None], DiscoveryResult] = {}


def invalidate_cache(provider: str | None = None) -> None:
    if provider is None:
        _CACHE.clear()
        return
    for key in [k for k in _CACHE if k[0] == provider]:
        _CACHE.pop(key, None)


def _scrub_api_key(message: str, api_key: str | None) -> str:
    """Strip the api_key value from a log/error string before it escapes the function.

    Defensive: openai SDK errors can include URL-encoded request payloads that
    contain the Bearer token in some failure modes.
    """
    if not api_key or not message:
        return message
    return message.replace(api_key, "***REDACTED***")


def _canonical_ollama_url(base_url: str | None) -> str:
    return (base_url or _OLLAMA_DEFAULT_URL).rstrip("/")


def _discover_openai(api_key: str | None) -> DiscoveryResult:
    cap = providers.PROVIDER_REGISTRY["OpenAI"]
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key) if api_key else OpenAI()
        models = client.models.list()
        ids = [m.id for m in models.data]
        filtered = sorted({mid for mid in ids if _OPENAI_MODEL_RE.match(mid)})
        if filtered:
            return DiscoveryResult("OpenAI", tuple(filtered), Source.LIVE, None)
        logging.info("OpenAI discovery: API responded OK but no TTS models matched allowlist")
        return DiscoveryResult("OpenAI", (), Source.EMPTY, "no models matched allowlist")
    except Exception as exc:
        scrubbed = _scrub_api_key(str(exc), api_key)
        logging.warning("OpenAI discovery failed; using registry fallback: %s", scrubbed)
        return DiscoveryResult("OpenAI", tuple(cap.fallback_models), Source.FALLBACK, scrubbed)


def _discover_ollama(canonical_url: str) -> DiscoveryResult:
    try:
        response = requests.get(f"{canonical_url}/api/tags", timeout=10)
        response.raise_for_status()
        payload = response.json()
        entries = payload.get("models", []) if isinstance(payload, dict) else []
        names = []
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("name"), str):
                names.append(entry["name"])
        total = len(names)
        filtered = sorted({n for n in names if _OLLAMA_MODEL_RE.search(n)})
        logging.info(
            "Ollama discovery: %d models reported, %d after registry filter", total, len(filtered)
        )
        if filtered:
            return DiscoveryResult("Ollama", tuple(filtered), Source.LIVE, None)
        if total > 0:
            return DiscoveryResult("Ollama", (), Source.EMPTY, "no models matched registry allowlist")
        return DiscoveryResult("Ollama", (), Source.EMPTY, None)
    except Exception as exc:
        logging.warning("Ollama discovery failed: %s", exc)
        return DiscoveryResult("Ollama", (), Source.EMPTY, str(exc))


def discover_models(
    provider: str,
    *,
    api_key: str | None = None,
    ollama_base_url: str | None = None,
    use_cache: bool = True,
) -> DiscoveryResult:
    if provider not in providers.PROVIDER_REGISTRY:
        return DiscoveryResult(provider, (), Source.EMPTY, "unknown provider")

    if provider == "Ollama":
        identity: str | None = _canonical_ollama_url(ollama_base_url)
    elif provider == "OpenAI":
        identity = api_key
    else:
        identity = None

    cache_key = (provider, identity)

    if use_cache and cache_key in _CACHE:
        return _CACHE[cache_key]

    if provider == "OpenAI":
        result = _discover_openai(api_key)
    elif provider == "Ollama":
        result = _discover_ollama(identity)  # type: ignore[arg-type]
    else:
        cap = providers.PROVIDER_REGISTRY[provider]
        result = DiscoveryResult(provider, tuple(cap.fallback_models), Source.FALLBACK, None)

    _CACHE[cache_key] = result
    return result
