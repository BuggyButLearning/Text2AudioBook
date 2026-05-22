---
phase: 03-text-processing-improvements
plan: 01
subsystem: text-processing
tags: [chunking, position-metadata, char-budget, unicode, openai-limit]
requires:
  - phase: 00-discovery-and-approval
    provides: characterization regression baseline (existing test_text_processing.py tests)
provides:
  - OPENAI_TTS_MAX_INPUT_CHARS / DEFAULT_CHUNK_MAX module-level constants
  - position-accuracy fix (forward-cursor pattern; duplicate substrings get distinct ordered positions)
  - reconstruction-invariant contract for positions[i] (locked via test)
  - _locate DEBUG-log on fallback path (defensive observability)
  - unicode + edge-case + budget test coverage
affects: [04-gui (progress bar can trust positions[]), 06-ollama, 06.2-kokoro, 07-testing]
tech-stack:
  added: []
  patterns:
    - "Forward-only find_cursor in chunker prevents duplicate-substring collapse"
    - "Module-level named char-budget constants over inline magic numbers"
    - "Hard-split pieces use arithmetic position (sentence_start + hard_start) -- exact, no find() needed"
key-files:
  modified:
    - text_processing.py
    - tests/test_text_processing.py
  created:
    - .paul/phases/03-text-processing-improvements/03-01-pytest.log
    - .paul/phases/03-text-processing-improvements/03-01-SUMMARY.md
key-decisions:
  - "char-budget constants live in text_processing.py (not providers.py / not settings.py); per-provider generalization deferred to Phase 6.2 / 7 when local providers reveal their own limits"
  - "Position-accuracy fix classified as bug fix, not behavior shift; no existing test characterized; pre-existing tests remain valid"
  - "Reconstruction-invariant test pattern: whitespace-tolerant first-20-char prefix match with source-slice length floor + non-empty-chunk assertion (audit S4)"
patterns-established:
  - "When a module manages a finite resource bounded by an upstream limit, expose both the upstream ceiling and the safe-margin default as named constants"
  - "When iterating a substring search over text that may contain duplicates, use a monotonically-advancing cursor so repeated phrases resolve to distinct offsets in source order"
duration: ~15min
started: 2026-05-21
completed: 2026-05-21
status: complete
---

# 03-01 SUMMARY — Text Processing Improvements

## Outcome
Hardened `text_processing.split_text` against the duplicate-substring position bug (forward-only `find_cursor` + `_locate` helper). Added named char-budget constants `OPENAI_TTS_MAX_INPUT_CHARS = 4096` and `DEFAULT_CHUNK_MAX = 3500` with safe-margin invariant test. Added reconstruction-style position tests + unicode + edge-case coverage. Regression suite: **195 passed in 0.76s, exit 0, zero DeprecationWarning, zero new third-party deps**.

## AC Results

| AC | Title | Result |
|----|-------|--------|
| AC-1 | Module-level char-budget constants | PASS — `TestSplitTextBudget` (4 tests): safe-margin invariant, OpenAI 4096 anchor, default parameter binds to constant, no chunk exceeds limit on long input |
| AC-2 | Position-accuracy fix for repeated substrings | PASS — `test_duplicate_paragraphs_get_distinct_positions`: two `"He said."` paragraphs land at distinct source-ordered positions; `find_cursor` forward-only |
| AC-3 | Reconstruction invariant | PASS — `_reconstruct_check` with audit S4 hardening (non-empty chunks + source-slice length floor); 3 reconstruction tests across short / multi-paragraph / hard-split fixtures |
| AC-4 | Edge-case coverage | PASS — `TestSplitTextEdgeCases` (6 tests): unicode (Café, François, em-dash), blank-line interspersing (both no-split and forced-split cases), exact-max-length boundary, whitespace-only input, long-no-punctuation hard-split under limit |
| AC-5 | Existing tests stay green; new tests added | PASS — 195 tests total (180 baseline incl. text_processing existing 20 + Phase 0-2.1 prior 160 = wait baseline was 179, +16 new here = 195); all 20 pre-existing text_processing tests pass UNCHANGED (no characterization needed); 0.76s wall < 5.0s; exit 0 |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `text_processing.py` | Modified | Added OPENAI_TTS_MAX_INPUT_CHARS + DEFAULT_CHUNK_MAX constants; refactored split_text body to forward-cursor + _locate helper; added DEBUG log on fallback path |
| `tests/test_text_processing.py` | Modified (additive only) | Added DEFAULT_CHUNK_MAX + OPENAI_TTS_MAX_INPUT_CHARS to imports; appended 3 new test classes: `TestSplitTextBudget` (4), `TestSplitTextPositions` (6), `TestSplitTextEdgeCases` (6) |
| `.paul/phases/03-text-processing-improvements/03-01-pytest.log` | Created | Verbatim regression run output (EXIT=0) |

