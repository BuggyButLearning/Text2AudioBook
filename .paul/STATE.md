# Project State

## Project Reference

See: .paul/PROJECT.md (updated 2026-05-21)

**Core value:** Convert text files into high-quality audiobook MP3s with a choice of hosted (OpenAI) or local (Ollama / Kokoro) TTS providers, without editing code. (VibeVoice deferred to v0.2.)
**Current focus:** v0.1 Modernization MVP — Phase 2 (TTS Engine Modernization)

## Current Position

Milestone: v0.1 Modernization MVP (v0.1.0)
Phase: 2 of 11 (TTS Engine Modernization) — Not started
Plan: Not started
Status: Phase 1 complete; ready to plan Phase 2
Last activity: 2026-05-21 — Phase 1 transition: providers.py contract layer + settings additions shipped to PROJECT.md "Validated"; ROADMAP Phase 1 marked Complete; paul.json advanced to phase 2

Progress:
- Milestone: [██░░░░░░░░] 20% (2 of 10 active v0.1 phases done; Phase 6.3 deferred to v0.2)
- Phase 2: [░░░░░░░░░░] 0%

## Loop Position

Current loop state (next: Phase 2):
```
PLAN ──▶ APPLY ──▶ UNIFY
  ○        ○        ○     [Ready for Phase 2 PLAN]
```
Phase 0: ✅ Complete · Phase 1: ✅ Complete (01-01 PLAN ✓ APPLY ✓ UNIFY ✓).

## Accumulated Context

### Decisions

| Decision | Phase | Impact |
|----------|-------|--------|
| Keep Tkinter UI; modernize under the hood | Phase 0 | Bounds all UX work to in-place changes |
| OpenAI SDK migration replaces raw HTTP TTS | Phase 0 | Drives Phase 2 scope |
| Four-provider abstraction (OpenAI / Ollama / Kokoro / VibeVoice) | Phase 0 | Shapes Phases 1, 6, 6.2, 6.3 |
| Kokoro = recommended local default; VibeVoice = opt-in GPU-only | Phase 0 | Phase 6.3 gated on GPU availability + license opt-in |
| Pin HF model revisions in settings | Phase 0 | Required in Phase 6.2 and 6.3 |
| Real OpenAI smoke test capped <$1 / <5 min | Phase 0 | Constrains Phase 7 test design |
| Conda env named `text2audiobook` (`conda activate text2audiobook`) for all commands | Phase 0 | Enforced via CONDA_ENV_RULE.md; legacy `--prefix .conda` form retired 2026-05-21 |
| 00-02 audited 2026-05-21: verdict conditionally acceptable; 4 must-have + 5 strongly-recommended upgrades applied; .gitignore credential-leak gap closed (M1) | Phase 0 | Plan now enterprise-defensible; AUDIT.md preserved at `.paul/phases/00-discovery-and-approval/00-02-AUDIT.md` |
| 00-02 applied 2026-05-21: 101/101 tests pass in 0.77s; baseline characterization regression net live | Phase 0 | Phases 1, 3, 5, 7 must re-run suite before declaring their own exit criteria |
| key.txt untracked via `git rm --cached` (was tracked since 2024-05-18 commit 4a65c8e on public GitHub remote) | Phase 0 | Local index clean; user must commit + push the removal. Test test_key_txt_not_tracked_by_git enforces it cannot regress. |
| Leaked key.txt content verified as PLACEHOLDER (`<place key here>`, 16 bytes, 401 from OpenAI) | Phase 0 | Threat downgraded: no live credential exposed; no revocation needed; no history scrub needed. test_repo_hygiene.py keeps the guard active for future real keys. |
| 00-01 audited 2026-05-21: verdict conditionally acceptable; 2 must-have + 5 strongly-recommended upgrades applied; 3 deferred | Phase 0 | Plan now enterprise-defensible; paul.json advancement correctly deferred to transition workflow; original PRD text preserved; idempotent propagation; rejection/correction branches added; AUDIT.md preserved at `.paul/phases/00-discovery-and-approval/00-01-AUDIT.md` |
| 00-01 applied 2026-05-21: PRD approved via bulk-accept-all-defaults (see .paul/phases/00-discovery-and-approval/00-01-APPROVAL-PACKET.md) | Phase 0 | All 9 §14 decisions propagated to PRD + PROJECT.md + ROADMAP.md; VibeVoice (Phase 6.3) deferred to v0.2; PRD §14 has zero unannotated "Open"/"TBD" tokens |
| Phase 0 transition complete 2026-05-21: PROJECT.md "Validated (Shipped)" promoted with 3 entries; ROADMAP Phase 0 marked Complete; paul.json advanced to phase 1; git commit `a4d0be6` created locally (not pushed) | Phase 0 → Phase 1 | First milestone progress: 1/10 active v0.1 phases done. Push pending user approval (HITL on git push) |
| 01-01 audited 2026-05-21: verdict conditionally acceptable; 3 must-have + 5 strongly-recommended upgrades applied; 3 deferred | Phase 1 | M1 fail-fast regex compile + revision schema validation; M2 single source of truth (no HF SHA duplication); M3 MappingProxyType immutable registry; S1 MILESTONE constant; S3 frozen-dataclass mutation test; S4 ast no-new-deps test; S5 monkeypatch pattern demo. AUDIT.md preserved at `.paul/phases/01-architecture-and-configuration/01-01-AUDIT.md` |
| 01-01 applied 2026-05-21: providers.py contract layer live; settings.py extended additively; conftest sys.path hack removed (00-02 D3 closes); 145 tests passing in 0.77s | Phase 1 | Single-source-of-truth registry now available for Phase 2 wiring; v0.1 milestone guardrails in code (MILESTONE constant, immutable registry, ast no-new-deps check) |

