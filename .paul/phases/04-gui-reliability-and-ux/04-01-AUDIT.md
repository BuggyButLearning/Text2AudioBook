# Enterprise Plan Audit Report

**Plan:** `.paul/phases/04-gui-reliability-and-ux/04-01-PLAN.md`
**Audited:** 2026-05-21
**Auditor role:** Senior principal engineer + compliance reviewer
**Verdict:** Conditionally acceptable — approved after 0 must-have + 3 strongly-recommended upgrades applied.

---

## 1. Executive Verdict

Phase 4 is the largest behavior-change plan in the milestone: a real threading refactor + cache wiring + validation enrichment + DiscoveryResult consumption. The plan is internally consistent, respects the Phase 1 / 2 / 2.1 / 3 immutability boundaries, and correctly classifies the GUI behavior as something only a human can verify (checkpoint:human-verify at the end).

Pre-audit gaps are correctness-around-the-edges items: a concurrent-click race window, a missing programmatic smoke test for the worker function, and underspecified docs for the new thread-marshaling helper. None are release-blocking on their own; together they harden the plan against regressions that a future contributor (or an LLM running APPLY) might quietly introduce.

Pre-upgrade: would sign with caveats. The threading work is the right shape; the race window between `set_controls_enabled(False)` and worker spawn is a latent UX bug that affects no one today but compounds the moment a user with a fast double-click habit encounters it.
Post-upgrade: yes.

---

## 2. What Is Solid (Do Not Change)

- **Threading model is the correct Tkinter pattern.** `threading.Thread(daemon=True)` for the worker + `root.after(0, ...)` for marshaling back to the main thread is the canonical Tk-with-blocking-work approach. No async, no third-party libraries, no asyncio reactor — just stdlib.
- **`_thread_safe_status` chokepoint discipline.** Single helper for ALL status updates from the worker thread. Direct widget writes from the worker are explicitly forbidden in the action spec. This is exactly the contract you want — testable, auditable, debuggable.
- **`_safe_status_callback` reuse from Phase 2.** Phase 2's UI-callback exception-isolation helper is already in place inside `convert_text_chunk_to_speech`. Phase 4 layers `_thread_safe_status` ON TOP of that without duplicating the try/except — the two patterns compose correctly.
- **Extract-then-test discipline for the validation + status-format helpers.** Pure-Python functions, no Tk imports at call time, testable without instantiating a window. Mirrors the Phase 1 / 2 / 2.1 / 3 pattern of "extract the logic, test the logic, leave the wiring untestable."
- **Late-binding fix in lambda.** Plan correctly uses `lambda exc=exc: ...` for the exception-display lambda — prevents the classic Python closure trap where all lambdas in a loop bind to the final value. Detail-oriented.
- **DiscoveryResult is consumed directly, not via the shim.** `refresh_models` calls `discover_models` (not `list_available_models`) so `source` + `error` are observable. The shim is preserved for back-compat but main.py now uses the rich type. Phase 2.1's contract finally gets used as designed.
- **Checkpoint placement.** ONE `checkpoint:human-verify` at the END of all auto tasks. Not in the middle, not multiple. Avoids verification fatigue while gating the truly subjective behavior (window-responsiveness, dropdown state, status-label ticking).
- **Validation surface is the right shape.** Tuple-returning `(ok, missing)` lets the caller format the message; the helper doesn't bake in messagebox semantics. Reusable, testable, future-proof.

---

## 3. Enterprise Gaps Identified

