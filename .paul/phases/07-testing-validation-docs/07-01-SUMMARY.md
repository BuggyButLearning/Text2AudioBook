---
phase: 07-testing-validation-docs
plan: 01
subsystem: validation-docs
tags: [smoke-test, opt-in, readme, validation-checklist, release-prep]
requires:
  - phase: 06.2-local-provider-kokoro
    provides: kokoro_synthesis module + install steps
provides:
  - tests/test_openai_smoke.py (opt-in real-API smoke; gated by OPENAI_SMOKE_TEST=1)
  - README.md rewritten for v0.1 multi-provider
  - HUMAN_VALIDATION_CHECKLIST.md release-day walkthrough
affects: []
tech-stack:
  added: []
status: complete
duration: ~15min
started: 2026-05-22
completed: 2026-05-22
---

# 07-01 SUMMARY — Testing, Validation, and Docs

## Outcome
Closed v0.1 with: (a) opt-in real-OpenAI smoke test gated by `OPENAI_SMOKE_TEST=1` env var (skipped by default, ~$0.0001 per run, asserts valid MP3 header + size > 1 KB); (b) full README.md rewrite covering all 3 v0.1 providers (OpenAI / Ollama / Kokoro), env-var docs, install steps, troubleshooting; (c) `HUMAN_VALIDATION_CHECKLIST.md` for the release-day walkthrough (11 sections covering environment, regression, GUI sanity, OpenAI flow, validation errors, Ollama flow, Kokoro flow, smoke test, combine-and-convert utility, credential hygiene, sign-off).

Final suite: **266 passed, 1 skipped in 0.96s**. Skipped test is the opt-in smoke. Zero new third-party deps beyond Phase 6.2's `kokoro / soundfile / huggingface_hub`.

## AC Results

| AC | Title | Result |
|----|-------|--------|
| AC-1 | Opt-in OpenAI smoke test | PASS — `tests/test_openai_smoke.py` skipped by default; runs only when `OPENAI_SMOKE_TEST=1` + valid `OPENAI_API_KEY` are set |
| AC-2 | README rewrite | PASS — provider matrix, env vars, Kokoro install (incl. espeak-ng), troubleshooting, module layout |
| AC-3 | HUMAN_VALIDATION_CHECKLIST.md | PASS — 11 sections, ~50 checkboxes covering all 3 providers + edge cases |
| AC-4 | Regression green; source files untouched | PASS — 266 + 1 skipped; `git diff` confirms no edits to providers/settings/model_discovery/tts_conversion/text_processing/kokoro_synthesis/main/combine_and_convert |

## Files Created

| File | Lines | Purpose |
|------|------:|---------|
| `tests/test_openai_smoke.py` | 56 | Opt-in real-API smoke; cost-bounded per PRD §14.1(c) |
| `README.md` | rewritten | End-user docs for v0.1 |
| `HUMAN_VALIDATION_CHECKLIST.md` | 90 | Pre-tag walkthrough |

## Test Count

| Phase | Tests | Skipped | Δ |
|-------|------:|--------:|---|
| 06.2-01 baseline | 266 | 0 | — |
| **07-01 add** | **266** | **1** | +0 active / +1 opt-in |

## v0.1 Milestone Test Trajectory

| Phase | Total | Δ |
|-------|------:|---|
| 00 baseline | 101 | — |
| 01 | 145 | +44 |
| 02 | 161 | +16 |
| 02.1 | 179 | +18 |
| 03 | 195 | +16 |
| 04 | 228 | +33 |
| 05 | 243 | +15 |
| 06 | 251 | +8 |
| 06.2 | 266 | +15 |
| **07** | **266 + 1 opt-in** | +0 active |

## Loop Status
PLAN ✓ AUDIT (inline) ✓ APPLY ✓ UNIFY ✓ (2026-05-22)

## v0.1 Release Readiness

| Item | Status |
|------|--------|
| All 10 active v0.1 phases (0, 1, 2, 2.1, 3, 4, 5, 6, 6.2, 7) | Complete |
| Phase 6.3 VibeVoice | Deferred to v0.2 per §14.2(1) (no GPU assumption) |
| Suite: 266 + 1 opt-in, exit 0 | ✓ |
| Real-API smoke test | Opt-in, cost-bounded, ready for release-day run |
| Documentation | README + HUMAN_VALIDATION_CHECKLIST shipped |
| Human walkthrough | Awaiting user (Phase 4 AC-7 + Phase 7 checklist) |
| Git commit + tag `v0.1.0` | Pending HITL approval (no `git push` without explicit consent per project memory) |