## Behavior Shifts Characterized

None. The position-accuracy fix is classified as a bug fix, not a behavior shift; all 20 pre-existing `test_text_processing.py` tests pass UNCHANGED. No `# CHARACTERIZED — Phase 3` comments added.

## Test Count

| Phase | Tests | Δ |
|-------|------:|---|
| 00-02 baseline | 101 | — |
| 01-01 add | 145 | +44 |
| 02-01 add | 161 | +16 |
| 02.1-01 add | 179 | +18 |
| **03-01 add** | **195** | **+16** |

Floor (≥ 194) cleared.

## Audit Invariants Verified

- `git diff providers.py settings.py model_discovery.py tts_conversion.py main.py` returns no changes.
- `git diff requirements.txt environment.yml` returns no changes — no new deps.
- No DeprecationWarning, no SyntaxWarning in pytest log.
- Audit S1 (test count): corrected baseline 20 (not 12); regression floor ≥ 194 cleared at 195.
- Audit S2 (defensive observability): `_locate` DEBUG-log present at line 53 of text_processing.py; visible under `--log-cli-level=DEBUG`.
- Audit S3 (distinct-positions trap): `test_distinct_chunks_have_distinct_positions` catches the [0,0,0] regression path.
- Audit S4 (reconstruction hardening): `_reconstruct_check` enforces non-empty chunks + source-slice length floor.

## Deferred (per audit)

| # | Item | Revisit |
|---|------|---------|
| D1 | O(n²) `text.find` for very large inputs | Phase 7 / future optimization (bounded by v0.1 audiobook size <500KB) |
| D2 | Full-list memory build (generator-style chunking) | Phase 7+ (real architectural change; out of v0.1 scope) |
| D3 | Per-provider char limits | Phase 6 / 6.2 territory (Kokoro / Ollama may have different effective limits) |

## Next Phase Readiness

Phase 4 (GUI Reliability and UX) is the natural next step. Phase 3's accurate position metadata gives Phase 4 a clean foundation for a progress bar that maps chunks back to character offsets in the original text — duplicate-substring confusion is no longer a risk.

## Loop Status

- PLAN ✓ (2026-05-21)
- AUDIT ✓ (2026-05-21 — conditionally acceptable, 0 must-have + 4 strongly-recommended applied)
- APPLY ✓ (2026-05-21 — 195 tests, 0.76s, exit 0)
- UNIFY → next (`/paul:unify`)

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~15 min (PLAN + AUDIT + APPLY) |
| Started | 2026-05-21 |
| Completed | 2026-05-21 |
| Tasks | 3 / 3 completed PASS |
| Files modified | 2 (source) + 2 (artifacts) |
| Tests delta | +16 (179 → 195) |
| Suite wall time | 0.76s |
| Exit code | 0 |
| Qualify result | 0 GAPs, 0 DRIFTs — first-pass green |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Forward-only `find_cursor` over per-call cursor calculation | Simplest correct fix; cursor advance is centralized in `_locate` helper; impossible to forget | Duplicate substrings now resolve to distinct, source-ordered positions |
| OpenAI 4096 limit anchored as `OPENAI_TTS_MAX_INPUT_CHARS` in text_processing.py (not providers.py) | OpenAI limit is the input-side concern of the chunker, not a provider capability; providers.py stays immutable | Future per-provider char limits (Kokoro, Ollama) can follow same module-level pattern when those phases land |
| Position-accuracy fix is a bug fix, not a behavior shift | Old behavior was demonstrably wrong (positions could collide on duplicates); no documented contract specifying the bug | No `# CHARACTERIZED — Phase 3` comments; all existing tests remain valid |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------:|--------|
| Auto-fixed | 0 | First-pass green |
| Scope additions | 0 | — |
| Deferred | 3 | All from audit; logged above |

## Issues Encountered

None.

---
*Phase: 03-text-processing-improvements, Plan: 01*
*Completed: 2026-05-21*
