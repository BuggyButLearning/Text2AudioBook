"""
Per-(provider, model) chunk_max policy (Phase 8).

Research-backed defaults per provider, overridable via:
  1. Caller-passed `overrides` dict (CLI --chunk-max or programmatic call)
  2. config.json `chunk_overrides` map keyed by "Provider" or "Provider:model"
  3. Built-in DEFAULT_CHUNK_MAX_BY_PROVIDER

Precedence (most specific wins):
  caller_override > config[f"{provider}:{model}"] > config[provider] > built-in[provider] > FALLBACK

Why a separate module (not on ProviderCapability):
  providers.py is the Phase 1 immutable single-source-of-truth for provider
  CAPABILITY (kinds, voices, model regex, HF revision). chunk_max is a TUNING
  knob, not a capability — different deployments may legitimately pick
  different values for the same provider/model. Keeping it separate avoids
  registry churn and keeps the contract narrow.

Built-in defaults source:
  OpenAI:  4096-char hard ceiling per request (OpenAI TTS docs). 3500 leaves
           ~15% headroom for whitespace normalization rounding.
  Kokoro:  KPipeline auto-splits internally at 510 phonemes (see
           kokoro/pipeline.py waterfall on '!.?…' then ':;' then ',—').
           Feeding 2000-char app-level chunks reduces per-chunk model warmup
           while staying well above one paragraph.
  Ollama:  bark-style models commonly handle ~300 tokens (~1000 chars) before
           quality degrades. Conservative; user can override per-model.
"""

DEFAULT_CHUNK_MAX_BY_PROVIDER = {
    "OpenAI": 3500,
    "Kokoro": 2000,
    "Ollama": 1000,
}
DEFAULT_CHUNK_MAX_FALLBACK = 3500


def resolve_chunk_max(provider, model=None, overrides=None):
    """Return the effective chunk_max for (provider, model).

    `overrides` is a flat dict accepting two key shapes:
      - "Provider:model" (most specific)
      - "Provider"       (provider-wide)

    Falls back to built-in defaults then to DEFAULT_CHUNK_MAX_FALLBACK.
    Returns int.
    """
    overrides = overrides or {}
    if model:
        key = f"{provider}:{model}"
        if key in overrides:
            return int(overrides[key])
    if provider in overrides:
        return int(overrides[provider])
    if provider in DEFAULT_CHUNK_MAX_BY_PROVIDER:
        return DEFAULT_CHUNK_MAX_BY_PROVIDER[provider]
    return DEFAULT_CHUNK_MAX_FALLBACK


def policy_snapshot(overrides=None):
    """Return a dict suitable for `chunk-policy --json` output.

    Shape: {"policy": {provider: int}, "overrides": dict, "fallback": int}
    """
    return {
        "policy": dict(DEFAULT_CHUNK_MAX_BY_PROVIDER),
        "overrides": dict(overrides or {}),
        "fallback": DEFAULT_CHUNK_MAX_FALLBACK,
    }
