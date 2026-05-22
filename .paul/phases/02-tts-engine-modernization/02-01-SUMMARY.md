---
phase: 02-tts-engine-modernization
plan: 01
subsystem: tts-engine
tags: [openai-sdk, streaming, registry-integration, concurrency-clamp, structured-logging]
requires:
  - phase: 01-architecture-and-configuration
    provides: providers.PROVIDER_REGISTRY (MappingProxyType, immutable single source of truth)
provides:
  - tts_conversion.py wired to registry (no inline capability duplication)
  - with_streaming_response.create() context-manager streaming path (non-deprecated)
  - per-provider concurrency clamp with explicit policy log
  - structured chunk-level logging (provider, model, voice, attempt, elapsed) with key/text redaction
  - _safe_status_callback isolation (UI failure cannot abort synthesis)
  - settings ↔ registry fallback consistency invariant test
affects: [02.1-model-discovery, 04-gui, 06-ollama, 06.2-kokoro, 07-testing]
tech-stack:
  added: []
  patterns:
    - "Module-level compiled regex sourced from immutable registry pattern (cheap + fail-fast at import)"
    - "Three-branch concurrency-clamp log: clamped / using requested local / using requested hosted"
    - "_safe_status_callback wrapper: UI-callback exceptions logged WARNING + isolated from retry budget"
key-files:
  modified:
    - tts_conversion.py
    - tests/test_tts_conversion.py
  created:
    - .paul/phases/02-tts-engine-modernization/02-01-pytest.log
    - .paul/phases/02-tts-engine-modernization/02-01-SUMMARY.md
key-decisions:
  - "tts_conversion.py consumes providers.PROVIDER_REGISTRY; settings.py kept as parallel facade for OPENAI_FALLBACK_MODELS, drift-locked by test_fallback_consistency_settings_vs_registry"
  - "with_streaming_response context manager is the supported path; non-streaming create() actively asserted against in tests"
  - "Local provider concurrency capped at registry default; hosted provider honors user-requested value as-is"
patterns-established:
  - "Phase reads from registry; never mutates it; registry monkeypatch (Phase 1 audit S5) is the test-side injection method"
  - "Behavior shifts get inline # CHARACTERIZED comments naming the phase + reason"
duration: ~20min
started: 2026-05-21
completed: 2026-05-21
status: complete
---

# 02-01 SUMMARY — TTS Engine Modernization

## Outcome
`tts_conversion.py` now consumes `providers.PROVIDER_REGISTRY` as its single source of truth for OpenAI/Ollama capability lookups. Migrated `_write_openai_speech` from the deprecated `response.stream_to_file(...)` direct call to the non-deprecated `client.audio.speech.with_streaming_response.create(...)` context-manager pattern. Added concurrency clamp for local providers, structured chunk-level logging, and `status_callback` exception isolation. Regression suite: **161 passed in 0.64s, exit 0, zero DeprecationWarning**.

## AC Results

| AC | Title | Result |
|----|-------|--------|
| AC-1 | Registry-driven OpenAI model filter | PASS — `_filter_openai_tts_models` uses module-level `_OPENAI_MODEL_RE` + `cap.fallback_models` |
| AC-1b | Settings ↔ registry fallback consistency (audit M1) | PASS — `test_fallback_consistency_settings_vs_registry` |
| AC-2 | Registry-driven Ollama model-support validation | PASS — `_OLLAMA_MODEL_RE.search()` with explicit non-string guard |
| AC-3 | Non-deprecated SDK streaming API | PASS — `with_streaming_response.create(...)` context manager; fake stream writes bytes; explicit `catch_warnings` test passes |
| AC-4 | Concurrency clamp against registry default | PASS — three-branch log (clamped / under-cap-local / hosted); `TestConcurrencyClamp` verifies max_workers + log messages |
| AC-5 | Structured chunk-level logging | PASS — provider/model/voice/attempt logged; api_key + full chunk text NOT logged (`TestChunkLogging`) |
| AC-5b | status_callback exception isolation (audit S2) | PASS — `_safe_status_callback` wraps + logs WARNING; `TestStatusCallbackIsolation` |
| AC-6 | Existing characterization tests recharacterize cleanly | PASS — 2 `# CHARACTERIZED — Phase 2` comments on updated tests; no tests deleted |
| AC-7 | Full regression suite green | PASS — 161 tests, 0.64s, exit 0, no DeprecationWarning in log |
| AC-8 | No new third-party deps; providers.py untouched | PASS — `git diff providers.py` empty; no new imports beyond stdlib + `providers` (project module) |

## Files Modified

| File | Change |
|------|--------|
| `tts_conversion.py` | Imports added (`re`, `warnings`, `providers`); module-level compiled regex constants; `_filter_openai_tts_models` rewired to registry; `_validate_ollama_model_support` rewired with non-string guard; `_write_openai_speech` uses `with_streaming_response.create()`; `_safe_status_callback` helper added; `convert_text_chunk_to_speech` adds structured logging + safe callback; `convert_text_to_speech` adds three-branch concurrency clamp |
| `tests/test_tts_conversion.py` | Updated 2 tests with `# CHARACTERIZED — Phase 2` comments (`test_uppercase_tts_now_rejected`, `test_falls_back_when_no_tts_models`); added `test_fallback_consistency_settings_vs_registry` (M1), `test_uses_registry_pattern`, `test_non_string_inputs_return_false` (S4); added 5 new test classes: `TestConcurrencyClamp` (4 tests), `TestWithStreamingResponse` (2 tests, incl. S3 byte-writing + S5 catch_warnings), `TestChunkLogging`, `TestStatusCallbackIsolation` |
| `.paul/phases/02-tts-engine-modernization/02-01-pytest.log` | Verbatim regression run output (EXIT=0) |

