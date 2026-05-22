---
phase: 00-discovery-and-approval
plan: 02
subsystem: testing
tags: [pytest, characterization, regression-net, gitignore, security, monkeypatch, socket-block]

requires:
  - phase: none
    provides: existing pre-modernization source modules (settings.py, text_processing.py, tts_conversion.py, combine_and_convert.py)
provides:
  - baseline characterization test suite (101 tests, < 1s wall time)
  - strict pytest configuration (filterwarnings=error, autouse network block)
  - hardened .gitignore (key.txt + tmp/ + audio output)
  - .paul-tracked verbatim pytest log for audit evidence
  - meta-test that prevents key.txt from being re-added to git
affects: [phase-1-architecture-and-configuration, phase-3-text-processing, phase-5-audio-video-cleanup, phase-7-testing-validation-and-docs]

tech-stack:
  added: []   # No new deps. pytest, soundfile, pydub already in environment.yml.
  patterns:
    - "Characterization-tests-before-refactor"
    - "Autouse-socket-block-via-stdlib (no pytest-socket dep)"
    - "Conda env enforced for all test runs (.conda)"
    - "Audit-added test conventions (M1/M2/M3/M4 + S1..S5)"

key-files:
  created:
    - pytest.ini
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_settings.py
    - tests/test_text_processing.py
    - tests/test_tts_conversion.py
    - tests/test_combine_and_convert.py
    - tests/test_repo_hygiene.py
    - .paul/phases/00-discovery-and-approval/00-02-pytest.log
  modified:
    - .gitignore

key-decisions:
  - "Characterization-not-idealization: tests lock CURRENT behavior, even where unsafe, so Phase 1+ refactors land against a regression net"
  - "Network blocked at stdlib socket layer (no new dep) per audit S2"
  - "openai.OpenAI patched at source module (not tts_conversion.OpenAI) per audit M2 for deferred-import correctness"
  - "concatenate_audio_files tests located in test_tts_conversion.py per actual source (deviation from plan AC-5 wording)"
  - "key.txt untracked via git rm --cached (local index change only; commit/push/history-purge handed off to user per HITL policy)"

patterns-established:
  - "test_repo_hygiene.py meta-test enforces .gitignore credential protection — re-add of key.txt to git fails CI"
  - "filterwarnings = error in pytest.ini with narrow upstream-DeprecationWarning exceptions documented"
  - "Adversarial-input coverage in characterization tests (null byte, path traversal, Windows reserved names)"

duration: ~25min
started: 2026-05-21T00:00:00Z
completed: 2026-05-21T00:25:00Z
---

# Plan 00-02 — Execution Summary

**Baseline characterization test suite + pytest config + .gitignore credential protection; 101 tests passing in 0.77s; one real key.txt leak surfaced and HITL-remediated locally.**

**Plan:** `.paul/phases/00-discovery-and-approval/00-02-PLAN.md`
**Phase:** 0 — Discovery and Approval (sidecar)
**Completed:** 2026-05-21
**Status:** Loop closed (UNIFY ✓)
**Audit verdict (pre-execution):** Conditionally acceptable → upgrades applied → approved
**Apply outcome:** 101 / 101 tests pass; **1 real security finding surfaced and triaged during execution** (see §3).

---

## 1. Test counts

| Module | Tests | Status |
|---|---|---|
| `tests/test_settings.py` | 38 | Pass |
| `tests/test_text_processing.py` | 17 | Pass |
| `tests/test_tts_conversion.py` | 22 | Pass |
| `tests/test_combine_and_convert.py` | 9 | Pass |
| `tests/test_repo_hygiene.py` | 5 | Pass (after credential remediation) |
| **Total** | **101** | **All pass** |

- Wall time: **0.77s** (budget: < 5.0s) — well within audit S4 limit.
- Slowest test: `TestListAvailableModels::test_routes_to_openai_otherwise` at 0.46s (OpenAI module import + monkeypatch).
- Verbatim log: `.paul/phases/00-discovery-and-approval/00-02-pytest.log`, exit code captured as `EXIT=0`.

## 2. Behaviors locked per module

