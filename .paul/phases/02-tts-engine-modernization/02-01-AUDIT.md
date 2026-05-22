# Enterprise Plan Audit Report

**Plan:** `.paul/phases/02-tts-engine-modernization/02-01-PLAN.md`
**Audited:** 2026-05-21
**Auditor role:** Senior principal engineer + compliance reviewer
**Verdict:** Conditionally acceptable — approved after 1 must-have + 6 strongly-recommended upgrades applied.

---

## 1. Executive Verdict

Phase 2 plan is well-scoped: it respects Phase 1's immutability invariants, defers tts_conversion.py wiring to the right place, and pre-anticipates the case-sensitivity behavior shift. But the pre-audit version had three classes of enterprise-grade defect:

1. **Source-of-truth drift risk.** `settings.OPENAI_FALLBACK_MODELS` and `providers.PROVIDER_REGISTRY["OpenAI"].fallback_models` are two surfaces that must stay in sync. The plan didn't enforce this. Phase 1's M2 audit closed the same defect class for HF revisions — same hygiene needed here.
2. **Hot-loop regex recompilation + missing failure isolation.** `_validate_ollama_model_support` runs inside `convert_text_chunk_to_speech` for every chunk + every retry; recompiling the regex each call is wasteful. Worse, `status_callback` exceptions (e.g. Tkinter "main thread not in main loop" after GUI close) would have aborted the chunk conversion — a UI failure leaking into the synthesis path.
3. **Test fidelity.** `with_streaming_response` mock did not actually write bytes to disk, so the file-on-disk contract was unverified. DeprecationWarning absence was only implicitly checked (via pytest.ini filterwarnings=error), not explicitly proven.

After applying the must-have + strongly-recommended upgrades inline, the plan is approved for APPLY.

Pre-upgrade: would not sign for production. Source-of-truth drift is the kind of defect that ships, hides for months, then explains an outage post-mortem.
Post-upgrade: yes.

---

## 2. What Is Solid (Do Not Change)

- **Boundary discipline.** No `providers.py` edits (Phase 1 immutability respected). No leakage into Phase 2.1 / 3 / 4 / 5 / 6 scope. No new third-party deps.
- **Behavior-shift pre-characterization.** Plan anticipates the case-sensitivity change in `_filter_openai_tts_models` and assigns `# CHARACTERIZED — Phase 2:` comments to the tests that need updating. Surfaces the change deliberately rather than as a silent regression.
- **Structured logging requirements.** Plan explicitly forbids logging the API key or full chunk text, and pre-defines the 80-char preview. Right calibration for an enterprise audit trail.
- **Concurrency-clamp primitive.** `min(requested, registry_cap)` for local providers is the right model — local synthesis is memory-bound by definition, hosted is rate-limit-bound, so the policy correctly splits.
- **Frozen public signatures.** `convert_text_chunk_to_speech`, `convert_text_to_speech`, `concatenate_audio_files`, `list_available_models` keep their existing signatures. Callers in `main.py` won't break.
- **Pre-PAUL baseline acknowledged.** Plan correctly notes that `f2ff098` already landed the SDK migration baseline; Phase 2 is integration polish, not a from-scratch refactor.
- **Phase 1 monkeypatch pattern reused.** S5 from 01-01 audit ("monkeypatch fake providers, never mutate the registry") is the canonical fake-injection method in the new tests. Continuity.
- **Verify steps are executable.** Each task has runnable `python -c "..."` or `grep` verification, not "check it works".

---

## 3. Enterprise Gaps Identified

### G1 — `re.compile` inside hot loop
`_validate_ollama_model_support` is called inside `convert_text_chunk_to_speech` for every chunk for every retry. Compiling the regex on each call wastes cycles. The pattern is fixed at module import (Phase 1 invariant); compile once.

Severity: **strongly recommended** (perf hygiene; not safety).

### G2 — `OPENAI_FALLBACK_MODELS` ↔ registry drift risk
`settings.OPENAI_FALLBACK_MODELS = ["tts-1", "tts-1-hd"]` and `providers.PROVIDER_REGISTRY["OpenAI"].fallback_models = ("tts-1", "tts-1-hd")` are conceptually the same list but stored separately. Phase 2 makes `tts_conversion.py` read from the registry but leaves `settings.py` referencing its own constant. Future contributor updates one without the other; behavior diverges silently. Same defect class as Phase 1 G1/M2 (HF revisions).

Severity: **must-have**.

### G3 — `status_callback` exception aborts chunk
Current code: `if status_callback: status_callback(...)`. If the callback raises (Tkinter "main thread not in main loop" after GUI close, or any user-supplied callback bug), the exception falls into the `except Exception` retry loop. Three retries burned on a UI bug. Worse: the chunk that "failed" actually never had a chance to synthesize — the failure happened before `_write_openai_speech` was called.