### G1 — Concurrent-conversion race window
**Pre-audit:** `start_conversion()` calls `set_controls_enabled(False)` and then spawns a worker thread. Between those two operations, the Tk event loop may have BUFFERED a second click on Start. Tk processes the buffered click as if Start were still enabled (the disable hasn't been processed yet), spawning a SECOND worker thread. Two workers writing to the same `output_file.mp3` is a race condition with garbage-output potential.

The fix: a module-level boolean `_conversion_in_progress = False`, checked at the TOP of `start_conversion`, set to True before any UI changes, set back to False in the worker's `finally`. The boolean is a sync primitive even without a lock because Tk's event loop is single-threaded — only one event handler runs at a time, so the read-check-set sequence is atomic from Tk's perspective. The worker thread also only writes False to it (no other writes), so no lock needed.

Severity: **strongly recommended** (UX correctness; user-fast-double-click is realistic).

### G2 — No programmatic test for the worker function
**Pre-audit:** The worker function `_run_conversion_worker(input_file, output_folder, output_filename, settings, timestamp)` references `root` from module scope and calls `root.after(0, ...)` for every UI-side effect. The plan's tests only cover the pure-Python helpers; the actual worker function is entirely covered by the live walkthrough. A regression where someone removes the `_thread_safe_status` chokepoint and writes `status_var.set(...)` directly from the worker would NOT be caught — it would manifest as a flaky GUI on some systems and pass tests on others.

The fix: a smoke test that monkeypatches `main.root` with a fake object whose `.after(delay, callback)` immediately invokes `callback()` (sync), and monkeypatches the synthesis dependencies to deterministic stubs. Assert that the captured status-message sequence contains the expected milestones: "Reading input...", "Preparing text...", "Converting", "Merging audio...", "Conversion completed". This catches the chokepoint-bypass regression even without a real GUI.

Severity: **strongly recommended** (test fidelity; closes a regression path the GUI walkthrough alone cannot guarantee).

### G3 — `_thread_safe_status` thread-safety contract underspecified
**Pre-audit:** The helper is described as "marshal via root.after" but the WHY (Tkinter is not thread-safe; direct widget writes from a worker thread can crash on Windows) is buried in an Avoid bullet. A future contributor seeing the helper without context might be tempted to "simplify" it by inlining the `status_var.set` call.

The fix: a module-level docstring on `_thread_safe_status` explaining: (a) Tkinter's main-thread-only invariant on Windows specifically, (b) why `root.after(0, ...)` is the correct marshaling primitive (it queues into Tk's main event loop), (c) the defensive `RuntimeError` catch handles window destruction during in-flight callbacks.

Severity: **strongly recommended** (maintenance hazard; cheap to fix; the threading contract should be self-documenting).

### G4 — Window-close-during-conversion leaves partial files
**Pre-audit:** Daemon worker thread is killed when the user closes the window mid-conversion. Any partially-written `chunk_part_N_*.mp3` files remain on disk in the output folder. The `output_file.mp3` is created by `concatenate_audio_files` only after all chunks finish, so the final output file isn't half-written — but the intermediate per-chunk files litter the output directory.

The fix: cleanup is realistic but out of Phase 4 scope. Window-close handler (`root.protocol("WM_DELETE_WINDOW", ...)`) is a separate concern with its own race against the daemon thread. Phase 5 (Audio/Video Cleanup) or Phase 7 (Docs) can decide whether to (a) clean up the intermediates on next launch, (b) prompt the user, or (c) leave them for manual cleanup.

Severity: **can safely defer** (Phase 5 / 7).

### G5 — Provider-change refresh still blocks main thread
**Pre-audit:** `on_provider_change` calls `refresh_models()` synchronously when the user changes provider dropdown. This is a 1-3 second network call that blocks the GUI. The conversion is now threaded, but provider-change refresh is not. Consistency would suggest threading it too.

