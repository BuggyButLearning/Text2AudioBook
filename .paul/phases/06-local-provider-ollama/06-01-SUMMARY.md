---
phase: 06-local-provider-ollama
plan: 01
subsystem: providers
tags: [ollama, connectivity-probe, error-hint, kokoro-fallback]
requires:
  - phase: 02.1-model-discovery-and-selection
    provides: _discover_ollama / _canonical_ollama_url / requests-based HTTP probe
provides:
  - `ollama_reachable(base_url, timeout, request_fn)` connectivity helper
  - refined "ollama serve" hint in _discover_ollama ConnectionError branch
  - "use Kokoro provider (Phase 6.2)" hint in unsupported-TTS-endpoint error
affects: [04-gui (could surface reachability), 06.2-kokoro]
tech-stack:
  added: []
status: complete
duration: ~10min
started: 2026-05-22
completed: 2026-05-22
---

# 06-01 SUMMARY — Local Provider: Ollama

## Outcome
Added `ollama_reachable(base_url, timeout, request_fn)` connectivity probe that separates "Ollama not running" (start `ollama serve`) from "Ollama running but no TTS model" (pull a TTS-capable model). Refined `_discover_ollama` to surface the `ollama serve` hint on `ConnectionError` (distinct branch from generic exception). Refined `convert_text_chunk_to_speech` no-endpoint error to point user toward Kokoro as the v0.1 local synthesis path. Documented v0.1 contract: Ollama is discovery-only; synthesis lives in Kokoro (Phase 6.2). Regression: **251 passed in 0.93s, exit 0**.

## AC Results

| AC | Title | Result |
|----|-------|--------|
| AC-1 | `ollama_reachable` helper | PASS — `TestOllamaReachable` 6 tests cover 2xx, non-2xx, connect-refused, connect-timeout, URL canonicalization, default URL |
| AC-2 | `ollama serve` hint in discovery error | PASS — `TestOllamaConnectionRefinedError::test_connection_error_surfaces_serve_hint` |
| AC-3 | Kokoro hint in no-endpoint error | PASS — `test_ollama_no_endpoint_error_mentions_kokoro` |
| AC-4 | Tests | PASS — +8 tests (6 reachable + 1 refined error + 1 Kokoro hint) |
| AC-5 | Regression green | PASS — 251 tests in 0.93s |

## Files Modified

| File | Change |
|------|--------|
| `model_discovery.py` | Added `ollama_reachable(base_url, timeout, request_fn)`; refined `_discover_ollama` ConnectionError branch |
| `tts_conversion.py` | No-endpoint error now mentions Kokoro alternative |
| `tests/test_model_discovery.py` | +2 test classes (`TestOllamaReachable`, `TestOllamaConnectionRefinedError`) |
| `tests/test_tts_conversion.py` | +1 test (`test_ollama_no_endpoint_error_mentions_kokoro`) |

## Test Count

| Phase | Tests | Δ |
|-------|------:|---|
| 05-01 baseline | 243 | — |
| **06-01 add** | **251** | **+8** |

## Documented Limitation

Standard Ollama (as of v0.1 dev cycle) exposes a model-listing API (`/api/tags`) and a chat API but **no general TTS endpoint**. Phase 2.1 ships discovery; synthesis via Ollama requires either upstream changes or a custom shim — neither in v0.1 scope. **Kokoro (Phase 6.2) is the v0.1 local synthesis path.**

## Loop Status
PLAN ✓ AUDIT (inline) ✓ APPLY ✓ UNIFY ✓ (2026-05-22)
