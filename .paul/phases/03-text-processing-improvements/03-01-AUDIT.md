# Enterprise Plan Audit Report

**Plan:** `.paul/phases/03-text-processing-improvements/03-01-PLAN.md`
**Audited:** 2026-05-21
**Auditor role:** Senior principal engineer + compliance reviewer
**Verdict:** Conditionally acceptable — approved after 0 must-have + 4 strongly-recommended upgrades applied.

---

## 1. Executive Verdict

Phase 3 is the smallest plan in the milestone so far: a forward-cursor bug fix + module-level constants + targeted test extensions. No new modules, no new dependencies, no scope creep. The position-accuracy fix is correct and the reconstruction-invariant test is the right contract lock.

Pre-audit gaps are doc / observability hygiene, not safety issues. After applying the must-have-equivalent rigor (test-count claim, observability for the fallback path, all-equal-positions trap, reconstruction-tolerance strengthening), the plan is approved for APPLY.

Pre-upgrade: would sign with caveats — the bug fix is correct but the test surface has weak negative-space coverage (a regressed implementation that returned `positions = [0, 0, 0]` would still pass the monotonic-non-decreasing test).
Post-upgrade: yes.

---

## 2. What Is Solid (Do Not Change)

- **Forward-cursor pattern.** `find_cursor` advancing only on successful find, with `_locate` helper centralizing the search-and-advance, is the cleanest possible fix for the duplicate-substring bug. No backtracking, no per-call state to manage in the caller.
- **Hard-split arithmetic position.** Pieces of a hard-split sentence compute position as `sentence_start + hard_start` — exact, no `find()` needed. Eliminates one whole class of duplicate-substring confusion inside hard-split loops.
- **Module-level constants over magic numbers.** Naming `OPENAI_TTS_MAX_INPUT_CHARS = 4096` and `DEFAULT_CHUNK_MAX = 3500` makes the safety margin auditable. A future contributor can't quietly raise the default past the API ceiling without the safe-margin test catching it.
- **Test-additive discipline.** Phase 3 does not modify any existing test — the position-accuracy fix is correctly classified as a bug fix, not a behavior shift. No `# CHARACTERIZED — Phase 3` comments needed. Clean.
- **Scope discipline.** No providers.py / settings.py / model_discovery.py / main.py / tts_conversion.py changes. Phase 3 is purely intra-module within text_processing.py.
- **Reconstruction invariant locked at the contract layer (AC-3).** Reconstruction tests catch a whole class of subtle position bugs that wouldn't otherwise surface until Phase 4 GUI progress-bar work — exactly the right time to lock it.

---

## 3. Enterprise Gaps Identified

### G1 — Test-count claim is wrong
Pre-audit AC-5 says "≥ 190 tests collected (179 baseline + ≥ 11 new)". The current `tests/test_text_processing.py` actually has **20** tests, not the implied 12. Counting: TestReadTextFromFile=2, TestNormalizeText=5, TestSentenceSplit=3, TestChunkPreview=3, TestSplitText=7. Total = 20. Plan-added tests target ≥ 11 (Budget=4 + Positions=5 + EdgeCases=6 = 15). Realistic post-plan total: ≥ 194 (179 + 15), or ≥ 190 if some of the planned new tests are merged. Doc inconsistency only — not a defect — but a sloppy plan that under-counts its baseline invites future confusion.

Severity: **strongly recommended** (doc hygiene).

### G2 — `_locate` fallback path is silent
When `text.find(substring, find_cursor)` returns -1, `_locate` returns the fallback position and does NOT advance `find_cursor`. This is defensive (the substring SHOULD always be present because paragraphs/sentences are extracted from the normalized text via `re.split`) but it's also a silent failure path. If a future change to `_normalize_text` ever causes `find` to miss, the positions would degrade silently — same class of defect Phase 3 is fixing.

The fix: when `_locate` takes the fallback path, log at DEBUG level with the substring's first ~30 chars (truncated, no full content) so a maintainer running the suite under `--log-cli-level=DEBUG` sees the invariant violation. Costs nothing in production (DEBUG is off), buys defensive observability for the very thing Phase 3 is trying to lock.

Severity: **strongly recommended** (defensive observability against future regressions).

### G3 — All-equal-positions trap not caught by tests
Pre-audit `TestSplitTextPositions::test_positions_are_monotonic_non_decreasing` asserts `positions == sorted(positions)`. With positions `[0, 0, 0]` this PASSES — a regressed implementation that always returns 0 for every position passes the monotonic test. The companion `test_duplicate_paragraphs_get_distinct_positions` catches duplicates, but only for the specific "He said." fixture. A truly broken implementation returning `[0, 0, 0]` for `["Alpha sentence.", "Beta sentence.", "Gamma sentence."]` would NOT be caught.

Need: when there are ≥ 2 chunks AND they have distinct content, at least 2 of the positions MUST be distinct.

Severity: **strongly recommended** (test-fidelity; closes a regression path).