Severity: **strongly recommended** (correctness + audit-trail integrity).

### G4 — `_write_openai_speech` test mock doesn't write bytes
Pre-audit `FakeStream.stream_to_file(path)` only records the call. The real `stream_to_file` writes bytes to disk. A test that doesn't exercise the write path can't catch a regression where the path argument gets ignored or the file is created at the wrong location.

Severity: **strongly recommended**.

### G5 — DeprecationWarning absence is implicit
AC-7 says "no DeprecationWarning from openai appears in the log". The mechanism is `pytest.ini` setting `filterwarnings = error` (from 00-02 audit S1), which converts DeprecationWarning into a hard test failure. That's good, but it's not directly testing the contract of `_write_openai_speech` — it's testing the test runner config. An explicit `warnings.catch_warnings(record=True)` test would prove the function emits no DeprecationWarning independent of how pytest is configured.

Severity: **strongly recommended**.

### G6 — Concurrency-clamp log line is informational, not policy-explicit
Pre-audit log: `"convert_text_to_speech provider=X requested_concurrency=N effective_max_workers=M chunks=K"`. Reader has to mentally compute "wait, requested was 8 and effective is 1 — must've been clamped". An explicit log message ("clamped requested=8 to registry-default=1 for local provider Ollama") makes the policy decision auditable at a glance.

Severity: **strongly recommended** (audit-trail readability).

### G7 — Non-string input handling for `_validate_ollama_model_support`
Pre-audit AC-2 says "None and empty string still return False". But the registry-driven implementation must explicitly type-guard against integers, lists, objects, etc. The old code's `(model_name or "").lower()` would raise `AttributeError` on a non-string — the new code's `re.search` would too unless guarded. Plan should explicitly add type check and assert it.

Severity: **strongly recommended**.

### G8 — Retry-everything semantics not flagged
PRD §FR-5 says "retry transient failures". Current code retries every exception, including non-transient ones like `AuthenticationError` and `BadRequestError`. Burning 3 attempts on a 401 wastes time and produces noisy logs. Plan preserves this behavior without flagging it.

Severity: **can safely defer** — Phase 2 scope is integration polish; introducing an exception allowlist is a real semantic change worth its own plan. Flagging in deferred-issues list rather than expanding scope here.

### G9 — Mock fidelity on `with_streaming_response.create` kwargs
The test asserts kwargs match `{"model", "voice", "input", "speed", "response_format"}`. If a future openai SDK version requires a new mandatory kwarg, the mock still passes — but the real call would fail. Versions of this fidelity gap exist in every SDK mock; not unique to this plan.

Severity: **can safely defer** — pin openai version in requirements.txt as the long-term mitigation; that's Phase 6.2 / 7 scope.

### G10 — Voice value logged unredacted
For OpenAI voices ("alloy", etc.) this is fine. For Ollama where users may name local models or voices, the logged value could echo user-controlled strings. Standard caution; no PII risk in current scope.

Severity: **can safely defer** — voices in v0.1 come from the registry (closed enumeration); user-named voices are a Phase 6.2 / 6.3 concern.

---

## 4. Upgrades Applied to Plan

