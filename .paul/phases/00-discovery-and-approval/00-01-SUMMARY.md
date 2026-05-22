---
phase: 00-discovery-and-approval
plan: 01
subsystem: governance
tags: [prd-approval, discovery, decisions, hf-providers, vibevoice-deferral, kokoro, ollama]

requires:
  - phase: none
    provides: MODERNIZATION_PRD.md (drafted v0.1 milestone scope and §14 open questions)
provides:
  - explicit stakeholder approval of MODERNIZATION_PRD.md (bulk: accept-all-defaults)
  - 9 propagated decisions (§14.1 x3 + §14.2 x6) into PRD + PROJECT.md + STATE.md + ROADMAP.md
  - Phase 6.3 (VibeVoice) deferred from v0.1 milestone to v0.2
  - APPROVAL-PACKET.md as durable decision-source-of-truth artifact
affects: [phase-1-architecture-and-configuration, phase-4-gui-reliability-and-ux, phase-6-2-kokoro, phase-6-3-vibevoice-deferred, phase-7-testing-validation-and-docs]

tech-stack:
  added: []
  patterns:
    - "Decision-propagation across 4 surfaces (PRD + PROJECT.md + STATE.md + ROADMAP.md)"
    - "Original PRD text preserved verbatim — decisions are annotations, not overwrites (audit S2)"
    - "Bidirectional traceability — every decision row cites APPROVAL-PACKET.md (audit S1)"
    - "Idempotent propagation guard prevents duplicate Decision lines (audit M2)"

key-files:
  created:
    - .paul/phases/00-discovery-and-approval/00-01-APPROVAL-PACKET.md
    - .paul/phases/00-discovery-and-approval/00-01-AUDIT.md
    - .paul/phases/00-discovery-and-approval/00-01-SUMMARY.md
  modified:
    - MODERNIZATION_PRD.md   (§14.1 [Confirmed YYYY-MM-DD] annotations; §14.2 **Decision (YYYY-MM-DD):** lines)
    - .paul/PROJECT.md        (9 new Key Decisions rows; VibeVoice + multi-speaker added to Out of Scope)
    - .paul/STATE.md          (Decisions table; Blockers cleared)
    - .paul/ROADMAP.md        (Phase 6.3 row → Deferred (v0.2); Phase 6.3 detail section gets deferral note)

key-decisions:
  - "PRD approved via bulk: accept-all-defaults — stakeholder accepted Claude's pre-filled recommended values verbatim"
  - "Phase 6.3 (VibeVoice) deferred from v0.1 milestone to v0.2 — no GPU assumed in v0.1 target machines"
  - "Multi-speaker scripting UX deferred to v0.2 — tied to Phase 6.3 deferral"
  - "VibeVoice research/dev-use license pre-accepted for v0.2 (first-run opt-in + no shipped weights)"
  - "HF cache defaults to ~/.cache/huggingface with HF_HOME env override"
  - "Provider defaults: OpenAI hosted; Kokoro offline"

patterns-established:
  - "Resolution mode tagging (bulk-accept-all-defaults vs bulk-enable-vibevoice vs individually-considered) — future approval cycles must classify the same way"
  - "Decisions propagate via the 4-surface pattern; rationale column always cites APPROVAL-PACKET artifact"

duration: ~30min
started: 2026-05-21T00:30:00Z
completed: 2026-05-21T01:00:00Z
---

# Plan 00-01 — Execution Summary

**MODERNIZATION_PRD.md approved via bulk: accept-all-defaults; 9 §14 decisions propagated across PRD + PROJECT.md + STATE.md + ROADMAP.md; Phase 6.3 (VibeVoice) deferred from v0.1 milestone to v0.2; v0.1 critical path now contains 10 phases (0 thru 7 with sub-phases except 6.3).**

**Plan:** `.paul/phases/00-discovery-and-approval/00-01-PLAN.md`
**Phase:** 0 — Discovery and Approval
**Completed:** 2026-05-21
**Status:** APPLY complete; ready for UNIFY
**Audit verdict (pre-execution):** Conditionally acceptable → 2 must-have + 5 strongly-recommended upgrades applied → approved
**Resolution mode:** **bulk: accept-all-defaults** (audit-added S5)
**Approver:** BuggyButLearning (jcrsantiago@hotmail.com)
**Approval signal:** "prd is approved. start with the paul phases." — received 2026-05-21