- **settings.py** — `load_openai_api_key` precedence (env > file > None), `sanitize_output_filename` happy-path + adversarial inputs (null byte, path traversal, Windows reserved names, very-long, empty, whitespace-only), `coerce_float`, `coerce_int`, `build_runtime_settings` precedence and quality-preset mapping. Constants (`QUALITY_PRESETS`, `OPENAI_VOICES`, `OPENAI_FALLBACK_MODELS`) frozen.
- **text_processing.py** — `read_text_from_file` returns `None` on missing file (CHARACTERIZED — Phase 1 may surface error), `_normalize_text` CRLF/CR/whitespace handling, `_sentence_split`, `_chunk_preview`, `split_text` paragraph/sentence/hard-split behavior + ordering preservation + position-metadata invariants.
- **tts_conversion.py** — `_filter_openai_tts_models` filter/dedupe/sort + fallback, `_validate_ollama_model_support` keyword detection, `list_ollama_models` happy path + HTTP error + malformed entries, `list_available_models` provider routing (Ollama and OpenAI branches, with OpenAI failure fallback), `convert_text_chunk_to_speech` Ollama branch (both supported-keyword and unsupported-model paths). `concatenate_audio_files` empty-list `ValueError` + ordering (moved here per actual source location — see §4).
- **combine_and_convert.py** — `combine_audio_files` ordering + empty-list returns empty segment (CHARACTERIZED — Phase 5 may change), `is_gpu_encoding_available` nvenc detection + subprocess error path, `get_media_height` integer parse + empty-stdout + exception paths.
- **test_repo_hygiene.py** (audit-added M1) — `.gitignore` contains each required pattern; `key.txt` is not tracked by git.

## 3. Real security finding surfaced during execution (HITL-resolved)

The audit-added M1 meta-test (`test_key_txt_not_tracked_by_git`) caught a credential exposure on first run:

- **Finding:** `key.txt` (16 bytes) was tracked in git, committed in `4a65c8e` ("Initial C", 2024-05-18), and the project remote is the public GitHub repo `https://github.com/BuggyButLearning/Text2AudioBook.git`. If the file ever contained a real OpenAI key, that key has been publicly exposed for ~2 years.
- **HITL escalation:** Stopped execution, surfaced the finding, asked the user to (a) confirm key status and (b) choose a remediation path. User chose the `.gitignore` (lighter-touch) path with stated intent "block github from sharing the key".
- **Action taken (reversible, local-only):** `git rm --cached key.txt`. Removes from the git index; file remains on disk; no commit; no push.
- **Result:** Test now passes — `git ls-files key.txt` returns empty.
- **REMAINING REQUIRED USER ACTIONS (NOT performed by this plan):**
  1. **Commit** the index change so future pushes don't re-add the file. (User decision — not auto-committed because this plan's boundaries did not authorize a security-themed commit on top of the existing dirty working tree.)
  2. **Push** the commit to GitHub so the latest tree no longer contains `key.txt`. (Requires explicit user approval per HITL policy on push.)
  3. **Decide on historical purge:** The blob from commit `4a65c8e` is **still served by GitHub** at the historical URL (and via `git clone` of any tag/branch pointing at history). To truly remove the secret, the history must be rewritten with `git filter-repo` or BFG and force-pushed. This is destructive (rewrites every commit hash; collaborators must re-clone). User has NOT approved this; it remains an open item.
  4. **Revoke the key on the OpenAI dashboard** if there is any chance the 16-byte content was ever a real key. Two years of public exposure mandates this regardless of certainty.

This finding is the single strongest justification for the audit pass that preceded execution.

## 4. Spec deviation flagged during execution

- **Issue:** Plan AC-5 listed `concatenate_audio_files` under `combine_and_convert.py`. Actual source location is `tts_conversion.py`. `combine_and_convert.py` has a similar but different helper named `combine_audio_files` (used by the legacy MP3→video flow).
- **Resolution:** Tests written against actual source. `concatenate_audio_files` tests live in `tests/test_tts_conversion.py`. `combine_and_convert.py` tests cover its real public surface (`combine_audio_files`, `is_gpu_encoding_available`, `get_media_height`). AC-4 and AC-5 are both satisfied by this distribution; the AC text in PLAN.md was not edited (kept for audit trail of the deviation).
- **Reported via:** DONE_WITH_CONCERNS status during Task 1.
- **Impact:** Zero functional impact. Naming clarity will be improved in Phase 5 (Audio/Video Cleanup) when that module is audited.

## 5. AC satisfaction