All must-have + strongly-recommended findings applied inline. Audit-added content tagged with `audit-added M1`, `audit-added S1`, etc.

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| M1 | G2 — settings/registry fallback drift | New AC-1b, Task 2 step 1 | Added `test_fallback_consistency_settings_vs_registry` asserting `list(settings.OPENAI_FALLBACK_MODELS) == list(PROVIDER_REGISTRY["OpenAI"].fallback_models)`. Locks the same single-source invariant Phase 1's M2 audit closed for HF revisions. |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| S1 | G1 — regex recompilation per call | AC-1, AC-2, Task 1 step 2 | Added module-level constants `_OPENAI_MODEL_RE` and `_OLLAMA_MODEL_RE` compiled once at import. Functions reference these instead of compiling inline. |
| S2 | G3 — `status_callback` exception leak | New AC-5b, Task 1 step 6 | Added `_safe_status_callback` helper wrapping callback in try/except + WARNING log. New test class `TestStatusCallbackIsolation` verifies a raising callback does NOT abort the chunk. |
| S3 | G4 — fake stream writes no bytes | AC-3 (strengthened), Task 2 step 5 | `FakeStream.stream_to_file` now writes `b"FAKE_AUDIO_PAYLOAD"` to the actual path. Test asserts file contents on disk. |
| S4 | G7 — non-string input handling | AC-2 (strengthened), Task 1 step 4, Task 2 step 2 | Plan now mandates explicit `isinstance(model_name, str)` guard at the top of `_validate_ollama_model_support`. Added parametrized test `test_non_string_inputs_return_false` covering int / float / list / dict / object / bool. |
| S5 | G5 — DeprecationWarning absence implicit | AC-3 (strengthened), new test `test_no_deprecation_warning_emitted` | Test wraps `_write_openai_speech` in `warnings.catch_warnings(record=True)` with `simplefilter("always")` and asserts captured DeprecationWarning records == []. Direct proof, independent of pytest.ini config. |
| S6 | G6 — clamp log not policy-explicit | AC-4 (strengthened), Task 1 step 7 | Three-branch log: "clamped requested=X to registry-default=Y for local provider Z" (when clamp fires), "using requested concurrency=N for local provider Z" (under cap), "using requested concurrency=N for provider Z" (hosted). Auditor sees the policy decision at a glance. |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|----------------------|
| D1 | G8 — retry-everything semantics | Real behavior shift, deserves its own plan with classification of transient (HTTP 5xx, RateLimitError, APIConnectionError) vs non-transient (AuthenticationError, BadRequestError) exceptions. Flag for Phase 7 (Testing, Validation, Docs) or a Phase 2.x follow-up. Not blocking Phase 2 integration. |
| D2 | G9 — mock kwarg fidelity to future openai SDKs | Mitigation is pinning openai version in `requirements.txt`. Already `openai>=1.0.0`; can tighten in Phase 7 release prep. Out of Phase 2 scope. |
| D3 | G10 — voice value logged unredacted | v0.1 voices are closed-enumeration from the registry. User-named local voices arrive in Phase 6.2 / 6.3 alongside the question of what's safe to log. Defer to those phases. |

---

## 5. Audit & Compliance Readiness

### Defensible audit evidence
- **Before:** Pytest log records pass/fail; reader has to know that pytest.ini's `filterwarnings = error` is what catches DeprecationWarning. Indirect.
- **After (S5):** Explicit catch_warnings test produces a direct assertion. Audit trail says "function emits no DeprecationWarning" by name.

### Silent failure prevention
- **Before:** Fallback model list could silently diverge between `settings.py` and `providers.py`.
- **After (M1):** `test_fallback_consistency_settings_vs_registry` fails loudly on drift.
- **Before:** Callback exception silently consumed retry budget; chunk "fails" with no synthesis ever attempted.
- **After (S2):** Callback wrapped; failure logged at WARNING; synthesis proceeds unaffected.

### Post-incident reconstruction
- **Before:** Log shows `requested_concurrency=8 effective_max_workers=1`. Reader has to know what "registry-default" means.
- **After (S6):** Log shows `clamped requested=8 to registry-default=1 for local provider Ollama (chunks=12)`. Self-explanatory.

### Boundary integrity
- Unchanged. `providers.py` untouched. `settings.py` referenced only as read source for the consistency test. No new third-party deps.

### Test fidelity
- **Before (G4):** Fake stream didn't write bytes; "file exists" was unverified.
- **After (S3):** Fake writes a known sentinel byte string; test reads it back. Path + write contract both exercised.

---

## 6. Final Release Bar

### What must be true before this plan ships
- Must-have + strongly-recommended upgrades applied → **Done in this audit pass.**
- APPLY produces:
  - `tts_conversion.py` with module-level compiled regex constants
  - `_safe_status_callback` helper isolating UI failures from synthesis
  - Three-branch clamp log message
  - Fake stream that writes bytes (test fidelity)
  - Explicit DeprecationWarning catch_warnings test
  - Fallback consistency test asserting `settings ≡ registry`
- Regression suite at ≥ 155 tests, < 5.0s, exit 0
- `providers.py` unchanged (Phase 1 immutability)
- No new third-party deps

### Risks remaining if shipped as-is (post-audit)
- D1: retry-everything semantics — known issue, flagged for follow-up plan
- D2: openai SDK version drift — pin in Phase 7
- D3: user-named voice logging — Phase 6.2/6.3 territory

None blocking for an integration plan.

### Would I sign?
**Yes — post-upgrade.** Pre-upgrade: no. M1 (drift) and S2 (callback isolation) are subtle defects that compound; catching them at audit costs ten minutes here vs days of post-mortem later.

---

**Summary:** Applied **1 must-have + 6 strongly-recommended** upgrades to PLAN.md. Deferred **3 can-safely-defer** items.
**Plan status:** Updated and ready for APPLY.

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
*Auditor stance: senior principal engineer + compliance reviewer, last review before production.*