The fix: real, but adds complexity (dropdown state during provider-change-refresh needs to be locked, the worker needs to know it's a refresh-not-conversion). Provider change is a user-initiated infrequent action; 1-3s is acceptable UX for v0.1. If the user feels the lag, Phase 7 can revisit.

Severity: **can safely defer**.

### G6 — `refresh_models` not programmatically tested for `invalidate_cache` invocation
**Pre-audit:** A future refactor that removes the `invalidate_cache(provider)` call would silently return cached results. The plan adds no programmatic test for this — the only signal is the human-verify checkpoint, which is great once but not regression-proof.

The fix: similar to G2 — monkeypatch `main.invalidate_cache` and `main.discover_models`, call `refresh_models()`, assert `invalidate_cache` was called with the provider name before `discover_models`. Requires test-time module-attribute tweaking but doable.

Severity: **can safely defer** — adds complexity for a defect class (silent cache-poisoning) that's already heavily characterized by the human walkthrough and by Phase 2.1's own test suite. Low ROI relative to G2.

### G7 — No test for credential-scrubbed reasons surfacing through the status label
**Pre-audit:** `test_credential_scrubbed_reason_carries_through` exists in the plan's `TestFormatDiscoveryStatus` — it asserts the redacted token survives through `_format_discovery_status`. That covers the formatter. Phase 2.1's audit M1 already covers the source side. The chain is locked end-to-end.

Severity: **not a gap** — well-covered already.

---

## 4. Upgrades Applied to Plan

All strongly-recommended findings applied inline.

### Must-Have (Release-Blocking)

None.

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| S1 | G1 — Concurrent-conversion race window | AC-1 (strengthened), Task 1 source guidance | Added module-level `_conversion_in_progress = False` flag. `start_conversion()` checks it FIRST and returns early (with no error) if True. The flag is set to True before any UI state changes; worker `finally` sets it back to False (via `root.after`). Single-threaded Tk event loop guarantees atomic read-check-set without a lock. |
| S2 | G2 — No programmatic test for the worker | AC-5 (strengthened), Task 2 (new test class) | New `TestRunConversionWorker` in `tests/test_main_gui_logic.py` (separate from the Tk-instantiation-free helpers): monkeypatches `main.root` with a fake object having a sync `.after(delay, callback)` (immediately invokes callback), stubs `read_text_from_file`, `split_text`, `convert_text_to_speech`, `concatenate_audio_files`, `save_user_defaults`, captures the status-message sequence, asserts the expected milestones. Closes the chokepoint-bypass regression path. |
| S3 | G3 — `_thread_safe_status` contract underspecified | Task 1 source guidance | Helper now has an explicit multi-line docstring explaining the Tkinter main-thread invariant, why `root.after(0, ...)` is correct, what the `RuntimeError` catch handles, and the contract that this is the ONLY status-update path allowed from worker threads. |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|----------------------|
| D1 | G4 — Window-close partial-file cleanup | Phase 5 (Audio/Video Cleanup) is the natural home for output-directory hygiene. Daemon thread cleanup-on-close is a separate architectural concern with its own race. |
| D2 | G5 — Provider-change refresh blocks main thread | Provider-change is user-initiated + infrequent; 1-3s lag is acceptable UX for v0.1. Phase 7 can revisit if needed. |
| D3 | G6 — Programmatic test for refresh_models invalidate-call | Low ROI vs. G2; the human-verify checkpoint catches it visually; Phase 2.1's invalidate_cache test suite already characterizes the underlying call. |

---

## 5. Audit & Compliance Readiness

### Defensible audit evidence
- **Before:** Worker function had no programmatic test surface; only the human walkthrough caught chokepoint-bypass regressions.
- **After (S2):** `TestRunConversionWorker` captures the status-call sequence with a fake root; regression-proof.

### Silent failure prevention
- **Before:** Race window between `set_controls_enabled(False)` and worker spawn allowed concurrent conversions on fast-double-click.
- **After (S1):** Explicit `_conversion_in_progress` guard makes double-spawn impossible.

### Post-incident reconstruction
- The threading contract is now documented inline (S3); a future maintainer can reconstruct intent without reading audit history.

### Boundary integrity
- Unchanged. `providers.py` / `settings.py` / `model_discovery.py` / `tts_conversion.py` / `text_processing.py` untouched. No new third-party deps (`threading` is stdlib).

### Test fidelity
- **Before:** Only the GUI walkthrough covered worker-thread behavior.
- **After:** Programmatic smoke test catches chokepoint-bypass + status-message-sequence regressions even when no human is in the loop.

### Ownership of HITL gate
- The checkpoint:human-verify is the explicit, scoped HITL ask for this session. 7 numbered verification steps + 1 optional step. Specific, executable, time-bounded.

---

## 6. Final Release Bar

### What must be true before this plan ships
- 3 strongly-recommended upgrades applied → **Done in this audit pass.**
- APPLY produces:
  - `_conversion_in_progress` flag preventing concurrent worker spawn (S1)
  - `_thread_safe_status` docstring documenting the contract (S3)
  - `TestRunConversionWorker` smoke test (S2)
- Regression suite at ≥ 210 tests (post-S2 floor: 195 baseline + ≥ 13 helper tests + ≥ 4 worker smoke tests), exit 0, < 5.0s
- Human-verify checkpoint passed (7 numbered behaviors confirmed)
- `providers.py` / `settings.py` / `model_discovery.py` / `tts_conversion.py` / `text_processing.py` unchanged
- No new third-party deps

### Risks remaining if shipped as-is (post-audit)
- D1: Window-close mid-conversion intermediates → Phase 5
- D2: Provider-change refresh lag → Phase 7 polish
- D3: Programmatic invalidate_cache assertion → low ROI; characterized indirectly

None blocking for the GUI integration plan.

### Would I sign?
**Yes — post-upgrade.** Pre-upgrade: yes with caveats. The plan's threading shape is correct; the audit's job was to harden the contract against a fast-double-click race (S1) and against a future contributor quietly undoing the chokepoint pattern (S2/S3). Catching both at audit costs ten minutes; catching either via a real-user bug report after release would cost a debugging session and a UX patch loop.

---

**Summary:** Applied **0 must-have + 3 strongly-recommended** upgrades to PLAN.md. Deferred **3 can-safely-defer** items.
**Plan status:** Updated and ready for APPLY.

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
*Auditor stance: senior principal engineer + compliance reviewer, last review before production.*
