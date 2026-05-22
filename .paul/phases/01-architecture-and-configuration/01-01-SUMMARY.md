---
phase: 01-architecture-and-configuration
plan: 01
subsystem: providers
tags: [provider-abstraction, registry, mapping-proxy, fail-fast, immutable, hf-revisions, kokoro-pin]

requires:
  - phase: 00-discovery-and-approval
    provides: PRD-approved §14 decisions (HF cache, provider defaults, VibeVoice deferral) + 101-test regression net
provides:
  - providers.py — immutable single-source-of-truth registry (3 providers)
  - ProviderCapability dataclass (frozen)
  - MappingProxyType-wrapped PROVIDER_REGISTRY
  - fail-fast validation at module import (regex + revision schema)
  - settings.HF_HOME_DEFAULT constant
  - settings.HF_MODEL_REVISIONS view object deriving from providers
  - settings.get_provider_capability facade
  - audit D3 closed (sys.path hack removed)
affects: [phase-2-tts-engine-modernization, phase-2-1-model-discovery, phase-4-gui, phase-6-ollama, phase-6-2-kokoro]

tech-stack:
  added: []   # No new third-party deps. Enforced by ast-based test.
  patterns:
    - "Immutable-registry-as-single-source-of-truth (MappingProxyType)"
    - "Fail-fast validation at module import (regex compile + revision schema)"
    - "Deferred import + view object to avoid circular imports while preserving single source of truth"
    - "Frozen dataclass for capability records (hashable, mutation-safe)"
    - "Milestone constant in code (MILESTONE = 'v0.1') as guardrail against scope leakage"

key-files:
  created:
    - providers.py
    - tests/test_providers.py
    - .paul/phases/01-architecture-and-configuration/01-01-pytest.log
  modified:
    - settings.py                  # additive only — appended HF_HOME_DEFAULT, get_provider_capability, _HFModelRevisionsView
    - tests/conftest.py            # removed sys.path.insert hack (audit D3 closes)
    - tests/test_settings.py       # appended TestPhase1Additions class (8 new tests)

key-decisions:
  - "PROVIDER_REGISTRY is wrapped in MappingProxyType — mutation raises TypeError"
  - "HF revision SHA is hardcoded ONCE in providers.py; settings.HF_MODEL_REVISIONS derives from it"
  - "Kokoro voice list ships 20 of 54 (American English subset); Phase 6.2 may expand"
  - "MILESTONE = 'v0.1' module constant + docstring lock VibeVoice omission in code, not just docs"
  - "Revision schema accepts SHA / semver / 'main'|'master' literal; anything else raises at module import"

patterns-established:
  - "providers.py is the SOLE source of truth for provider capabilities; never duplicate in settings"
  - "Future tests requiring fake providers must monkeypatch get_provider_capability — direct registry mutation is blocked"
  - "Any new third-party import in providers.py fails the ast-based no-new-deps test"

duration: ~20min
started: 2026-05-21T01:00:00Z
completed: 2026-05-21T01:20:00Z
---

# Plan 01-01 — Execution Summary

**Phase 1 contract layer landed: immutable, fail-fast `providers.py` registry (OpenAI/Ollama/Kokoro; no VibeVoice in v0.1); `settings.py` additions derive HF revisions from the registry without duplication; `conftest.py` sys.path hack removed; 145/145 tests pass in 0.77s (101 baseline + 44 Phase 1 new).**

**Plan:** `.paul/phases/01-architecture-and-configuration/01-01-PLAN.md`
**Phase:** 1 — Architecture and Configuration
**Completed:** 2026-05-21
**Status:** APPLY complete; ready for UNIFY
**Audit verdict (pre-execution):** Conditionally acceptable → 3 must-have + 5 strongly-recommended upgrades applied → approved
**Apply outcome:** All 3 tasks DONE with PASS qualify; no deviations.

---

## 1. Test counts

