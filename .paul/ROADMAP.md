# Roadmap: Text2AudioBook

## Overview

Migrate the existing Tkinter-based text-to-audio utility from a raw-HTTP OpenAI TTS integration to a modern, multi-provider architecture (OpenAI + Ollama + Kokoro-82M + VibeVoice-1.5B), with config-driven model selection, robust chunking, retries, bounded concurrency, and a real test suite — while preserving the existing single-window workflow for non-technical users.

## Current Milestone

**v0.1 Modernization MVP** (v0.1.0)
Status: In progress (Phases 0 + 1 + 2 + 2.1 complete; Phase 3 next)
Phases: 4 of 11 complete (4 of 10 active v0.1 phases — Phase 6.3 deferred to v0.2)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work imported from MODERNIZATION_PRD.md §9
- Decimal phases (2.1, 6.2, 6.3): Sub-phases inserted for tightly-coupled scope (model discovery, Kokoro provider, VibeVoice provider)

Phases execute in numeric order.

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 0 | Discovery and Approval | 2 | Complete | 2026-05-21 |
| 1 | Architecture and Configuration | 1 | Complete | 2026-05-21 |
| 2 | TTS Engine Modernization | 1 | Complete | 2026-05-21 |
| 2.1 | Model Discovery and Selection | 1 | Complete | 2026-05-21 |
| 3 | Text Processing Improvements | TBD | Planning | - |
| 4 | GUI Reliability and UX | TBD | Not started | - |
| 5 | Audio/Video Cleanup | TBD | Not started | - |
| 6 | Local Provider — Ollama | TBD | Not started | - |
| 6.2 | Local Provider — Kokoro-82M | TBD | Not started | - |
| 6.3 | Local Provider — VibeVoice-1.5B | TBD | Deferred (v0.2) | - |
| 7 | Testing, Validation, and Docs | TBD | Not started | - |

## Phase Details

### Phase 0: Discovery and Approval

**Goal:** Stakeholder approval of MODERNIZATION_PRD.md and resolution of open questions in §14.
**Depends on:** Nothing (first phase)
**Research:** Unlikely (decisions already drafted)

**Scope:**
- PRD review
- Confirm UI simplicity level, video scope, dependency tolerance, Python version target
- Confirm GPU availability, VibeVoice license acceptance, HF disk budget

### Phase 1: Architecture and Configuration

**Goal:** Settings/config helper module, provider abstraction layer, config precedence (UI > env > file > defaults), `OPENAI_API_KEY` + `key.txt` fallback, voice/preset registry.
**Depends on:** Phase 0 (PRD approved)
**Research:** Unlikely (internal refactor)

### Phase 2: TTS Engine Modernization

**Goal:** Replace raw HTTP TTS calls with official OpenAI SDK; add bounded concurrency, retry/backoff, chunk-level logging.
**Depends on:** Phase 1 (config + provider abstraction in place)
**Research:** Likely (confirm current OpenAI SDK speech API surface and recommended models)
**Research topics:** Latest OpenAI TTS model names and recommended quality-preset mapping.

### Phase 2.1: Model Discovery and Selection

**Goal:** OpenAI model discovery, Ollama local model discovery, `Refresh Models` UI action, curated fallback list.
**Depends on:** Phase 2
**Research:** Unlikely (uses already-modernized SDK)

### Phase 3: Text Processing Improvements

**Goal:** Paragraph-aware chunking, sentence-aware fallback, accurate position metadata, dependency-light.
**Depends on:** Phase 1
**Research:** Unlikely (no new libs needed)

### Phase 4: GUI Reliability and UX

**Goal:** Disable Start while processing, progress/status label, improved validation messages, provider/model dropdowns, `Refresh Models` button — all without redesigning the layout.
**Depends on:** Phase 2 + Phase 2.1
**Research:** Unlikely

### Phase 5: Audio/Video Cleanup

**Goal:** Audit `combine_and_convert.py`, decide MoviePy vs FFmpeg, fix ImageClip/VideoFileClip ambiguity, add helper-logic tests.
**Depends on:** Phase 4
**Research:** Likely (MoviePy vs FFmpeg trade-offs)

### Phase 6: Local Provider — Ollama

**Goal:** Connectivity checks, local invocation path, base URL config, capability/fallback behavior, documented limitations.
**Depends on:** Phase 2 + Phase 2.1
**Research:** Likely (verify which Ollama-served models actually support speech synthesis)
**Research topics:** Whether the local Ollama API exposes any usable TTS path beyond model listing.

### Phase 6.2: Local Provider — Kokoro-82M

**Goal:** Add `kokoro`/`soundfile`/`huggingface_hub` deps, espeak-ng probe with actionable error, `_write_kokoro_speech` helper, pinned model revision, voice/language selection, WAV→MP3 conversion, single-thread default for local concurrency.
**Depends on:** Phase 2 + Phase 2.1
**Research:** Likely (confirm Kokoro pipeline API stability and licensing for redistribution of weight references)
**Research topics:** Kokoro `KPipeline` parameters, espeak-ng install UX on Windows.

### Phase 6.3: Local Provider — VibeVoice-1.5B  **[DEFERRED to v0.2 — 2026-05-21]**

**Goal:** Add `transformers`/`torch`/`accelerate` deps (pinned), license/safety opt-in dialog, GPU detection, `_write_vibevoice_speech` helper, multi-speaker scoping, preservation of upstream watermark + audible disclaimer.
**Depends on:** Phase 6.2 (Kokoro pattern established)
**Research:** Likely (confirm upstream pyproject.toml deps, verify inference-logging behavior, confirm no required network calls at inference time)
**Research topics:** Exact torch/CUDA pin from upstream; whether "inference request logging" applies to local invocation.
**Deferral reason:** §14.2(1) decision 2026-05-21 — no GPU assumed in v0.1 target machines. Phase 6.3 moves to v0.2 milestone. Multi-speaker scripting UX (§14.2(5)) also defers with this phase. License position and disk budget are pre-approved; v0.2 plan can re-use without re-relitigating.

### Phase 7: Testing, Validation, and Docs

**Goal:** Unit + mocked integration test suites, real OpenAI smoke test (<$1, <5 min), human validation checklist, README/setup docs (incl. espeak-ng + HF cache + VibeVoice license note), release validation summary.
**Depends on:** All prior phases (each phase should add its own tests as it lands; Phase 7 closes any gaps)
**Research:** Unlikely

---
*Roadmap created: 2026-05-21*
*Last updated: 2026-05-21 (Phase 2.1 complete)*