### Git State
Last Phase 0 commit: `a4d0be6` — feat(00-discovery-and-approval): close Phase 0 with PRD approval and characterization tests
Branch: main
Feature branches merged: none
Push status: not pushed (HITL required)
Pre-existing dirty source files NOT in commit: README.md, combine_and_convert.py, main.py, requirements.txt, text_processing.py, tts_conversion.py — owned by user.

### Deferred Issues

| Issue | Origin | Effort | Revisit |
|-------|--------|--------|---------|
| ~~key.txt historical purge from GitHub~~ | Phase 0 / 00-02 | — | CLOSED 2026-05-21: content verified as placeholder `<place key here>`, no live credential exposed; history purge unnecessary |
| ~~OpenAI key revocation~~ | Phase 0 / 00-02 | — | CLOSED 2026-05-21: not a real key (401 from OpenAI on test) |
| Commit + push the `git rm --cached key.txt` index change | Phase 0 / 00-02 | S | User action; cosmetic now (no real secret) but keeps repo hygiene correct |
| ~~sys.path.insert hack in conftest.py~~ | Phase 0 / 00-02 (audit D3) | — | CLOSED 2026-05-21 by Phase 1 plan 01-01 — `pytest.ini` `pythonpath = .` provides discovery; `sys.path.insert` removed from conftest.py |
| pytest-cov coverage measurement | Phase 0 / 00-02 (audit D1) | S | Phase 7 (Testing, Validation, and Docs) |
| CI workflow integration (.github/workflows/tests.yml) | Phase 0 / 00-02 (audit D2) | M | Phase 7 |
| `concatenate_audio_files` vs `combine_audio_files` naming clarity | Phase 0 / 00-02 | S | Phase 5 (Audio/Video Cleanup) |

### Blockers/Concerns

| Blocker | Impact | Resolution Path |
|---------|--------|-----------------|
| (none — all Phase 0 blockers resolved 2026-05-21) | — | PRD approved; §14.2(1)/(2) resolved by deferring Phase 6.3 to v0.2 |

## Session Continuity

Last session: 2026-05-21
Stopped at: Phase 1 complete; ready to plan Phase 2 (TTS Engine Modernization).
Next action: `/paul:plan` for Phase 2.
Resume file: .paul/ROADMAP.md

---
*STATE.md — Updated after every significant action*
