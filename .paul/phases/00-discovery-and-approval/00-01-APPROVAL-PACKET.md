# MODERNIZATION_PRD.md — Approval Packet

**Date:** 2026-05-21
**Plan:** Phase 0 · 00-01 (PRD approval gate)
**Reviewer / approver:** BuggyButLearning (jcrsantiago@hotmail.com)
**Resolution mode:** **bulk: accept-all-defaults** (per audit S5; stakeholder accepted Claude's pre-filled recommended values verbatim with the message "prd is approved. start with the paul phases.")

---

## 1. PRD at a glance

Text2AudioBook modernization migrates a Tkinter desktop utility from a raw-HTTP OpenAI TTS integration to a multi-provider architecture (OpenAI hosted + Ollama / Kokoro-82M / VibeVoice-1.5B local), with config-driven model selection, paragraph/sentence-aware chunking, retries with bounded concurrency, structured tests, and minimal UX disruption. Kokoro is the recommended local default (Apache 2.0, CPU-capable); VibeVoice is opt-in and GPU-only and carries an upstream research/dev-use license that must be surfaced to the user. The video sub-pipeline stays in scope but isolated. Eleven phases, sidecar tests live, single-developer cadence.

## 2. §14.1 — Final planning assumptions (pre-approval text)

The three assumptions below are quoted verbatim from PRD §14.1.

1. **Ollama behavior:** the app should query the local Ollama API and show local models as available options. The implementation should still validate capabilities and warn or block when a selected local model cannot support the required generation flow.
2. **OpenAI discovery behavior:** the app should dynamically retrieve current model options where technically feasible. Because dynamic listings can be broad, the implementation should apply validation rules so only valid/current models relevant to the app are shown or are clearly labeled.
3. **Real smoke test budget/time cap:** default target should be under $1 per validation run and under 5 minutes total runtime. Smoke tests should use tiny sample inputs and minimize generated audio length.

## 3. §14.2 — Open questions (HF providers) — pre-approval text

The six questions below are quoted verbatim from PRD §14.2.

1. **GPU availability:** does the target machine have a CUDA-capable GPU with sufficient VRAM for VibeVoice-1.5B (BF16, ~3B param)? If no, Phase 6C is skipped or deferred.
2. **VibeVoice license acceptance:** stakeholder confirmation that the upstream "research and development only" guidance is acceptable for this project's distribution model, OR explicit decision to keep VibeVoice out of scope.
3. **Disk budget:** ~6 GB for VibeVoice weights + a few hundred MB for Kokoro. Confirm acceptable cache footprint.
4. **HF cache location:** default to standard HF cache (`~/.cache/huggingface`) or project-local cache directory?
5. **Multi-speaker UX:** for VibeVoice, do we expose multi-speaker scripting (e.g. `[S1] line / [S2] line`) in v1, or default to single-speaker mode?
6. **Provider default:** with four providers available, confirm the recommended default remains OpenAI for hosted-mode users and Kokoro for offline-mode users.

## 4. Risk reminders (PRD §12, high-impact only)

- VibeVoice upstream license restricts to research/dev use — must surface to user via opt-in dialog before any download. Cannot ship binaries that bundle weights.
- VibeVoice ~6 GB BF16 model + CUDA-capable GPU requirement filters out most casual users. Keep Kokoro as the recommended local default.
- Kokoro requires external `espeak-ng` system dep (manual `.msi` install on Windows). Detect missing dep at startup; show actionable install link.

## 5. Decision matrix

| # | Question | Recommended default | Decision (2026-05-21) | Notes |
|---|---|---|---|---|
| 14.1(a) | Ollama behavior | Query local API, validate capabilities, warn/block unsupported models | **Confirmed** | Matches PRD §FR-1A, §6.2 Phase 6 scope |
| 14.1(b) | OpenAI discovery behavior | Dynamic listing with allowlist filter to known TTS models | **Confirmed** | Matches PRD §FR-3A, §7.2A |
| 14.1(c) | Real smoke test budget | <$1 per run, <5 min total | **Confirmed** | Drives Phase 7 test design |
| 14.2(1) | GPU availability for VibeVoice | **No GPU assumed; Phase 6.3 (VibeVoice) deferred to v0.2 unless GPU confirmed** | **Confirmed (Deferred to v0.2)** | Defers Phase 6.3 from the v0.1 milestone; Phase 6 (Ollama) + 6.2 (Kokoro) remain in v0.1 |
| 14.2(2) | VibeVoice license acceptance | Accept research/dev use; require first-run opt-in dialog; do not ship binaries that include weights | **Confirmed (with deferral)** | Decision is moot for v0.1 because Phase 6.3 is deferred. Recorded so v0.2 can re-use the position. |
| 14.2(3) | Disk budget | Accept ~6 GB for VibeVoice (only if Phase 6.3 enabled); Kokoro ~500 MB always OK | **Confirmed** | Only Kokoro footprint applies to v0.1 |
| 14.2(4) | HF cache location | Default standard `~/.cache/huggingface`; expose `HF_HOME` env var override | **Confirmed** | Implementation in Phase 6.2 |
| 14.2(5) | Multi-speaker UX | Defer multi-speaker to v0.2; ship VibeVoice as single-speaker first if at all | **Confirmed** | Moot for v0.1; locks the v0.2 default |
| 14.2(6) | Default provider | OpenAI for hosted; Kokoro for offline. Matches PRD §15 | **Confirmed** | Drives Phase 4 (GUI default-provider behavior) |

## 6. Sign-off

```
Approved by:    BuggyButLearning (jcrsantiago@hotmail.com)
Date:           2026-05-21
Signal:         "prd is approved. start with the paul phases."  →  interpreted as approved + bulk-accept-all-defaults
Resolution mode: bulk: accept-all-defaults (audit S5)
```

---

## 7. Net scope impact for v0.1 Modernization MVP

| Phase | Original v0.1 scope | After approval | Reason |
|---|---|---|---|
| 6.3 (VibeVoice) | In scope | **Deferred to v0.2** | §14.2(1) — no GPU assumed in target machines |
| 6 (Ollama) | In scope | In scope | §14.1(a) confirmed |
| 6.2 (Kokoro) | In scope | In scope | §14.2(3) Kokoro footprint OK; §14.2(4) cache loc confirmed |
| 4 (GUI) | In scope | In scope, provider default order = OpenAI then Kokoro | §14.2(6) |
| 7 (Testing) | In scope | In scope, smoke-test budget locked at <$1 / <5 min | §14.1(c) |

VibeVoice work product produced so far (PRD provider descriptions, Phase 6.3 in ROADMAP, etc.) remains in the repo for v0.2 readiness but is removed from the v0.1 critical path.

---
*Generated by /paul:apply 2026-05-21 from Task 1 of 00-01-PLAN.md.*