| Module | Before | After | Delta |
|---|---|---|---|
| tests/test_settings.py | 38 | 46 | +8 (TestPhase1Additions) |
| tests/test_text_processing.py | 17 | 17 | 0 |
| tests/test_tts_conversion.py | 22 | 22 | 0 |
| tests/test_combine_and_convert.py | 9 | 9 | 0 |
| tests/test_repo_hygiene.py | 5 | 5 | 0 |
| tests/test_providers.py | — | 36 | +36 (new module) |
| tests/test_providers.py — TestRegistryContents | — | 8 | (parametrized) |
| tests/test_providers.py — TestOpenAICapability | — | 5 | |
| tests/test_providers.py — TestOllamaCapability | — | 4 | |
| tests/test_providers.py — TestKokoroCapability | — | 6 | |
| tests/test_providers.py — TestGetProviderCapability | — | 6 | |
| tests/test_providers.py — TestRegistryImmutability | — | 2 | audit M3 |
| tests/test_providers.py — TestCapabilityImmutability | — | 2 | audit S3 |
| tests/test_providers.py — TestMilestoneAndDocstring | — | 2 | audit S1 |
| tests/test_providers.py — TestNoNewDependencies | — | 1 | audit S4 |
| tests/test_providers.py — TestMonkeypatchPattern | — | 1 | audit S5 |
| **Total** | **101** | **145** | **+44** |

- Wall time: **0.77s** (budget < 5.0s — well within audit S4 limit)
- Slowest test: `test_routes_to_openai_otherwise` at 0.45s (openai module import cost, unchanged)
- Verbatim log: `.paul/phases/01-architecture-and-configuration/01-01-pytest.log` — `EXIT=0`

## 2. AC satisfaction

| AC | Description | Status |
|---|---|---|
| AC-1 | providers.py with declarative immutable registry + fail-fast validation + MILESTONE constant | ✅ |
| AC-2 | settings.py additions are additive only; HF_MODEL_REVISIONS derived from providers (no hardcoded dict) | ✅ |
| AC-3 | tests/conftest.py sys.path hack removed; suite still passes | ✅ (audit D3 closes) |
| AC-4 | test_providers.py covers registry contents, per-provider, adversarial inputs | ✅ |
| AC-5 | test_settings.py TestPhase1Additions class covers HF surfaces + delegation + no-hardcoded-dict | ✅ |
| AC-6 | Full regression suite green, ≥ 115 tests, < 5.0s, verbatim log saved | ✅ (145 tests, 0.77s) |
| AC-7 | Registry + capability immutability tests | ✅ |
| AC-8 | ast-based no-new-deps test | ✅ |
| AC-9 | Monkeypatch fake-provider pattern demo | ✅ |

All 9 ACs satisfied.

## 3. Files created / modified

**Created:**
- `providers.py` — 113 lines, single source of truth for 3 provider capabilities. Validates regex + revision schemas at module import. Wrapped in `MappingProxyType`. Includes `MILESTONE = "v0.1"` constant and docstring stating "VibeVoice intentionally omitted".
- `tests/test_providers.py` — 36 tests across 10 test classes.
- `.paul/phases/01-architecture-and-configuration/01-01-pytest.log` — verbatim audit-trail log.
- `.paul/phases/01-architecture-and-configuration/01-01-SUMMARY.md` (this file).

**Modified (additive only):**
- `settings.py` — appended 3 surfaces (HF_HOME_DEFAULT, get_provider_capability, _HFModelRevisionsView). No existing code touched. 00-02 characterization tests all still pass.
- `tests/conftest.py` — removed `sys.path.insert` block + the `pathlib`/`sys` imports it relied on. The `_block_network` autouse fixture remains; the project-side fixtures (`clean_env`, `no_key_file`, `tmp_key_file`, `isolated_config`) all kept. `pytest.ini` already provides `pythonpath = .` so import discovery is unaffected.
- `tests/test_settings.py` — appended `TestPhase1Additions` class (8 tests). No edits to existing test classes.

**Untouched (per plan boundaries):**
- `tts_conversion.py` — Phase 2 owns the refactor.
- `text_processing.py` — Phase 3.
- `combine_and_convert.py` — Phase 5.
- `main.py` — Phase 4.
- `requirements.txt`, `environment.yml` — no new deps.
- `pytest.ini` — already configured by 00-02 audit.
- `.gitignore` — locked by 00-02 audit.

