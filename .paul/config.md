# Project Config

**Project:** Text2AudioBook
**Created:** 2026-05-21

## Project Settings

```yaml
project:
  name: Text2AudioBook
  version: 0.0.0
```

## Integrations

### SonarQube

```yaml
sonarqube:
  enabled: false
```

### Enterprise Plan Audit

```yaml
enterprise_plan_audit:
  enabled: true
  mode: autonomous
  notes: |
    Auto-insert /paul:audit between PLAN and APPLY for every plan.
    Execute the full PAUL loop autonomously.
    Only message the user when human-in-the-loop input is required
    (e.g. stakeholder approvals, license opt-ins, real-API smoke test
    cost gates, subjective audio-quality validation).
```

## Preferences

```yaml
preferences:
  auto_commit: false
  verbose_output: false
  hitl_mode: ping_only   # Only interrupt user when HITL input is required
```

---
*Config created: 2026-05-21*