## Behavior Shifts Characterized

| Test | Old behavior | New behavior | Why OK |
|------|-------------|-------------|--------|
| `test_uppercase_tts_now_rejected` (was `test_case_insensitive_match`) | Substring `"tts" in id.lower()` accepted `"TTS-MODEL-X"` | Anchored regex `^tts-[a-z0-9.-]+$` rejects uppercase → returns fallback list | Real OpenAI TTS model IDs are lowercase; uppercase was a false positive |
| `test_falls_back_when_no_tts_models` | Compared against `settings.OPENAI_FALLBACK_MODELS` | Compares against `providers.PROVIDER_REGISTRY["OpenAI"].fallback_models` | Single source of truth; `test_fallback_consistency_settings_vs_registry` enforces invariant |

## Test Count

| Phase | Tests | Δ |
|-------|------:|---|
| 00-02 baseline | 101 | — |
| 01-01 add | 145 | +44 |
| **02-01 add** | **161** | **+16** |

Floor (≥150) cleared.

## Audit Invariants Verified

- `git diff providers.py` returns no changes — Phase 1 immutability respected.
- `git diff requirements.txt environment.yml` returns no changes — no new deps.
- Phase 1 ast no-new-deps test on providers.py still passes (included in `161 passed`).
- No DeprecationWarning from openai in pytest log — explicit `catch_warnings` test + pytest.ini `filterwarnings = error` both validate.
- Single-source-of-truth invariant for fallback models locked by `test_fallback_consistency_settings_vs_registry` (audit M1).
- Registry monkeypatch pattern (Phase 1 audit S5) used in `TestConcurrencyClamp` and `TestWithStreamingResponse` — no registry mutation.

## Deferred (per audit)

| # | Item | Revisit |
|---|------|---------|
| D1 | Retry-everything semantics → transient vs non-transient exception allowlist | Phase 7 or Phase 2.x follow-up |
| D2 | Pin openai SDK version in requirements.txt | Phase 7 (release prep) |
| D3 | User-named voice log redaction | Phase 6.2 / 6.3 (when local voices become user-named) |

## Next Phase Readiness

Phase 2.1 (Model Discovery and Selection) is the natural next step. `list_openai_models` / `list_ollama_models` were intentionally untouched — Phase 2.1 owns the `Refresh Models` UI flow + curated allowlist polish. The registry-driven filter is now in place to receive their outputs.

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~20 min (PLAN + AUDIT + APPLY + UNIFY) |
| Started | 2026-05-21 |
| Completed | 2026-05-21 |
| Tasks | 3 / 3 completed PASS |
| Files modified | 2 (source) + 2 (artifacts) |
| Tests delta | +16 (145 → 161) |
| Suite wall time | 0.64s (well under 5.0s floor) |
| Exit code | 0 |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Keep `settings.OPENAI_FALLBACK_MODELS` as a parallel facade | Public config surface ergonomics + backwards compat for any external caller; drift defeated by M1 invariant test | Future contributors can change one and CI will fail loudly until both move together |
| Compile regex constants at module import (not per call) | Hot loop runs once per chunk × retry; per-call recompile is wasted cycles; fails fast if registry pattern is malformed | One-time import cost; cheap call site for every chunk |
| Three-branch concurrency clamp log | Auditor reads "clamped" and immediately knows the policy fired; informational lines distinguish hosted vs under-cap local | Post-incident reconstruction is single-glance |
| `_safe_status_callback` helper wraps every callback site | Tkinter "main thread not in main loop" after GUI close was the realistic trigger; UI bugs must not burn retry budget or fake "chunk failure" | Synthesis no longer reflects UI lifecycle |

## Task Commits

Per-task atomic commits NOT taken — Phase 2 follows the established project pattern (Phase 0 + Phase 1) of a single `feat(<phase>): ...` commit at transition. Transition workflow will land the phase commit.

| Task | Action |
|------|--------|
| Task 1: registry wiring + with_streaming_response | tts_conversion.py refactored (12 anchor points) |
| Task 2: tests | tests/test_tts_conversion.py updated + extended (+16 tests across 5 classes) |
| Task 3: regression + SUMMARY | pytest.log captured (161 passed, exit 0); SUMMARY written |

Phase commit: pending in transition workflow.

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------:|--------|
| Auto-fixed | 0 | — |
| Scope additions | 0 | — |
| Deferred | 3 | All from audit; logged below |

Plan executed as written. Audit upgrades had already landed in the plan pre-APPLY; no in-flight surprises.

### Deferred Items

| # | Item | Origin | Revisit |
|---|------|--------|---------|
| D1 | Retry-everything semantics (transient vs non-transient exception allowlist) | 02-01 audit | Phase 7 or Phase 2.x follow-up |
| D2 | Pin openai SDK version in requirements.txt | 02-01 audit | Phase 7 (release prep) |
| D3 | User-named voice log redaction | 02-01 audit | Phase 6.2 / 6.3 |

## Issues Encountered

None. APPLY passed every verify on the first attempt; no qualify gaps; no boundary violations attempted; no required-skill blocks.

## Loop Status

- PLAN ✓ (2026-05-21)
- AUDIT ✓ (2026-05-21 — conditionally acceptable, 1 must-have + 6 strongly-recommended applied)
- APPLY ✓ (2026-05-21 — 161 tests, 0.64s, exit 0)
- UNIFY ✓ (2026-05-21 — SUMMARY closed, STATE updated, phase ready for transition)

---
*Phase: 02-tts-engine-modernization, Plan: 01*
*Completed: 2026-05-21*
