# Special Flows — Text2AudioBook

Registered skills/commands available during PAUL phases. Invoke via `/skill-name` or Skill tool.

## Implementation flow

| Skill | When to invoke | Phase fit |
|-------|----------------|-----------|
| `/tdd` | Building features or fixing bugs that need red-green-refactor discipline. PRD §10 mandates tests-before-done. | Phases 1, 2, 2.1, 3, 6, 6.2, 6.3, 7 |
| `/run` | Launch the Tkinter app to see a change live (Phase 4 GUI changes, Phase 5 video, Phase 6.x local providers). | Phases 4, 5, 6, 6.2, 6.3 |
| `/verify` | Run the app and confirm a fix actually works — audio output spot-checks, GUI behavior, end-to-end conversion. | All phases after APPLY |
| `/diagnose` | Disciplined debug loop for hard bugs / performance regressions (chunking edge cases, retry/backoff anomalies, GPU OOM on VibeVoice). | Phases 2, 3, 6.3 in particular |
| `/simplify` | Review changed code for reuse, quality, efficiency — keeps diffs lean per project rule "no premature abstraction". | UNIFY phase of every loop |
| `/frontend-design` | Distinctive web-frontend design. **Caveat:** This project's GUI is Tkinter, not web. Skill is registered but not directly applicable unless a future web companion is built. | Out-of-band (future) |

## Review / quality gates

| Skill | When to invoke | Phase fit |
|-------|----------------|-----------|
| `/review` | Review a PR before merge. | Before every release tag |
| `/security-review` | Security review of pending branch changes (look for command injection in shell-out paths, key leakage in logs, model-download integrity). | Before Phase 7 close, before any release |
| `/paul:audit` | Enterprise plan audit. Auto-inserted between PLAN and APPLY per config.md (`enterprise_plan_audit.enabled = true`). | Every plan |

## HITL policy

`config.md → preferences.hitl_mode = ping_only`. The PAUL loop runs autonomously through PLAN → AUDIT → APPLY → UNIFY. User is interrupted **only** when human-in-the-loop input is genuinely required:

- Stakeholder approval gates (PRD approval, phase-exit sign-off)
- License opt-in (VibeVoice research-only acceptance, before first download)
- Real-API smoke test cost gates (OpenAI smoke runs against the <$1 / <5 min budget)
- Subjective audio-quality validation (PRD §10.3, §11.2 human-only items)
- Destructive or irreversible actions (force-push, branch deletes, package downgrades)
- Decisions that change project scope or constraints
- **Blocking audit findings** — if `/paul:audit` reports blocking severity, stop and escalate

**Audit gate auto-run:** Because `enterprise_plan_audit.enabled = true`, `/paul:audit` is invoked automatically after every `/paul:plan` and before `/paul:apply`. Do not ask the user "run audit?" — just run it. Proceed to apply on pass; escalate on blocking fail. (Confirmed by user 2026-05-21.)

Anything else: proceed without prompting. Report results at end of loop.

---
*SPECIAL-FLOWS.md — Updated when skills are added or removed*
*Last updated: 2026-05-21*
