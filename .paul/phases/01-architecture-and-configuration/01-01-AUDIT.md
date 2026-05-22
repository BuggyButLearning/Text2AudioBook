# Enterprise Plan Audit Report

**Plan:** `.paul/phases/01-architecture-and-configuration/01-01-PLAN.md`
**Audited:** 2026-05-21
**Auditor role:** Senior principal engineer + compliance reviewer
**Verdict:** Conditionally acceptable — approved after must-have + strongly-recommended upgrades applied (see §4).

---

## 1. Executive Verdict

This is the project's first "real code" plan — Phase 0 was paperwork, 00-02 was test scaffolding. The plan correctly bounds scope (no `tts_conversion.py` edits, no synthesis logic, no new deps) and respects the regression net. But the pre-audit plan had three classes of enterprise-grade defect:

1. **Duplication of the source of truth.** The HF revision SHA was written into BOTH `providers.py` AND `settings.py`. Two months from now, when someone updates one and not the other, the build silently uses the stale value. Single-source-of-truth is the whole point of a registry.
2. **Mutable registry.** `PROVIDER_REGISTRY: dict[...]` invites runtime mutation. A "single source of truth" registry that can be silently replaced at runtime isn't a source of truth — it's a suggestion.
3. **No fail-fast validation.** A typo'd regex or malformed revision SHA would ship and explode at first use, not at import. Enterprise systems fail at startup, not at midnight.

After applying the must-have + strongly-recommended upgrades inline, the plan is **approved for APPLY**.

Pre-upgrade: I would not sign my name to it. The duplication finding alone is the kind of latent rot that creates 2am pages.
Post-upgrade: yes.

---

## 2. What Is Solid (Do Not Change)

- **Scope discipline.** Plan explicitly defers `tts_conversion.py` to Phase 2 and refuses to refactor it inside Phase 1. This is the right call — the user has uncommitted edits there; silently overwriting them would be a boundary violation.
- **Additive-only edits to settings.py.** Existing 00-02 characterization tests stay green. The append-only constraint is enforced both in plan text and (post-audit) by a meta-test.
- **Three-provider scope for v0.1.** Matches Phase 0 decision §14.2(1). No VibeVoice slipping in. Plan explicitly asserts `"VibeVoice" not in PROVIDER_REGISTRY` as a regression test — catches accidental v0.2 leakage during refactors.
- **`frozen=True` on `ProviderCapability`.** Hashable, safe to use as dict keys / set members, prevents field mutation. Right primitive.
- **Provider kinds enumerated as `Literal["hosted", "local-api", "local-hf"]`.** Forces every new provider to pick a category; prevents the "what is this thing" drift.
- **Audit D3 (sys.path hack) folded in.** Closing carry-over technical debt while you're already in the conftest file is the right move — cheaper than queuing it for later.
- **Regression net required to be re-green.** No phase advances on broken tests. Discipline.
- **Voice list intentionally a subset.** 20 voices instead of 54 keeps the v0.1 surface small. Phase 6.2 will expand consciously.

---

## 3. Enterprise Gaps Identified

### G1 — HF revision SHA duplicated across `providers.py` and `settings.py`
Pre-audit Task 2 has `HF_MODEL_REVISIONS = {"hexgrad/Kokoro-82M": "496dba1..."}` hardcoded in `settings.py`. The SAME SHA also lives in `providers.py` (registry entry for Kokoro). Two places, one truth. First time someone updates one without updating the other, the pipeline misbehaves silently.

Severity: **must-have**.

### G2 — `PROVIDER_REGISTRY` is mutable
Plain `dict` allows runtime mutation. A misbehaving test (or a future contributor) can do `providers.PROVIDER_REGISTRY["FakeProvider"] = ...` and the change propagates everywhere `providers.PROVIDER_REGISTRY` is read. For a registry billed as "single source of truth", this is incoherent.

Severity: **must-have**.