---

## 1. Decisions resolved (9 total)

All decisions cite [`00-01-APPROVAL-PACKET.md`](00-01-APPROVAL-PACKET.md) as source of truth.

### §14.1 — Final planning assumptions (3 confirmed)

- **§14.1(a) Ollama behavior** — Confirmed. Query local API, validate capabilities, warn/block unsupported models. (Phase 6 scope.)
- **§14.1(b) OpenAI discovery behavior** — Confirmed. Dynamic listing + allowlist filter to known TTS models. (Phase 2.1 scope.)
- **§14.1(c) Real smoke test budget** — Confirmed. <$1 per run, <5 min total runtime. (Phase 7 scope.)

### §14.2 — HuggingFace provider open questions (6 confirmed, with deferrals)

- **§14.2(1) GPU availability** — Confirmed. No GPU assumed in v0.1 target machines. **Phase 6.3 (VibeVoice) deferred to v0.2.**
- **§14.2(2) VibeVoice license** — Confirmed-with-deferral. Accept research/dev-use license; first-run opt-in dialog mandatory in v0.2; do NOT ship binaries with bundled weights.
- **§14.2(3) Disk budget** — Confirmed. Kokoro ~500 MB in v0.1; VibeVoice ~6 GB applies only when Phase 6.3 enabled (v0.2).
- **§14.2(4) HF cache location** — Confirmed. Default `~/.cache/huggingface`; expose `HF_HOME` env var override. Implementation in Phase 6.2 (Kokoro).
- **§14.2(5) Multi-speaker UX** — Deferred to v0.2 (tied to Phase 6.3 deferral). Ship VibeVoice as single-speaker first if at all.
- **§14.2(6) Default provider** — Confirmed. OpenAI hosted default; Kokoro offline default. Phase 4 GUI default-provider behavior.