| AC | Description | Status |
|---|---|---|
| AC-1 | tests/ package scaffolded with conftest + fixtures | ✅ |
| AC-2 | settings.py characterization locked (incl. adversarial inputs per audit S3) | ✅ |
| AC-3 | text_processing.py baseline locked | ✅ |
| AC-4 | tts_conversion.py pure-logic locked (incl. concatenate_audio_files, per real source location) | ✅ |
| AC-5 | combine_and_convert.py helpers locked (real public surface, not the originally-named function) | ✅ |
| AC-6 | Full suite passes; verbatim log saved; time budget met | ✅ |
| AC-7 | .gitignore protects credentials (M1) | ✅ (after HITL remediation) |
| AC-8 | Strict pytest configuration (S1) | ✅ |
| AC-9 | Network calls blocked at socket layer (S2) | ✅ |

All 9 ACs satisfied.

## 6. Files modified / created

**New files:**
- `pytest.ini`
- `tests/__init__.py`
- `tests/conftest.py` (incl. network-block fixture)
- `tests/test_settings.py`
- `tests/test_text_processing.py`
- `tests/test_tts_conversion.py`
- `tests/test_combine_and_convert.py`
- `tests/test_repo_hygiene.py`
- `.paul/phases/00-discovery-and-approval/00-02-pytest.log`
- `.paul/phases/00-discovery-and-approval/00-02-SUMMARY.md` (this file)

**Modified files:**
- `.gitignore` (appended `key.txt`, `tmp/`, `*.mp3`, `*.wav`, `.paul/phases/**/00-02-pytest.log` — original entries preserved)

**Git index changes (uncommitted):**
- `key.txt` removed from index via `git rm --cached` (HITL §3 step). File preserved on disk.

**No source files modified:** `settings.py`, `text_processing.py`, `tts_conversion.py`, `combine_and_convert.py`, `main.py` are untouched, per plan boundaries.

## 7. Re-run command

To re-run the suite at any later time:

```powershell
conda activate text2audiobook
python -m pytest tests -q --durations=10
```

Phase 1, Phase 3, Phase 5, and Phase 7 should re-run this suite before declaring their own exit criteria. Any test that goes red after a refactor either (a) is a real regression (fix the source) or (b) is an intentional behavior change (update the characterization with a comment explaining why).

## 8. Open items handed off

| Item | Owner | Routing |
|---|---|---|
| key.txt: commit + push the index removal | User | Manual git ops (not done by this plan) |
| key.txt: historical purge from GitHub (filter-repo + force-push) | User | Destructive — explicit approval needed |
| key.txt: OpenAI key revocation if ever real | User | Out-of-band on OpenAI dashboard |
| `sys.path.insert` in conftest.py (audit D3) | Phase 1 | Refactor to packaged install during Phase 1 module reshape |
| Coverage measurement (audit D1) | Phase 7 | Add `pytest-cov` per PRD §13 |
| CI workflow integration (audit D2) | Phase 7 | `.github/workflows/tests.yml` |
| Naming clarity: `concatenate_audio_files` vs `combine_audio_files` | Phase 5 | Audio/video module audit |

## 9. Plan 00-01 unaffected

The PRD approval plan (00-01) is unchanged. Its checkpoint is still awaiting stakeholder sign-off. This sidecar produced no PRD edits.

## 10. Skill audit

Per `.paul/SPECIAL-FLOWS.md`, no skills were marked **required** for this plan; `/verify` was registered as optional. Skill audit: no gaps to log.

## 11. Next phase readiness

**Ready for next plan:**
- Regression net is live and green. Phases 1, 3, 5, 7 can refactor confidently and detect drift.
- `pytest.ini` provides a strict baseline (filterwarnings=error). Future tests can assume this.
- `.gitignore` and `test_repo_hygiene.py` ensure no plan can silently re-introduce the credential leak.

**Concerns / technical debt:**
- `sys.path.insert` hack in `tests/conftest.py` must be removed in Phase 1 (audit D3).
- 16-byte `key.txt` still in git history on the public GitHub remote until user runs history rewrite + force-push.
- Adversarial-input tests CHARACTERIZE current (sometimes unsafe) behavior of `sanitize_output_filename`. Phase 1 must consciously decide whether to harden or document.

**Blockers for proceeding:**
- None for new plans. 00-01 (PRD approval) remains open on its own track.

---
*Generated by /paul:apply 2026-05-21; finalized by /paul:unify same day.*