### G3 — No fail-fast validation at module import
Pre-audit `providers.py` had `model_pattern` strings that were never compiled at import time. A typo in any regex would compile when first used (in synthesis code, which doesn't exist yet) and explode there. Same for `hf_model_revision`: any string passes — could be `"abc"`, could be `"latest"`, could be empty.

Severity: **must-have** (regex compile), **strongly recommended** (revision schema).

### G4 — `is_available_in_v01` is a soft signal
Just a bool. Nothing enforces "all entries in PROVIDER_REGISTRY are available in v0.1 because VibeVoice isn't here yet". A future PR could add a VibeVoice entry with `is_available_in_v01=False` and pretend that means "it's hidden" — but `list_providers()` would still return it and the UI dropdown would still show it.

Severity: **strongly recommended** (don't remove the field; add a MILESTONE constant + docstring + test that catches the leakage).

### G5 — Frozen dataclass mutation not unit-tested
Pre-audit tests assert registry contents but never verify that `capability.name = "X"` actually raises. If a future contributor changes `frozen=True` to `frozen=False` to add a setter, no test catches it.

Severity: **strongly recommended**.

### G6 — No no-new-deps test
Pre-audit plan asserts "stdlib + already-installed packages only" in AC-1 but doesn't enforce it. Six months from now, someone adds `import structlog` to `providers.py` and the test suite happily passes.

Severity: **strongly recommended**.

### G7 — Registry mutation defense is missing the test-only fake-provider pattern
If the registry is immutable (M3), tests that want a fake provider can't just inject one. The plan needs to document and demonstrate the canonical alternative (monkeypatch `get_provider_capability`).

Severity: **strongly recommended**.

### G8 — Kokoro voice list versioning
Hardcoded American-English subset (20 voices) is the right v0.1 call, but there's no signal in code about where the canonical 54-voice list lives or how to upgrade.

Severity: **can safely defer** — Phase 6.2 owns the expansion; a comment in `providers.py` is enough for now.

### G9 — `get_provider_capability` accepts non-str types via isinstance check
Returns None for non-strings. Defensible. But a `str`-subclass that *should* be valid (e.g. an enum's `.value` that's been wrapped) would also return None. Edge case.

Severity: **can safely defer** — unlikely to bite in practice; UI dropdown values are always plain `str`.

### G10 — Tests assume `providers.py` is imported fresh per test
With `MappingProxyType` (M3), the registry is module-singleton-scoped. If any test does `importlib.reload(providers)` it gets a NEW MappingProxyType wrapping a fresh dict. Not a correctness problem, but tests should not reload providers unless they know what they're doing.

Severity: **can safely defer** — no current test does this; defensive note in conftest if it ever happens.

---

## 4. Upgrades Applied to Plan

All must-have and strongly-recommended findings have been applied **directly to `01-01-PLAN.md`**. Audit-added content references `audit M1`, `audit S2`, etc. inline for traceability.

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| M1 | G3 — no fail-fast regex compilation | AC-1 (strengthened), Task 1 action block | `providers.py` now compiles every `model_pattern` via `re.compile(...)` at module-import. Invalid regex raises `ValueError` before any caller can hit it. |
| M2 | G1 — HF revision SHA duplicated | AC-2 (strengthened), Task 1 (added `hf_model_repo` field), Task 2 (replaced hardcoded dict with `_HFModelRevisionsView`), Task 3 step 3 (ast meta-test) | `providers.py` is the sole source of truth. `settings.HF_MODEL_REVISIONS` is now a dict-like view object that derives from `PROVIDER_REGISTRY` on every access. A meta-test asserts no hardcoded `HF_MODEL_REVISIONS = {...}` literal exists in `settings.py` source. |
| M3 | G2 — `PROVIDER_REGISTRY` mutable | AC-1 (strengthened), Task 1 action, AC-7 (new) | Registry wrapped in `MappingProxyType`. Mutation attempts raise `TypeError`. AC-7 tests this explicitly. |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| S1 | G4 — milestone constraint only in docs | AC-1, AC-7, Task 1 action | Added `MILESTONE = "v0.1"` module constant + docstring stating "VibeVoice intentionally omitted". Tests assert both. Catches accidental v0.2 leakage at unit-test time. |
| S2 | G3 (partial) — no revision-schema validation | AC-1 (strengthened), Task 1 action (`_validate_revision`) | `providers.py` validates every non-None `hf_model_revision` against three schemas (SHA / semver / `main`/`master`). Invalid schemas raise `ValueError` at module import. |
| S3 | G5 — frozen mutation not tested | AC-7 (new), Task 3 step 2 | New test asserts `dataclasses.FrozenInstanceError` when attempting field mutation. Catches `frozen=False` regressions. |
| S4 | G6 — no no-new-deps enforcement | AC-8 (new), Task 3 step 2 | New test parses `providers.py` via `ast` and asserts every top-level import is in an allowlist. Any new third-party import fails loudly. |
| S5 | G7 — no fake-provider pattern documented | AC-9 (new), Task 3 step 2 | At least one test demonstrates the canonical `monkeypatch.setattr(providers, "get_provider_capability", ...)` pattern. Documents how to inject fake providers without touching the immutable registry. |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|----------------------|
| D1 | G8 — Kokoro voice canonical-list documentation | Phase 6.2 owns Kokoro expansion. A `# 20 of 54 voices; Phase 6.2 expands` comment in `providers.py` is acceptable; codified versioning of the 54-voice list is overengineering for v0.1. |
| D2 | G9 — `str`-subclass edge case in `get_provider_capability` | UI dropdown source-of-truth is plain `str`. The defensive `isinstance(name, str)` check is sufficient. Revisit only if a real downstream caller passes a wrapped type. |
| D3 | G10 — defensive note about `importlib.reload(providers)` | No current test does this. If a future test reloads the module, the immutability invariants still hold per-reload. Add a conftest note then; no current risk. |

---

## 5. Audit & Compliance Readiness

### Defensible audit evidence
- **Before:** Plan output was tests-pass and a SUMMARY.md. No proof that the architectural invariants (single source of truth, immutability, fail-fast) held.
- **After (M1/M2/M3 + S2/S3/S4):** Each architectural invariant has a corresponding test. AC-7 (immutability), AC-8 (no new deps), AC-9 (monkeypatch pattern), plus the M2 ast-based meta-test against duplication. An auditor can verify the design promises programmatically.

### Silent failure prevention
- **Before:** Typo'd regex compiles to no-match; ships silently; explodes at first synthesis call (Phase 2).
- **After (M1):** `re.compile(...)` runs at module import. A typo crashes the test suite immediately.
- **Before:** Stale HF SHA could exist in `settings.py` after a `providers.py` update.
- **After (M2):** Impossible by construction. `settings.HF_MODEL_REVISIONS` derives on every access.

### Post-incident reconstruction
- **Before:** "Why did the Kokoro download use the wrong revision?" — auditor has to compare two files.
- **After:** Single source. The git history of `providers.py::PROVIDER_REGISTRY["Kokoro"].hf_model_revision` is THE answer.

### Ownership / accountability
- Unchanged. Solo project. Implicit.

### Boundaries
- **Before:** Boundaries listed protected files. Good.
- **After:** Unchanged but verification checklist now includes a meta-check for the M2 invariant (no hardcoded HF_MODEL_REVISIONS in settings.py).

---

## 6. Final Release Bar

### What must be true before this plan ships
- Must-have upgrades applied to PLAN.md → **Done.**
- Strongly-recommended upgrades applied to PLAN.md → **Done.**
- APPLY produces:
  - `providers.py` with `MappingProxyType` registry + fail-fast validation + `MILESTONE = "v0.1"` constant
  - `settings.py` with deferred-import view (no hardcoded HF dict)
  - `tests/test_providers.py` with ≥ 20 tests covering registry, adversarial inputs, immutability, fail-fast, no-new-deps, monkeypatch pattern
  - `tests/test_settings.py` augmented with the ast-based "no duplicate dict" check
  - `tests/conftest.py` clean (no `sys.path.insert`)
  - Regression suite green (≥ 115 tests)
  - Verbatim log saved to `01-01-pytest.log`

### Risks that remain if shipped as-is (post-audit)
- D1 (Kokoro voice canonical list) — comment-level, not blocking.
- D2 (str-subclass edge case) — academic.
- D3 (importlib.reload semantics) — no current code does it.

None of these are release-blocking for a contracts + scaffolding plan.

### Would I sign my name to this system?
**Yes — post-upgrade.** Pre-upgrade: no. The HF SHA duplication (G1/M2) is exactly the kind of small-seeming defect that creates a "why isn't the new model loading?" incident six months from now. The audit caught it before the code shipped.

---

**Summary:** Applied **3 must-have + 5 strongly-recommended** upgrades to PLAN.md. Deferred **3 can-safely-defer** items.
**Plan status:** Updated and ready for APPLY.

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
*Auditor stance: senior principal engineer + compliance reviewer, treating this as the last review before production.*
