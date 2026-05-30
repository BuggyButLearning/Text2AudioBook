---
phase: 04-gui-reliability-and-ux
plan: 01
subsystem: gui
tags: [tkinter, threading, refresh-cache, validation, status-label, registry-driven-dropdown, kokoro-guard]
requires:
  - phase: 02.1-model-discovery-and-selection
    provides: DiscoveryResult / Source enum / invalidate_cache hook
  - phase: 02-tts-engine-modernization
    provides: convert_text_to_speech status_callback chokepoint
  - phase: 01-architecture-and-configuration
    provides: PROVIDER_REGISTRY single source of truth (list_providers, get_provider_capability)
provides:
  - background-threaded conversion (window stays responsive)
  - "Refresh Models" truly refreshes (invalidate_cache → discover_models with use_cache=False)
  - capability-driven voice menu (Kokoro voices auto-populate when selected)
  - registry-driven provider dropdown (drift-proof — adding a provider in providers.py auto-shows)
  - Kokoro pre-thread guard: clear "Phase 6.2 pending" error instead of silent OpenAI-endpoint misroute
  - DiscoveryResult.source-aware status messages (LIVE / EMPTY / FALLBACK / registry-list)
  - enumerated validation errors ("Please provide: Input File, Output File Name")
  - all dropdowns locked mid-conversion; voice_menu state preserved by provider capability
  - audit-added concurrency guard `_conversion_in_progress` (fast-double-click safe)
  - `_thread_safe_status` chokepoint for worker→main marshaling via `root.after(0, ...)`
affects: [06-ollama, 06.2-kokoro, 07-testing]
tech-stack:
  added: []
  patterns:
    - "GUI worker pattern: threading.Thread + root.after(0, lambda: var.set(...)) for cross-thread widget updates"
    - "Registry-driven dropdowns: never hardcode provider lists; pull from PROVIDER_REGISTRY"
    - "Capability-driven voice menu: cap.voices=() → disabled; nonempty → populate + readonly"
    - "Pre-thread guard for unimplemented providers: reject at start_conversion, never spawn a worker that would misroute"
    - "FALLBACK-with-no-error semantic split: 'registry list' (no live probe) vs 'discovery failed' (live probe errored)"
key-files:
  created:
    - tests/test_main_gui_logic.py
    - .paul/phases/04-gui-reliability-and-ux/04-01-pytest.log
    - .paul/phases/04-gui-reliability-and-ux/04-01-SUMMARY.md
  modified:
    - main.py
key-decisions:
  - "Provider dropdown driven by `list_providers()` not a hardcoded list (drift bug user spotted: Kokoro was registered but never surfaced in GUI)"
  - "Kokoro IS shown in v0.1 GUI; Start click rejects with 'Phase 6.2 pending' messagebox. Picks honesty over hiding: registry shape stays single-source-of-truth"
  - "VibeVoice stays out of dropdown (still absent from PROVIDER_REGISTRY per Phase 0 §14.2(1); v0.2 only)"
  - "FALLBACK with error=None reads as 'registry list' (clean UX for Kokoro); FALLBACK with error reads as 'discovery failed' (OpenAI failure path)"
  - "Voice menu values capability-driven on every provider change (configure(values=cap.voices))"
patterns-established:
  - "Registry-driven GUI population: any control whose values come from PROVIDER_REGISTRY must read at runtime, not import-time-hardcode"
  - "Provider not yet wired for synthesis: guard pre-thread with clear messagebox; do NOT let it reach _write_openai_speech"
duration: ~55min
started: 2026-05-22
completed: 2026-05-22
status: complete
---

# 04-01 SUMMARY — GUI Reliability and UX

