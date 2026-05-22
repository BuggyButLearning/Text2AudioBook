# Project State

## Project Reference

See: .paul/PROJECT.md (updated 2026-05-21)

**Core value:** Convert text files into high-quality audiobook MP3s with a choice of hosted (OpenAI) or local (Ollama / Kokoro) TTS providers, without editing code. (VibeVoice deferred to v0.2.)
**Current focus:** v0.1 Modernization MVP — Phase 3 (Text Processing Improvements)

## Current Position

Milestone: v0.1 Modernization MVP (v0.1.0)
Phase: 3 of 11 (Text Processing Improvements) — Ready to plan
Plan: Not started
Status: Ready to plan
Last activity: 2026-05-21 — Phase 2.1 transition complete: PROJECT.md "Validated" + 5 Phase 2.1 key decisions promoted; ROADMAP Phase 2.1 marked Complete; paul.json advanced to phase 3; phase commit pending stage+commit.

Progress:
- Milestone: [████░░░░░░] 40% (4 of 10 active v0.1 phases done; Phase 6.3 deferred to v0.2)
- Phase 3: [░░░░░░░░░░] 0% (planning to start)

## Loop Position

Current loop state:
```
PLAN ──▶ APPLY ──▶ UNIFY
  ○        ○        ○     [Idle — ready for Phase 3 PLAN]
```
Phase 0: ✅ Complete · Phase 1: ✅ Complete · Phase 2: ✅ Complete · Phase 2.1: ✅ Complete.

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
| Phase 1 transition complete 2026-05-21: PROJECT.md gained 3 "Validated (Shipped)" entries; ROADMAP Phase 1 marked Complete; paul.json advanced to phase 2; git commit `5cead5c` created locally (not pushed) | Phase 1 → Phase 2 | Milestone progress: 2/10 active v0.1 phases done. Push pending user approval (HITL on git push) |
| Pre-PAUL modernization edits committed 2026-05-21 as `f2ff098`: tts_conversion SDK migration + Ollama discovery + retries; text_processing paragraph/sentence-aware chunking; main.py ttkbootstrap GUI + provider/quality/voice dropdowns; combine_and_convert ffmpeg GPU-aware; requirements pinned | Phase 1 → Phase 2 | Phase 2 (and partially 3/4/5) baseline now in HEAD. Phase 2 plan can focus on integrating providers.py registry into the already-migrated SDK code rather than from-scratch refactor. Regression net still 145/145 green after the commit. |
| 02-01 audited 2026-05-21: verdict conditionally acceptable; 1 must-have + 6 strongly-recommended upgrades applied; 3 deferred | Phase 2 | M1 settings/registry fallback consistency test; S1 module-level compiled regex; S2 status_callback exception isolation; S3 fake stream writes bytes; S4 non-string input guard; S5 explicit DeprecationWarning catch_warnings; S6 explicit clamp-event log message. AUDIT.md at `.paul/phases/02-tts-engine-modernization/02-01-AUDIT.md` |
| 02-01 applied 2026-05-21: tts_conversion.py now consumes providers.PROVIDER_REGISTRY (module-level compiled regex), `_write_openai_speech` uses with_streaming_response context manager, concurrency clamp + structured logging + `_safe_status_callback` isolation live; 161 tests pass in 0.64s; zero DeprecationWarning; providers.py untouched | Phase 2 | Registry-driven implementation gap closed; Phase 2.1 can build on `list_openai_models`/`list_ollama_models` for Refresh Models UI flow. SUMMARY.md + pytest log at `.paul/phases/02-tts-engine-modernization/`. |
| 02-01 unified 2026-05-21: SUMMARY.md augmented with full frontmatter (requires/provides/affects/key-decisions/patterns); performance, deviations (0 auto-fix / 0 scope-add / 3 audit-deferred), task commits (deferred to phase commit at transition), issues (none) sections added; loop closed | Phase 2 | Single plan in Phase 2 → transition workflow required next (PROJECT.md promote, ROADMAP Phase 2 Complete, paul.json → 2.1, phase git commit) |
| Phase 2 transition complete 2026-05-21: PROJECT.md gained 4 "Validated (Shipped)" entries + 4 Phase 2 Key Decisions; ROADMAP Phase 2 marked Complete; Phase 2.1 promoted to Planning; paul.json advanced to phase 2.1; git commit `92a902e` created locally (not pushed) | Phase 2 → Phase 2.1 | Milestone progress: 3/10 active v0.1 phases done. Push pending user approval (HITL on git push) |
| 02.1-01 audited 2026-05-21: verdict conditionally acceptable; 1 must-have + 5 strongly-recommended upgrades applied; 3 deferred | Phase 2.1 | M1 `_scrub_api_key` helper + credential-not-in-logs test; S1 Source.EMPTY for OpenAI live-but-allowlist-empty (parity with Ollama); S2 canonical Ollama URL in cache key (None ≡ default ≡ trailing-slash); S3 None-vs-default api_key cache-sharing test; S4 explicit FALLBACK-cached-until-invalidate test; S5 `error` field contract: short user-readable string, credential-scrubbed. AUDIT.md at `.paul/phases/02.1-model-discovery-and-selection/02.1-01-AUDIT.md` |
| 02.1-01 applied 2026-05-21: model_discovery.py module created with DiscoveryResult+Source+_scrub_api_key+_canonical_ollama_url+discover_models+invalidate_cache; tts_conversion.py reduced to thin shims; Ollama curated allowlist filter live (PRD §14.1(a)); 179 tests pass in 0.67s; zero DeprecationWarning; main.py untouched; providers.py untouched; 1 DRIFT auto-fixed via characterization | Phase 2.1 | Discovery now decoupled from synthesis; Phase 4's Refresh Models button has clean hook (invalidate_cache + discover_models). SUMMARY.md + pytest log at `.paul/phases/02.1-model-discovery-and-selection/`. |

### Git State
Last commit: `92a902e` — feat(02-tts-engine-modernization): close Phase 2 with registry-driven TTS + non-deprecated streaming SDK
Phase 2 commit: `92a902e` — feat(02-tts-engine-modernization): close Phase 2 with registry-driven TTS + non-deprecated streaming SDK
Pre-PAUL baseline: `f2ff098` — chore(pre-paul): land in-progress modernization edits as Phase 2-5 baseline
Phase 1 commit: `5cead5c` — feat(01-architecture-and-configuration): close Phase 1 with provider abstraction contracts
Phase 0 commit: `a4d0be6` — feat(00-discovery-and-approval): close Phase 0 with PRD approval and characterization tests
Branch: main
Feature branches merged: none
Push status: not pushed (HITL required for git push)
Working tree: clean except IDE noise (.vscode/, test_tracking/.vscode.configs.import.cspell.config.json) — neither is in scope for any active phase.

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
| (none — pre-PAUL dirty state landed as `f2ff098`; working tree clean) | — | Phase 2 PLAN can proceed against clean HEAD |

## Session Continuity

Last session: 2026-05-21
Stopped at: Phase 2.1 complete; transitioned to Phase 3 (Text Processing Improvements). Phase 2.1 git commit pending.
Next action: `/paul:plan` for Phase 3 (Text Processing Improvements)
Resume file: .paul/ROADMAP.md

---
*STATE.md — Updated after every significant action*
