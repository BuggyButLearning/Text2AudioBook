"""
Provider capability registry for Text2AudioBook (v0.1 milestone).

VibeVoice intentionally omitted from the v0.1 registry per Phase 0 §14.2(1)
decision (no GPU assumed in v0.1 target machines). v0.2 Phase 6.3 will add
a VibeVoice entry; do NOT add it earlier without re-opening that decision.

This module is the SINGLE SOURCE OF TRUTH for provider capabilities.
settings.py is a thin facade and reads from here.
"""
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, Mapping


MILESTONE = "v0.1"


@dataclass(frozen=True)
class ProviderCapability:
    name: str
    kind: Literal["hosted", "local-api", "local-hf"]
    voices: tuple[str, ...]
    model_pattern: str
    fallback_models: tuple[str, ...]
    output_format: Literal["mp3", "wav"]
    default_max_concurrency: int
    hf_model_repo: str | None = None
    hf_model_revision: str | None = None
    is_available_in_v01: bool = True


_ALLOWED_REVISION_LITERALS = {"main", "master"}
_SHA_RE = re.compile(r"[0-9a-f]{40,64}")
_SEMVER_RE = re.compile(r"v?\d+\.\d+\.\d+([+-][\w.]+)?")


def _validate_revision(rev, *, repo):
    if rev is None:
        return
    if _SHA_RE.fullmatch(rev):
        return
    if _SEMVER_RE.fullmatch(rev):
        return
    if rev in _ALLOWED_REVISION_LITERALS:
        return
    raise ValueError(
        f"HF model revision for {repo!r} does not match accepted schema "
        f"(SHA / semver / 'main'|'master'): {rev!r}"
    )


_RAW_REGISTRY: dict[str, ProviderCapability] = {
    "OpenAI": ProviderCapability(
        name="OpenAI",
        kind="hosted",
        voices=("alloy", "echo", "fable", "onyx", "nova", "shimmer"),
        model_pattern=r"^tts-[a-z0-9.-]+$",
        fallback_models=("tts-1", "tts-1-hd"),
        output_format="mp3",
        default_max_concurrency=2,
        hf_model_repo=None,
        hf_model_revision=None,
    ),
    "Ollama": ProviderCapability(
        name="Ollama",
        kind="local-api",
        voices=(),
        model_pattern=r".*(bark|kokoro|tts|speech).*",
        fallback_models=(),
        output_format="mp3",
        default_max_concurrency=1,
        hf_model_repo=None,
        hf_model_revision=None,
    ),
    "Kokoro": ProviderCapability(
        name="Kokoro",
        kind="local-hf",
        # 20 of 54 voices shipped in v0.1 (American English subset). Phase 6.2 may expand.
        voices=(
            "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica",
            "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
            "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael",
            "am_onyx", "am_puck", "am_santa",
        ),
        model_pattern=r"^kokoro(-[a-z0-9-]+)?$",
        fallback_models=("kokoro-82m",),
        output_format="wav",
        default_max_concurrency=1,
        hf_model_repo="hexgrad/Kokoro-82M",
        hf_model_revision="496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4",
    ),
}


for _cap in _RAW_REGISTRY.values():
    try:
        re.compile(_cap.model_pattern)
    except re.error as exc:
        raise ValueError(
            f"Invalid model_pattern regex for provider {_cap.name!r}: {exc}"
        ) from exc
    _validate_revision(_cap.hf_model_revision, repo=_cap.hf_model_repo or _cap.name)


PROVIDER_REGISTRY: Mapping[str, ProviderCapability] = MappingProxyType(_RAW_REGISTRY)


def get_provider_capability(name):
    if not isinstance(name, str) or not name:
        return None
    return PROVIDER_REGISTRY.get(name)


def list_providers():
    return tuple(PROVIDER_REGISTRY.keys())