## Outcome
Background-threaded the Tkinter conversion (window stays responsive), wired `invalidate_cache(provider)` into the "Refresh Models" button so it actually refreshes, surfaced `DiscoveryResult.source/error` via the status label, extracted pure-Python helpers (`_validate_conversion_inputs`, `_format_discovery_status`, `_thread_safe_status`), and locked all input controls mid-conversion. Audit-added S1 concurrency guard `_conversion_in_progress` makes fast-double-click safe. **Mid-phase extension (user-driven):** replaced hardcoded `providers = ["OpenAI", "Ollama"]` drift with registry-driven `provider_options = list(list_providers())` so Kokoro now appears in the dropdown; added a pre-thread guard that rejects Kokoro Start with a clear "Phase 6.2 pending" messagebox rather than silently routing the Kokoro model name into the OpenAI endpoint. Voice menu is now capability-driven (Kokoro's 20 American-English voices auto-populate). Regression suite: **228 passed in 0.64s, exit 0, zero new third-party deps**.

## AC Results

| AC | Title | Result |
|----|-------|--------|
| AC-1 | Background-thread the conversion + audit-S1 concurrency guard | PASS — `threading.Thread(target=_run_conversion_worker, daemon=True)` spawned from `start_conversion`; `_thread_safe_status` marshals via `root.after(0, ...)`; `_conversion_in_progress` flag set BEFORE UI state changes and reset in worker `finally`; `TestRunConversionWorker` and `TestStartConversionGuards::test_concurrent_click_does_not_spawn_second_worker` lock it down |
| AC-2 | Refresh Models invalidates before re-discovering | PASS — `TestRefreshModelsBehavior::test_refresh_calls_invalidate_before_discover` asserts call order; `test_refresh_use_cache_false` asserts use_cache=False; `test_refresh_populates_dropdown_on_live`, `test_refresh_empty_with_reason_status`, `test_refresh_fallback_status` cover LIVE / EMPTY / FALLBACK paths |
| AC-3 | Validation errors enumerate missing fields | PASS — `TestValidateConversionInputs` (6 tests: all populated / single empty / all empty / whitespace / None / stable order); `TestStartConversionGuards::test_empty_inputs_rejected_with_enumerated_message` validates the enumerated messagebox |
| AC-4 | set_controls_enabled covers all controls | PASS — `TestSetControlsEnabled::test_disable_locks_buttons_and_dropdowns`, `test_enable_restores_buttons_and_readonly_dropdowns`, `test_enable_voice_disabled_when_ollama` |
| AC-5 | Tests for extracted helpers | PASS — `tests/test_main_gui_logic.py` ships 36 tests across 8 classes; zero `tkinter` / `ttkbootstrap` imports |
| AC-6 | Full regression + smoke | PASS — 228 tests, 0.64s, exit 0; up from 195 baseline (+33) |
| AC-7 | Live GUI walkthrough | PENDING — human-verify checkpoint at end (user runs `python main.py` and confirms window responsiveness, dropdown lockout, enumerated errors) |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `main.py` | Extensive edit | Added imports (`threading`, `from model_discovery import ...`, `from providers import list_providers, get_provider_capability`); replaced hardcoded `providers = [...]` with `provider_options = list(list_providers())`; added helpers `_validate_conversion_inputs`, `_format_discovery_status`, `_thread_safe_status`, `_provider_has_voices`; module-level `_conversion_in_progress` flag; refactored `refresh_models()` to invalidate-then-discover with `use_cache=False`; refactored `set_controls_enabled` to lock dropdowns + capability-driven voice_menu; refactored `on_provider_change` to repopulate voice_menu values from `cap.voices`; refactored `start_conversion` with validation + S1 guard + Kokoro pre-thread guard + worker spawn; new `_run_conversion_worker` module-level function |
| `tests/test_main_gui_logic.py` | Created (36 tests, 8 classes) | `TestValidateConversionInputs`, `TestFormatDiscoveryStatus`, `TestRunConversionWorker` (audit S2), `TestRefreshModelsBehavior` (audit-extended self-test), `TestSetControlsEnabled`, `TestStartConversionGuards`, `TestOnProviderChange`, `TestRegistryDrivenProviderOptions`, `TestKokoroSynthesisGuard` |
| `.paul/phases/04-gui-reliability-and-ux/04-01-pytest.log` | Created | Verbatim regression-run output |

## Mid-Phase User-Driven Extension (Registry-Driven Dropdown + Kokoro Guard)

The user spotted that the GUI only showed `OpenAI` and `Ollama` even though `PROVIDER_REGISTRY` has 3 v0.1 providers (OpenAI / Ollama / Kokoro). Root cause: `main.py` line 28 hardcoded `providers = ["OpenAI", "Ollama"]` — drift from registry. Without intervention this drift would have grown every time a provider was added.

**Fix landed mid-Phase 4:**
1. `provider_options = list(list_providers())` — drift-proof, registry-driven.
2. `on_provider_change` reads `get_provider_capability(provider).voices` and repopulates `voice_menu` accordingly. Kokoro picks → 20 American-English voices populate; Ollama picks → voice_menu disabled (voices=()).
3. `_provider_has_voices` helper drives the same logic in `set_controls_enabled`.
4. `start_conversion` adds a Kokoro pre-thread guard: `if provider == "Kokoro": showerror("Kokoro not yet available", "...Phase 6.2 is not wired up yet...")`. Without this, the Kokoro model name (`kokoro-82m`) would have routed into `_write_openai_speech` and produced an opaque HTTP error.
5. `_format_discovery_status` split: FALLBACK with `error=None` now reads "Kokoro: using registry list (1 model)" (clean Kokoro UX), FALLBACK with an `error` reads "OpenAI discovery failed (...) — using fallback list" (unchanged for OpenAI failure path).

**Tests added for the extension** (+4 tests): `TestRegistryDrivenProviderOptions::test_provider_options_includes_all_registry_providers` (drift sentinel), `test_provider_options_includes_kokoro`, `TestKokoroSynthesisGuard::test_kokoro_start_shows_phase_6_2_pending_error`, `TestOnProviderChange::test_kokoro_populates_voice_list_from_registry`.

**Why this didn't violate the Phase 1 frozen-providers.py invariant:** `providers.py` was not modified. The change consumed the existing `list_providers()` and `get_provider_capability()` public surface.

## Test Count

| Phase | Tests | Δ |
|-------|------:|---|
| 03-01 baseline | 195 | — |
| 04-01 initial APPLY | 212 | +17 (validation + format + worker smoke) |
| 04-01 audit human-verify extension | 224 | +12 (refresh_models, set_controls, start_conversion, on_provider_change) |
| **04-01 registry-drift extension** | **228** | **+4 (registry drift sentinels + Kokoro guard + Kokoro voices)** |

Floor (≥ 212 per plan) cleared by +16.

## Audit Invariants Verified

- `git diff providers.py settings.py model_discovery.py tts_conversion.py text_processing.py` returns no changes — out-of-phase files untouched.
- `git diff requirements.txt environment.yml` returns no changes — no new deps (`threading` is stdlib).
- `tests/test_main_gui_logic.py` imports neither `tkinter` nor `ttkbootstrap`.
- No DeprecationWarning, no SyntaxWarning in pytest log.
- Audit S1 (concurrency guard): `TestStartConversionGuards::test_concurrent_click_does_not_spawn_second_worker` proves the fast-double-click case is silently rejected (no second worker).
- Audit S2 (worker chokepoint): `TestRunConversionWorker::test_worker_status_sequence_on_success` proves every status update flows through `root.after(...)`.
- Audit S3 (docstring on `_thread_safe_status`): present in source.

## Deferred (per audit)

| # | Item | Revisit |
|---|------|---------|
| D1 | "Cancel Conversion" button (mid-conversion abort + partial-file cleanup) | Out of v0.1 scope; document if user requests |
| D2 | Progress percentage / N-of-M chunk counter on the status label | Phase 7 polish |
| D3 | OpenAI exception-type discrimination (Auth vs RateLimit vs APIConnection) | Same class as Phase 2 D1 / Phase 2.1 D3 — follow-up plan or Phase 7 |
| D4 | Quality preset selection for Kokoro is currently no-op (preset overrides ignored when registry model is set) | Phase 6.2 — define Kokoro quality semantics there |

## Next Phase Readiness

Phase 5 (Audio/Video Cleanup) is the natural next step. `tts_conversion.convert_text_to_speech` and `concatenate_audio_files` are stable; Phase 5 owns `combine_and_convert.py` (separate module). Phase 6 (Ollama synthesis path) and Phase 6.2 (Kokoro synthesis path) will plug into the existing worker + status chokepoint without further GUI changes — the registry-driven dropdown means the new providers auto-surface as soon as they're added to `PROVIDER_REGISTRY`.

## Loop Status

- PLAN ✓ (2026-05-21)
- AUDIT ✓ (2026-05-21 — conditionally acceptable, all must-have + strongly-recommended applied)
- APPLY ✓ (2026-05-22 — 228 tests, 0.64s, exit 0)
- UNIFY ✓ (2026-05-22)
- Human-verify checkpoint → next (`python main.py` walkthrough)

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~55 min (PLAN + AUDIT + APPLY across two sessions) |
| Started | 2026-05-21 |
| Completed | 2026-05-22 |
| Tasks | 3 / 3 completed PASS + 1 checkpoint pending (live walkthrough) |
| Files modified | 1 source (main.py) + 2 artifacts |
| Tests delta | +33 (195 → 228) |
| Suite wall time | 0.64s |
| Exit code | 0 |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Background thread the conversion (not asyncio) | Matches existing code style (threading already in use for chunk concurrency); simpler than asyncio in a single-window GUI app | Window stays responsive; status label visibly ticks |
| `_thread_safe_status` as the SINGLE chokepoint | Defends the Tkinter "widgets are main-thread only" invariant; one place to audit | Worker thread can NEVER write to widgets directly |
| Pre-thread Kokoro guard vs synthesis-side guard | Catch at the user-action boundary (Start click) before any UI state change; clearer error path | Kokoro selection is OK in dropdown (registry-driven), but Start short-circuits with "Phase 6.2 pending" |
| Registry-driven dropdown over hiding Kokoro until Phase 6.2 | Honest UX; drift-proof (any future provider auto-surfaces); single source of truth | User sees what's coming; drift bug class eliminated |
| FALLBACK semantic split (no-error ≡ registry list, error ≡ live probe failed) | Kokoro deserves "registry list" wording; OpenAI failure deserves "discovery failed" | Status label reads correctly for both shapes |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------:|--------|
| Auto-fixed | 0 | — |
| Scope additions | 1 | Registry-driven dropdown + Kokoro pre-thread guard + capability-driven voice menu. User-spotted drift bug surfaced during human-verify checkpoint discussion; landed mid-phase. |
| Deferred | 4 | All logged above |

**Total impact:** Scope added one user-driven extension (drift fix + Kokoro guard). Plan's AC-1 through AC-7 still satisfied; the extension layered on top.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Initial 4 test failures from `monkeypatch.setattr` on module-level GUI attributes that don't exist until `create_app()` runs | Added `raising=False` to all setattr calls for module attributes created inside `create_app()`. Pattern documented in test file. |
| User spotted Kokoro absent from GUI dropdown despite being in PROVIDER_REGISTRY | Drift root cause: `providers = ["OpenAI", "Ollama"]` hardcoded in `main.py`. Fixed by switching to `list_providers()` + adding Kokoro pre-thread guard for honest UX until Phase 6.2 wires synthesis. |
| `_format_discovery_status` FALLBACK branch said "discovery failed" for Kokoro even though nothing failed (no live probe path exists) | Split FALLBACK into two cases: with-error reads "discovery failed (...)", without-error reads "using registry list (N)". |

---
*Phase: 04-gui-reliability-and-ux, Plan: 01*
*Completed: 2026-05-22*