## 2. AC results

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | Approval packet produced | ✅ |
| AC-2 | Every open question resolved + resolution mode recorded | ✅ (bulk: accept-all-defaults) |
| AC-3 | Decisions propagated across PRD + PROJECT.md + STATE.md + ROADMAP.md with bidirectional traceability + original text preserved + idempotent | ✅ (6 `**Decision (2026-05-21):**` lines in PRD §14.2; 9 new rows in PROJECT.md Key Decisions) |
| AC-4 | Explicit approval recorded; paul.json untouched (transition workflow's job) | ✅ |
| AC-5 | Rejection / correction / defer branches available on human-verify checkpoint | ✅ (branch taken: approved) |
| AC-6 | No unannotated "Open"/"TBD" tokens in PRD §14 | ✅ (only "Open" match is the section header `### 14.2 Open questions...` — structural, not a status) |

## 3. Files created / modified

**Created:**
- `.paul/phases/00-discovery-and-approval/00-01-APPROVAL-PACKET.md` — durable decision-source-of-truth artifact
- `.paul/phases/00-discovery-and-approval/00-01-AUDIT.md` — enterprise audit report
- `.paul/phases/00-discovery-and-approval/00-01-SUMMARY.md` (this file)

**Modified:**
- `MODERNIZATION_PRD.md` — §14.1 gets `[Confirmed 2026-05-21]` annotations; §14.2 gets `**Decision (2026-05-21):**` lines under each question. Original PRD text preserved verbatim (audit S2).
- `.paul/PROJECT.md` — 9 new Key Decisions rows; "Out of Scope" section gains VibeVoice + multi-speaker entries with deferral reason.
- `.paul/STATE.md` — Decisions table gets the 00-01 application row; Blockers/Concerns table cleared (all 3 prior blockers now resolved).
- `.paul/ROADMAP.md` — Phase 6.3 row marked `Deferred (v0.2)`; Phase 6.3 detail section gains a "[DEFERRED to v0.2 — 2026-05-21]" header and deferral reason.

**Untouched (by design per audit M1):**
- `.paul/paul.json` — phase advancement, milestone status, and timestamp updates are the **transition workflow's** responsibility, not this plan's. The transition workflow will fire when Phase 0's last plan (this one) unifies. Until then paul.json correctly shows `phase.number=0, status=in_progress`.

## 4. What this plan did NOT do (audit M1 hand-off)

The following Phase 0 closure steps are explicitly the responsibility of the **PAUL transition workflow** triggered by `/paul:unify` when this plan closes the last open plan in Phase 0:

1. Advance `paul.json` to `phase.number=1, phase.name="Architecture and Configuration", phase.status="ready_to_plan"`.
2. Mark Phase 0 row in ROADMAP.md as `Complete (2026-05-21)` with Completed date.
3. Move v0.1 milestone status from `Not started` / `In progress` (current) to whatever the transition workflow determines (still in progress after Phase 0 — only one of 11 phases done).
4. Optionally produce a git commit `feat(00-discovery-and-approval): close Phase 0 with PRD approval and characterization tests` (transition workflow may propose).
5. PROJECT.md "Validated (Shipped)" promotion of any newly-validated items.

**This separation is enforced because the transition workflow's purpose is to make these advancements atomic and consistent across all artifacts.** Doing them inside this plan's Task 3 would silently bypass the transition step.

## 5. Net scope impact on v0.1 Modernization MVP

| Phase | Pre-approval scope | Post-approval scope | Net change |
|---|---|---|---|
| 0 — Discovery and Approval | In progress | Complete (pending transition workflow) | Closing |
| 1 — Architecture and Configuration | Not started | Not started — next up | None |
| 2 — TTS Engine Modernization | Not started | Not started | None |
| 2.1 — Model Discovery and Selection | Not started | Not started | None |
| 3 — Text Processing | Not started | Not started | None |
| 4 — GUI Reliability and UX | Not started | Not started; provider-default order locked (OpenAI then Kokoro) per §14.2(6) | Spec sharpened |
| 5 — Audio/Video Cleanup | Not started | Not started | None |
| 6 — Local Provider — Ollama | Not started | Not started | None |
| 6.2 — Local Provider — Kokoro-82M | Not started | Not started; HF cache + `HF_HOME` override locked per §14.2(4) | Spec sharpened |
| **6.3 — Local Provider — VibeVoice-1.5B** | **Not started (v0.1 scope)** | **Deferred (v0.2 milestone)** | **REMOVED from v0.1** |
| 7 — Testing, Validation, and Docs | Not started | Not started; smoke-test budget locked <$1 / <5 min per §14.1(c) | Spec sharpened |

**Critical-path phases for v0.1:** 1 → 2 → 2.1 → 3 → 4 → 5 → 6 → 6.2 → 7. Nine phases excluding Phase 0 (this one) and Phase 6.3 (deferred).

## 6. Deferred items handed off

- **VibeVoice provider integration (Phase 6.3)** — moved to v0.2 milestone. Pre-approved positions on license / disk budget / multi-speaker UX are recorded for v0.2 plan re-use.
- **Multi-speaker scripting UX** — moved to v0.2 with Phase 6.3.

## 7. Outstanding (user-owned) actions from prior plan 00-02

(Carried forward unchanged — not affected by 00-01 closure.)

- Commit + push the `git rm --cached key.txt` index change to GitHub (cosmetic now since key was a placeholder; keeps repo hygiene correct).

## 8. Skill audit

Per `.paul/SPECIAL-FLOWS.md`, no skills were marked **required** for this plan; `/paul:audit` was registered as optional but was auto-invoked per the project's audit-auto-run feedback policy. Skill audit: no gaps to log.

## 9. Next phase readiness

**Ready for Phase 1 (Architecture and Configuration):**
- All §14 decisions locked. Phase 1 plans can reference them without re-litigating.
- v0.1 critical path is well-defined (9 phases including Phase 1 itself).
- Regression net (101 tests, 0.77s) is live from 00-02. Phase 1 refactors will land against it.

**Concerns:**
- None. All Phase 0 blockers are cleared.

**Blockers:**
- None.

---
*Generated by /paul:apply 2026-05-21 from Task 3 of 00-01-PLAN.md. Finalized by /paul:unify same day. Transition workflow will run on UNIFY because this is the last open plan in Phase 0.*