### G4 — Reconstruction tolerance is fuzzy at the lower bound
Pre-audit `_reconstruct_check` does `source_slice.startswith(prefix[:20])` where `source_slice = text[pos:pos + len(prefix) + 10].lstrip()`. If `pos` is past the actual location, the slice could still START WITH a valid 20-char prefix of some OTHER chunk — false positive. Should add: `source_slice` must have at least N characters (sanity check that pos isn't past EOF), AND the chunk text length must be reasonable (no empty chunks).

Severity: **strongly recommended** (test-fidelity; reduces false positives).

### G5 — Performance characteristics not flagged
`text.find` is O(n). Called once per paragraph + once per sentence inside long paragraphs. For a 10MB book with many paragraphs/sentences, the cumulative `find` cost is O(n²) in worst case. Realistic audiobook inputs are <500KB; this is not a v0.1 issue. But absence of a note means a future maintainer wouldn't know the constraint exists.

Severity: **can safely defer** (premature optimization for v0.1; document in SUMMARY as a known characteristic).

### G6 — Memory characteristic for very large inputs
`split_text` builds full lists in memory. For a 10MB book → ~3000 chunks × ~3500 chars = ~10MB chunk storage (plus positions + sentences lists). Realistic v0.1 inputs are well under this. Generator-based chunking would let you stream — but it's a real architectural change (positions list becomes hard to pre-build), out of Phase 3 scope.

Severity: **can safely defer** (Phase 7 / future memory work).

### G7 — Per-provider char limits not generalized
`OPENAI_TTS_MAX_INPUT_CHARS = 4096` is OpenAI-specific. Kokoro and Ollama may have different effective limits. Plan correctly defers this to Phase 6.2 / 7, but doesn't note the deferral explicitly in the boundaries section.

Severity: **can safely defer** (scope-limits section already excludes it; explicit defer-note is documentation polish, not a defect).

---

## 4. Upgrades Applied to Plan

All strongly-recommended findings applied inline. Audit-added content tagged with `audit-added S1`, etc.

### Must-Have (Release-Blocking)

None.

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| S1 | G1 — Test-count claim wrong | AC-5, verification checklist | Updated "20 existing + ≥ 11 new = ≥ 31 in test_text_processing.py" and adjusted regression floor to "≥ 194 (179 baseline + ≥ 15 new)". |
| S2 | G2 — Silent fallback in `_locate` | Task 1 source guidance | `_locate` now emits `logging.debug("text_processing._locate: substring not found at-or-after cursor=%d; using fallback. substring_preview=%r", find_cursor, substring[:30])` when find returns -1. No production effect; visible only with `--log-cli-level=DEBUG`. |
| S3 | G3 — All-equal-positions trap | AC-3, Task 2 (new test) | New test `TestSplitTextPositions::test_distinct_chunks_have_distinct_positions`: when ≥ 2 chunks with distinct content exist, at least 2 of the positions MUST differ. Closes the [0,0,0] regression path. |
| S4 | G4 — Reconstruction tolerance fuzzy | Task 2 `_reconstruct_check` strengthening | The helper now asserts (a) `len(source_slice) >= min(len(prefix), 10)` so a past-EOF position fails fast, and (b) `len(chunks[i]) > 0` for every chunk inspected (no empty chunks in the list). |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|----------------------|
| D1 | G5 — O(n²) performance for very large inputs | Real audiobook inputs are < 500KB. Not a v0.1 issue. Document in SUMMARY as a known characteristic; Phase 7 or future optimization plan can revisit. |
| D2 | G6 — Memory: full-list construction | Same as D1; v0.1 inputs fit easily. Generator-based chunking is a real architectural change with public-API implications; out of Phase 3 scope. |
| D3 | G7 — Per-provider char limits | Phase 6 / 6.2 territory (Kokoro / Ollama). The `OPENAI_TTS_MAX_INPUT_CHARS` constant is the OpenAI-specific anchor; future per-provider extension can follow the same module-level-constant pattern. |

---

## 5. Audit & Compliance Readiness

### Defensible audit evidence
- **Before:** A regressed `split_text` returning `positions = [0, 0, 0]` would pass the monotonic-non-decreasing assertion silently.
- **After (S3):** Explicit distinctness test catches that regression.

### Silent failure prevention
- **Before:** `_locate` taking the fallback path produced no observable signal.
- **After (S2):** DEBUG-level log fires; visible during dev / CI with appropriate log level. No production noise.

### Post-incident reconstruction
- **Before:** Reconstruction test could false-positive when `pos` was past the actual location (slice starts with garbage that happens to share a prefix).
- **After (S4):** Length-floor check on the source slice + non-empty-chunk assertion close the false-positive path.

### Boundary integrity
- Unchanged. `providers.py` / `settings.py` / `model_discovery.py` / `tts_conversion.py` / `main.py` untouched. No new third-party deps.

### Test fidelity
- **Before:** Test-count claim off-by-8 (20 existing, not 12). Minor but a sign of careless math.
- **After (S1):** Corrected; regression floor reflects realistic count.

---

## 6. Final Release Bar

### What must be true before this plan ships
- 4 strongly-recommended upgrades applied → **Done in this audit pass.**
- APPLY produces:
  - `text_processing.py` with `_locate` DEBUG-log on fallback (S2)
  - `tests/test_text_processing.py` with `test_distinct_chunks_have_distinct_positions` (S3)
  - `_reconstruct_check` strengthened with length-floor + non-empty assertions (S4)
- Regression suite at ≥ 194 tests (post-S1 floor), exit 0, < 5.0s
- `providers.py` unchanged; no new third-party deps; `main.py` unchanged

### Risks remaining if shipped as-is (post-audit)
- D1: O(n²) for >5MB inputs — bounded by realistic v0.1 audiobook size
- D2: Full-list memory build — same bound
- D3: Per-provider char limits hardcoded for OpenAI only — Phase 6+ extends

None blocking for an integration polish plan.

### Would I sign?
**Yes — post-upgrade.** Pre-upgrade: yes, with the caveat that the test-fidelity gap (S3) is the kind of latent defect that lets a future regression slip past the suite. Catching it at audit costs five minutes; catching it via a production-fed bug report is days.

---

**Summary:** Applied **0 must-have + 4 strongly-recommended** upgrades to PLAN.md. Deferred **3 can-safely-defer** items.
**Plan status:** Updated and ready for APPLY.

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
*Auditor stance: senior principal engineer + compliance reviewer, last review before production.*