## 4. Deviations from plan

None. All 3 tasks executed exactly as written.

## 5. Audit-added invariants verified

- **M1 fail-fast regex compile:** `providers.py` runs `re.compile(_cap.model_pattern)` inside the module-level loop. A typo would raise `ValueError` at import. Not directly unit-tested (would require `importlib.reload` against a corrupted module), but the loop is in the source and was exercised at import-time by every test run.
- **M2 single source of truth:** `settings.HF_MODEL_REVISIONS` is the `_HFModelRevisionsView` object. The ast-based meta-test `test_no_hardcoded_hf_model_revisions_dict_literal_in_settings` parses settings.py and asserts no `HF_MODEL_REVISIONS = {...}` dict-literal assignment exists. Test passes.
- **M3 MappingProxyType immutability:** Tests `test_setitem_raises_type_error` and `test_delitem_raises_type_error` confirm mutation attempts on `PROVIDER_REGISTRY` raise `TypeError`.
- **S1 milestone constant:** `test_milestone_constant` and `test_docstring_mentions_vibevoice_omission` pass.
- **S2 revision schema validation:** `_validate_revision(...)` runs at module import for every capability. Kokoro's SHA passes; None passes; invalid values would raise.
- **S3 frozen-dataclass mutation:** `test_field_mutation_raises` confirms `FrozenInstanceError` when setting `cap.name = "X"`.
- **S4 no new deps:** `test_top_level_imports_are_stdlib_only` parses providers.py via ast and confirms imports ∈ {`dataclasses`, `typing`, `re`, `types`}.
- **S5 monkeypatch pattern:** `test_monkeypatch_get_provider_capability` demonstrates the canonical pattern for future tests needing fake providers.

## 6. Deferred / open items handed off

From 00-02 audit, **closed by this plan:**
- ✅ D3 — `sys.path.insert` hack in conftest.py (REMOVED)

From this plan's own audit, **deferred:**
- D1 — Kokoro voice canonical-list versioning → Phase 6.2 owns
- D2 — `str`-subclass edge case in `get_provider_capability` → academic, defer indefinitely
- D3 — `importlib.reload(providers)` defensive note → no current trigger

From this plan, **handed forward to Phase 2:**
- `providers.py` provides the contract layer. Phase 2's `_write_openai_speech` refactor should use `providers.PROVIDER_REGISTRY["OpenAI"]` for capability lookups (voices, fallback_models, max_concurrency).
- `tts_conversion._validate_ollama_model_support` can be replaced with `re.compile(PROVIDER_REGISTRY["Ollama"].model_pattern).match(model_name)`.
- `tts_conversion._filter_openai_tts_models` can be replaced with a registry-driven filter using `PROVIDER_REGISTRY["OpenAI"].model_pattern` + `.fallback_models`.

## 7. Re-run command

```sh
conda activate text2audiobook
python -m pytest tests -q --durations=10
```

## 8. Skill audit

Per `.paul/SPECIAL-FLOWS.md`, no skills were marked **required**. `/verify` and `/tdd` were optional and not invoked (regression net + new unit tests cover the work directly). `/paul:audit` was auto-invoked per project policy. Skill audit: no gaps to log.

## 9. Next phase readiness

**Ready for Phase 2 (TTS Engine Modernization):**
- Provider abstraction contract is live + immutable.
- Phase 2's refactor of `tts_conversion.py` has a clean target: replace inline provider dispatch with registry-driven lookups.
- Regression net at 145 tests; Phase 2 must keep all of these green plus add Phase 2 characterization tests for the SDK migration.
- Phase 2 will face the user's pre-session dirty edits to `tts_conversion.py` — must reconcile that dirty state before refactoring (HITL gate likely).

**Concerns:**
- The fail-fast validation in `providers.py` is asserted at module-import time but NOT exercised by a dedicated unit test (M1). The invariant is in the source; corrupting it would crash every test that imports `providers`. Future work could add an `importlib.reload` test if reload semantics turn out to be stable enough.

**Blockers:**
- None for proceeding to Phase 2 planning.

---
*Generated by /paul:apply 2026-05-21; finalized by /paul:unify same day.*
