# Text2AudioBook Modernization PRD

## 1. Document Status
- **Project:** Text2AudioBook
- **Document Type:** Product Requirements Document (PRD)
- **Status:** Draft for stakeholder review
- **Author:** Cline
- **Last Updated:** 2026-05-21
- **Implementation Status:** Planning only; no production code changes approved yet

## 2. Executive Summary
Text2AudioBook is a small desktop utility that converts text files into speech using OpenAI text-to-speech, then optionally combines MP3s into a video. The current codebase is functional but dated in several important areas: it uses a legacy-style raw HTTP integration for TTS, hardcoded voice/model defaults, simplistic text chunking, weak resilience for retries/rate limits, and a brittle audio/video pipeline.

This PRD proposes a modernization pass that keeps the project intentionally simple while upgrading it to current best practices. The plan focuses on:
- migrating to the official OpenAI Python SDK
- adding provider abstraction so OpenAI remains the primary hosted option and several local providers (Ollama, Kokoro, VibeVoice) become optional
- making model selection config-driven rather than hardcoded
- improving chunking and reliability without adding heavy dependencies
- adding automated tests so features can be validated safely
- keeping the GUI and general workflow familiar to existing users, with only small targeted UX improvements

Two HuggingFace TTS engines are added as opt-in local providers:
- **Kokoro-82M** (`hexgrad/Kokoro-82M`, Apache 2.0): 82M-param StyleTTS 2 model, CPU-capable, 8 languages, 54 voices, 24 kHz WAV output. Lightweight, permissive license, good fit for single-narrator audiobook flow.
- **VibeVoice-1.5B** (`microsoft/VibeVoice-1.5B`, MIT weights but **research/development use only** per upstream guidance): multi-speaker (up to 4), long-form (up to 90 min), English/Chinese, ~3B params BF16, GPU required. Suited to multi-character dialogue and podcast-style output. Includes upstream-baked AI watermark and audible disclaimer that must not be stripped.

This document is designed to be approved before any code changes are made.

---

## 3. Product Goals

### 3.1 Primary Goals
1. Modernize the TTS integration to use current OpenAI client patterns.
2. Make model and voice upgrades easy without changing core code each time.
3. Improve output quality and reliability without overcomplicating the project.
4. Add optional local model support via Ollama where feasible.
5. Add optional HuggingFace local providers: Kokoro-82M for lightweight narration and VibeVoice-1.5B for multi-speaker long-form audio.
6. Add meaningful automated testing coverage for key logic.
7. Preserve the project's small size and approachable structure.

### 3.2 Non-Goals
The following are **not** in scope for this modernization unless approved later:
- turning the project into a web app or SaaS
- adding a database
- adding user accounts, authentication, or cloud sync
- building a plugin architecture
- adding advanced NLP dependencies unless clearly justified
- redesigning the UI into a new framework

---

## 4. Current State Assessment

### 4.1 Strengths
- Small, understandable Python codebase
- Minimal user workflow
- Useful core utility for text-to-audio conversion
- Existing GUI reduces adoption friction for non-technical users

### 4.2 Key Problems / Outdated Areas

#### A. TTS integration is outdated
- Uses `requests.post()` directly against `/v1/audio/speech`
- Hardcodes model `tts-1`
- Makes future model changes require code edits
- Has no provider abstraction, making future local or alternate-provider support awkward

#### B. Configuration is brittle
- API key is read from `key.txt` at import time
- Voices are hardcoded in the GUI
- No clean separation between defaults and runtime selection
- No discovery mechanism for available provider models/voices

#### C. Chunking quality is basic
- Current punctuation-based chunking is naive
- Can split awkwardly around abbreviations, dialogue, or long paragraphs
- Logged “starting sentence” metadata is simplistic

#### D. Reliability is limited
- Thread pool concurrency is unbounded by explicit design
- No retry/backoff behavior for transient API failures or rate limits
- Failure reporting is minimal

#### E. Video pipeline is fragile
- `combine_and_convert.py` mixes `ImageClip` and `VideoFileClip` in a way that appears error-prone
- Current approach may be heavier than necessary for static-image videos
- Dependency footprint is larger than needed

#### F. Test coverage is absent
- No unit tests
- No integration test strategy
- No documented validation checklist for human-only verification

---

## 5. Users and Use Cases

### 5.1 Primary Users
- Individual creators converting text into audiobook-style audio
- Users who prefer a desktop GUI over code/scripts
- Small-scale content producers who want a simple OpenAI TTS workflow

### 5.2 Primary Use Cases
1. Select a text file and generate a high-quality MP3 audiobook.
2. Choose voice and quality mode without dealing with technical model names.
3. Process larger documents safely through chunking.
4. Optionally combine generated MP3 chunks into a single MP3 and/or simple video.
5. Switch between hosted OpenAI TTS and local Ollama-backed generation where supported.

---

## 6. Product Requirements

### 6.1 Functional Requirements

#### FR-1: Modern OpenAI TTS integration
- The app shall use the official OpenAI Python SDK for TTS requests.
- The app shall support configurable model selection.
- The app shall preserve the current text-to-MP3 workflow.

#### FR-1A: Multi-provider architecture
- The app shall support more than one TTS provider without requiring GUI rewrites.
- OpenAI shall be the default hosted provider.
- Ollama-backed local support shall be included as an optional provider path.
- Kokoro-82M (HuggingFace, Apache 2.0) shall be included as an optional local provider for lightweight narration.
- VibeVoice-1.5B (HuggingFace, MIT weights, upstream-restricted to research/dev use) shall be included as an optional local provider for multi-speaker long-form output.
- Provider-specific capabilities (max speakers, supported languages, output sample rate/format, GPU requirement) shall be surfaced cleanly and used to gate UI options.

#### FR-1B: HuggingFace model handling
- HuggingFace local providers shall download model weights via `huggingface_hub` with pinned revisions/commit hashes to prevent silent model swaps.
- The app shall cache models to a configurable directory (defaulting to the standard HF cache).
- The app shall verify required system dependencies (`espeak-ng` for Kokoro) on first use of the relevant provider and produce a clear actionable error if missing.
- The app shall not strip, alter, or disable upstream-baked safety artifacts (e.g. VibeVoice's audible AI disclaimer or imperceptible watermark).
- The app shall expose VibeVoice's research/development-only license guidance to the user before first use and require explicit opt-in.
- The app shall convert provider-native output (Kokoro: WAV 24 kHz) into the project's standard MP3 output via the existing pydub path.

#### FR-2: Backward-compatible credential loading
- The app shall first check `OPENAI_API_KEY` from the environment.
- The app shall support `key.txt` only as a fallback/backup option.
- The app shall surface clear errors when no API key is available.

#### FR-3: Simpler modern settings
- The app shall support a simple quality preset strategy.
- The app shall also support direct model selection for users who want control.
- The app shall allow voice selection from a maintained supported list.
- The app may optionally expose speed if it does not complicate the UI.

#### FR-3A: Model and voice discovery
- The app shall support refreshing available models from providers where technically feasible.
- The app shall cache or fall back to a curated supported list when live discovery is unavailable or unreliable.
- The app shall support local model discovery for Ollama via its local API.

#### FR-4: Better chunking
- The app shall split large inputs safely while preferring paragraph and sentence boundaries.
- The app shall avoid forced hard cuts unless no clean split exists.
- The app shall preserve chunk ordering metadata.

#### FR-5: Reliability controls
- The app shall use bounded concurrency for API calls.
- The app shall retry transient failures with backoff.
- The app shall log chunk-level success/failure information.

#### FR-6: Output handling
- The app shall still produce a final merged MP3.
- The app shall still save chunk position metadata.
- The app shall sanitize or validate output file names.

#### FR-7: Optional video pipeline cleanup
- The project shall either simplify static-image video generation or clearly isolate it as a secondary feature.
- This shall not block the core text-to-audio modernization.

### 6.2 Non-Functional Requirements
- Keep runtime dependencies lightweight.
- Keep modules small and understandable.
- Prefer deterministic, testable functions.
- Maintain Windows-first usability while avoiding OS-specific breakage where possible.
- Avoid hidden magic; use configuration defaults instead of sprawling settings.

---

## 7. Proposed Product Direction

### 7.1 Recommended UX Direction
Keep the current Tkinter desktop UI, but modernize the behavior under the hood.

Recommended user-facing simplification:
- **Quality Preset:** `Best Quality`, `Balanced`, `Fast` (applies to OpenAI; non-OpenAI providers ignore the preset and use direct model/voice selection)
- **Provider Dropdown:** `OpenAI` / `Ollama (Local)` / `Kokoro (Local)` / `VibeVoice (Local)`
- **Model Dropdown:** manually selectable, populated from provider discovery when available
- **Voice Dropdown:** supported voices only, filtered by provider (Kokoro: 54 voices across 8 languages; VibeVoice: speaker-slot mapping for up to 4 speakers)
- **Optional Advanced Settings:** collapsed or deferred unless needed
- **First-use notice:** selecting VibeVoice shows a one-time dialog summarising the research/dev-only license and the upstream safety features (watermark + audible disclaimer) before any download starts

Rationale:
- avoids overwhelming users with model names
- allows model upgrades later without changing the UI contract
- preserves simplicity while still feeling modern

### 7.1A Approved small UX improvements
The stakeholder approved small UX improvements while keeping the UI nearly identical. Recommended low-risk improvements are:
- disable the Start button while processing
- add a small status/progress label (for example: `Reading file`, `Chunk 3/12`, `Merging audio`, `Creating video`)
- add provider and model dropdowns without redesigning the layout
- add a `Refresh Models` button so the latest available models can be fetched where supported
- improve validation messages for missing API key, invalid paths, and unsupported local provider state
- preserve the existing single-window flow and overall field order as much as possible

### 7.2 Recommended Model Strategy
Do **not** hardcode a forever-model into the architecture.

Instead:
- define a default recommended model in config/constants
- allow a fallback model
- map UI presets to model settings internally

Example strategy:
- `Best Quality` → latest recommended high-quality speech model
- `Balanced` → stable general-use model
- `Fast` → lower-latency or lower-cost option

Final exact model names should be confirmed against current OpenAI docs during implementation.

### 7.2A Auto-pulling latest models
The stakeholder requested support for pulling the latest model names where possible.

Recommended approach:
- **OpenAI:** attempt provider-backed model discovery if the SDK/API exposes suitable listing capabilities for the intended TTS endpoint; otherwise use a maintained allowlist curated in config and updated during releases
- **Ollama:** query the local Ollama API to list installed local models
- **UI behavior:** provide a `Refresh Models` action and store the last successful result for the current session

Important note: model listing and model usability are not always the same thing. Even if a provider returns a large model list, the app should still filter to models known or configured to support the project’s use case.

### 7.3 Recommended Configuration Strategy
Minimal config hierarchy:
1. explicit UI choices
2. environment variables
3. local config file defaults
4. code defaults as last resort

Suggested configurable items:
- provider
- API key source
- default voice
- default quality preset
- optional explicit model override
- default output directory
- max concurrency
- local Ollama base URL

---

## 8. Scope by Release

### 8.1 Phase 1 — Core Modernization (Must Have)
- official OpenAI SDK integration
- provider abstraction layer
- config-driven model selection
- env var API key with `key.txt` fallback
- bounded concurrency
- retry/backoff for transient failures
- improved logging

### 8.2 Phase 2 — Output Quality and UX (Should Have)
- improved text chunking
- optional speed control if supported and simple
- provider/model refresh UX
- GUI progress state / disable button during work
- clearer user-facing error messages

### 8.3 Phase 3 — Video / Packaging Cleanup (Could Have)
- refactor or simplify `combine_and_convert.py`
- reduce unnecessary dependency complexity
- improve README/setup docs

### 8.4 Phase 4 — Local Provider Support (Must Have per stakeholder)
- Ollama integration for local model discovery and invocation, if the selected local model/provider path can support the desired workflow
- local provider setup checks and user guidance
- provider-specific validation and fallback behavior

### 8.5 Phase 4B — Kokoro-82M Local Provider (Should Have)
- HuggingFace download/caching via `huggingface_hub` with pinned revision
- espeak-ng presence check with actionable install guidance (Windows .msi link, Linux apt hint)
- Kokoro `KPipeline` invocation per chunk
- WAV→MP3 conversion via pydub to keep pipeline output uniform
- voice/language dropdown population from Kokoro's supported list

### 8.6 Phase 4C — VibeVoice-1.5B Local Provider (Could Have, gated on GPU)
- license/safety opt-in dialog on first selection
- HuggingFace download/caching via `huggingface_hub` with pinned revision (~6 GB BF16)
- GPU availability detection; clear failure if no compatible GPU
- multi-speaker input support (script with speaker tags) — design or defer
- preservation of upstream watermark and audible AI disclaimer in output

---

## 9. Detailed Phase Tracker

## Phase 0 — Discovery and Approval
- [ ] Confirm PRD approval from stakeholder
- [ ] Confirm preferred simplicity level for UI changes
- [ ] Confirm whether video generation remains in active scope or is secondary
- [ ] Confirm acceptable dependency changes
- [ ] Confirm baseline Python version target

### Exit Criteria
- PRD approved
- open product questions answered or accepted as assumptions

## Phase 1 — Architecture and Configuration
- [ ] Add a settings/config helper module or equivalent lightweight utility
- [ ] Add a provider abstraction layer for OpenAI and Ollama
- [ ] Define config precedence: UI > env > config file > defaults
- [ ] Add support for `OPENAI_API_KEY` with `key.txt` fallback
- [ ] Define supported voice list in one place
- [ ] Define quality preset mapping in one place
- [ ] Move model defaults out of hardcoded request payloads
- [ ] Define provider-specific capabilities and model filtering rules

### Exit Criteria
- configuration behavior documented and testable
- model and voice defaults no longer buried in GUI/business logic

## Phase 2 — TTS Engine Modernization
- [ ] Replace raw HTTP TTS calls with official OpenAI SDK calls
- [ ] Add bounded concurrency
- [ ] Add retry/backoff for transient request failures
- [ ] Add chunk-level logging and error reporting
- [ ] Ensure file outputs remain deterministic and ordered

### Exit Criteria
- TTS pipeline works with current SDK
- failure handling is predictable
- ordering and output naming remain stable

## Phase 2A — Model Discovery and Selection
- [ ] Add model discovery for OpenAI where feasible and safe
- [ ] Add local model discovery for Ollama
- [ ] Add `Refresh Models` UI action
- [ ] Add fallback curated model list when live discovery fails
- [ ] Validate that only usable models are exposed for each provider path

### Exit Criteria
- model selection is reliable even when discovery partially fails
- users can choose either presets or explicit models

## Phase 3 — Text Processing Improvements
- [ ] Refactor chunking to prefer paragraph boundaries
- [ ] Add sentence-aware fallback splitting
- [ ] Preserve chunk position metadata accurately
- [ ] Improve logged sentence preview behavior
- [ ] Keep implementation dependency-light

### Exit Criteria
- chunking is measurably cleaner on realistic text
- edge cases are covered by unit tests

## Phase 4 — GUI Reliability and UX
- [ ] Disable start button while processing
- [ ] Add visible progress/status updates
- [ ] Improve path and filename validation
- [ ] Improve missing-key and API-failure messaging
- [ ] Keep UI changes minimal and understandable

### Exit Criteria
- GUI behavior is clearer during processing
- preventable user errors are surfaced early

## Phase 5 — Audio/Video Cleanup
- [ ] Audit `combine_and_convert.py` behavior
- [ ] Keep MP3-to-video in active scope as approved by stakeholder
- [ ] Decide whether to keep MoviePy or replace parts with FFmpeg calls
- [ ] Fix image/video handling ambiguity
- [ ] Add tests around non-GUI helper logic where feasible
- [ ] Update documentation for video generation usage

### Exit Criteria
- optional video feature is reliable or explicitly deprioritized

## Phase 6 — Local Provider Support
- [ ] Add Ollama connectivity checks
- [ ] Add local provider invocation path
- [ ] Add provider-specific settings such as base URL / model listing
- [ ] Define fallback behavior when a selected local model is unavailable
- [ ] Document limitations of local model quality/capability compared with hosted TTS

### Exit Criteria
- local provider path can be selected and validated
- unsupported local configurations fail clearly and safely

## Phase 6B — Kokoro-82M Local Provider
- [ ] Add `kokoro>=0.9.4`, `soundfile`, `huggingface_hub` to project dependencies
- [ ] Document espeak-ng install steps (Windows .msi, Linux apt) in README
- [ ] Add startup espeak-ng probe with actionable error message on miss
- [ ] Implement `_write_kokoro_speech` helper in tts_conversion.py
- [ ] Pin Kokoro model revision in settings.py
- [ ] Add Kokoro voice list (54 voices across 8 langs) to supported-voices config
- [ ] Add WAV→MP3 conversion step (pydub) for Kokoro chunks
- [ ] Default `max_concurrency` to 1 for local providers (GPU/CPU memory-bound)
- [ ] Unit tests covering provider dispatch, voice validation, WAV→MP3 conversion

### Exit Criteria
- Kokoro can be selected, downloaded once, and used to produce MP3 chunks
- espeak-ng absence is detected and surfaced before any chunk fails

## Phase 6C — VibeVoice-1.5B Local Provider
- [ ] Add `transformers`, `torch`, `accelerate`, `huggingface_hub` to project dependencies (pin versions from upstream `pyproject.toml`)
- [ ] Confirm whether upstream's "inference request logging" applies to local invocation; document findings
- [ ] Implement first-use license/safety opt-in dialog
- [ ] Implement `_write_vibevoice_speech` helper in tts_conversion.py
- [ ] Pin VibeVoice model revision in settings.py
- [ ] Implement GPU detection and clear failure mode when unavailable
- [ ] Design multi-speaker input format OR scope to single-speaker for v1
- [ ] Verify upstream watermark and audible disclaimer remain in output (do not strip)
- [ ] Unit tests covering provider dispatch, GPU detection, opt-in gating

### Exit Criteria
- VibeVoice selectable only after explicit opt-in
- runs end-to-end on a GPU-equipped machine; fails clearly on non-GPU
- output retains upstream safety artifacts

## Phase 7 — Testing, Validation, and Docs
- [ ] Add automated unit test suite
- [ ] Add focused integration tests with mocks/stubs
- [ ] Add real API smoke tests for approved hosted-provider scenarios
- [ ] Document human-only validation checklist
- [ ] Update README and setup instructions
- [ ] Produce release validation summary

### Exit Criteria
- automated tests pass locally
- manual validation checklist completed for non-automatable areas

---

## 10. Testing Strategy

## 10.0 Testing is Mandatory and Tracked
Testing is not optional in this modernization effort. Every implementation phase must include explicit test work, test evidence, and a pass/fail status before the phase can be considered complete.

Required enforcement rules:
- no feature is considered complete until its required tests are implemented and run
- no phase may be marked complete unless its testing exit criteria are satisfied
- any bug found during testing must either be fixed in the same phase or explicitly logged as a deferred issue with approval
- real smoke tests must be tracked separately from mocked/integration tests
- human validation items must be recorded as pending until explicitly confirmed by the stakeholder

### 10.0A Required test tracking artifacts
Implementation must maintain the following test tracking artifacts:
- a **test matrix** mapping each feature to unit, integration, smoke, and manual validation coverage
- a **phase validation checklist** showing pass/fail status for each phase
- a **defect log** for failed tests, regressions, and deferred issues
- a **release validation summary** documenting what was tested, what passed, what was skipped, and why

### 10.0B Required status values
Each tracked test item should use one of these statuses:
- `Not Started`
- `In Progress`
- `Passed`
- `Failed`
- `Blocked`
- `Deferred (Approved)`

### 10.0C Gating policy
- A feature cannot move to `Done` without required automated test coverage.
- A phase cannot move to `Done` while any required test item is `Failed` or `Blocked` unless the stakeholder explicitly approves an exception.
- Release readiness cannot be declared until required smoke tests pass and all human validation items are either completed or explicitly waived.

## 10.1 Testing Principles
The project currently has no tests. This modernization will add a pragmatic test strategy that validates core behavior without introducing excessive infrastructure.

Principles:
- maximize coverage of deterministic logic with unit tests
- isolate API dependencies via mocks
- reserve human validation only for areas automation cannot reliably judge
- avoid expensive or flaky test design

## 10.2 Test Pyramid

### A. Unit Tests (highest priority)
Unit tests should cover:

#### Text Processing
- reading text file success/failure
- chunking under max length
- chunking over max length
- paragraph-aware splitting
- sentence-aware fallback splitting
- forced split fallback when no punctuation exists
- position metadata correctness
- sentence preview metadata correctness

#### Config / Settings
- env var API key loading
- fallback to `key.txt`
- error when both are missing
- config precedence behavior
- default quality preset selection
- provider selection and capability gating
- model discovery fallback logic

#### TTS Helper Logic
- request payload/model selection mapping
- output filename generation
- retry decision logic
- chunk ordering preservation
- bounded concurrency configuration
- provider-specific invocation path selection

#### Audio Utilities
- concatenation order behavior
- empty list handling
- invalid path handling where feasible

#### Video Helper Logic
- only for pure helper functions that can be isolated cleanly
- do not attempt heavy multimedia integration in basic unit tests

#### Local Provider Logic
- Ollama availability detection
- local model list parsing
- provider fallback and unsupported-capability behavior

### B. Integration Tests
Integration tests should remain lightweight and mostly mocked.

Recommended integration coverage:
- text file → chunk generation → mocked TTS outputs → merged MP3 path creation
- GUI-adjacent logic extracted into testable helper functions where possible
- config loading + TTS selection flow
- provider switching between OpenAI and Ollama using mocks/stubs

### C. End-to-End / Smoke Tests
These should be limited and carefully scoped.

Recommended smoke tests:
- run conversion on a very small sample input using mocked API responses
- verify chunk files and final output file creation
- run a real OpenAI smoke test with a tiny approved sample because the stakeholder explicitly requested real validation
- optionally run an Ollama smoke test if a compatible local model is installed and available

## 10.3 Human-Only Validation Checklist
The human should only be asked to validate what cannot be reliably judged through automation.

Human validation required for:
- subjective voice quality preference
- whether the generated speech sounds natural enough for target use
- whether selected default voices feel appropriate
- real-cost tolerance for chosen model/preset
- full GUI usability preferences
- optional GPU/FFmpeg/video behavior on the user’s machine
- whether local Ollama output quality is acceptable relative to the hosted provider

### Manual Validation Sections
1. **Voice Quality Review**
   - Listen to sample output across selected voices
   - Confirm preferred default voice

2. **Model / Preset Review**
   - Compare `Best Quality` vs `Balanced` vs `Fast`
   - Confirm chosen defaults meet budget and speed expectations

3. **Desktop UX Review**
   - Validate field labels are understandable
   - Confirm progress messaging is clear
   - Confirm startup flow is acceptable for non-technical users

4. **Optional Video Validation**
   - Confirm output plays correctly on target system
   - Confirm video/image behavior is acceptable

## 10.4 Suggested Test Tooling
- `pytest` for test runner
- `unittest.mock` or `pytest-mock` for mocking
- temporary file fixtures for filesystem tests
- avoid real network calls in default automated tests

## 10.5 Definition of Test Completion
Testing is considered complete when:
- all unit tests pass locally
- mocked integration tests pass locally
- required smoke tests pass locally or are explicitly approved as deferred
- the test matrix is up to date for all in-scope features
- the defect log is updated for all failures encountered during validation
- documentation for manual validation is written
- stakeholder completes human-only validation checklist items relevant to approved scope

## 10.6 Required Test Matrix

The implementation must maintain a feature-to-test mapping similar to the following.

| Feature / Area | Unit Tests | Integration Tests | Real Smoke Test | Human Validation | Status |
|---|---|---|---|---|---|
| Config loading and precedence | Required | Optional | No | No | Not Started |
| API key env var + key.txt fallback | Required | Required | No | No | Not Started |
| OpenAI SDK TTS flow | Required | Required | Required | Optional listening check | Not Started |
| OpenAI model discovery | Required | Required | Optional | No | Not Started |
| Ollama local model discovery | Required | Required | Optional | No | Not Started |
| Ollama generation path | Required | Required | Optional/Required if supported locally | Yes, quality review | Not Started |
| Kokoro download and revision pinning | Required | Required | Optional | No | Not Started |
| Kokoro espeak-ng probe and error path | Required | Optional | No | No | Not Started |
| Kokoro generation path + WAV→MP3 | Required | Required | Required (small sample) | Yes, quality review | Not Started |
| VibeVoice license opt-in gate | Required | Optional | No | Yes, consent flow review | Not Started |
| VibeVoice download and revision pinning | Required | Required | Optional | No | Not Started |
| VibeVoice GPU detection and failure mode | Required | Required | No | No | Not Started |
| VibeVoice generation path (preserves watermark) | Required | Required | Required (small sample, GPU-equipped) | Yes, quality + safety review | Not Started |
| Text chunking logic | Required | Optional | No | Optional output quality spot check | Not Started |
| Audio concatenation | Required | Required | Optional | Optional | Not Started |
| MP3-to-video pipeline | Required where practical | Required | Optional | Yes | Not Started |
| GUI progress and validation states | Required for helper logic | Optional | Optional | Yes | Not Started |
| Error handling / retry behavior | Required | Required | Optional | No | Not Started |

## 10.7 Required Defect Log Format
Each failed or blocked test must be captured in a defect log with at least:
- defect ID
- phase
- feature area
- failing test name
- date found
- severity
- current status
- disposition (`fix now`, `defer`, `won't fix`)
- stakeholder approval status if deferred

## 10.8 Phase Validation Tracker
Each phase must include a validation block during implementation:

### Validation Block Template
- **Phase:**
- **Implemented Items:**
- **Unit Tests:** Passed / Failed / Blocked
- **Integration Tests:** Passed / Failed / Blocked
- **Smoke Tests:** Passed / Failed / Blocked / N/A
- **Human Validation Needed:** Yes / No
- **Defects Open:**
- **Approved to Exit Phase:** Yes / No

No phase should be closed without completing this validation block.

---

## 11. Full Validation Plan

This section defines what the implementation agent should test directly versus what should be escalated to the human.

### 11.1 Validation the implementation agent can do
- static review of module boundaries
- run unit tests locally
- run mocked integration tests locally
- run real hosted-provider smoke tests with approved small input and credentials/environment setup
- validate config precedence behavior
- validate chunking behavior across sample inputs
- validate error handling for missing files / missing keys / mocked API failures
- verify output files are created in test environments
- verify deterministic ordering of chunks and merged outputs

### 11.2 Validation requiring the human
- live API billing/cost acceptability
- subjective speech quality and voice preference
- whether latency is acceptable in real-world use
- GUI polish preferences
- machine-specific FFmpeg/GPU behavior
- final acceptance of default presets and defaults

### 11.3 Acceptance Gate Before Release
Before release, require:
- automated tests green
- core text-to-audio workflow manually spot-checked by human
- at least one real audio sample approved by human
- documentation reviewed for setup accuracy

---

## 12. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| OpenAI model names or SDK APIs evolve | Medium | Keep model selection config-driven and isolate SDK usage |
| Live model discovery returns unusable or overly broad results | Medium | Filter discovered models through provider-specific allowlists/capability rules |
| Too many UI settings complicate the app | High | Use quality presets and keep advanced options optional or deferred |
| Rate limits or transient failures break multi-chunk conversion | High | Add retries, bounded concurrency, and chunk-level reporting |
| Chunking changes cause regressions | Medium | Add sample-based unit tests and preserve deterministic behavior |
| Video pipeline remains brittle | Medium | Make it a secondary scope item and simplify if retained |
| Local Ollama models may not provide TTS-quality output or compatible interfaces | High | Treat provider capabilities explicitly, document limitations, and fail clearly when unsupported |
| VibeVoice upstream restricts to research/dev use; commercial fit unclear | High | Surface license/intent dialog before first use; require explicit opt-in; document limitation in README |
| VibeVoice model is ~6 GB and requires GPU; many users will lack capability | Medium | GPU detection up front; clear failure path; keep Kokoro as the recommended local default |
| Kokoro requires external `espeak-ng` system dep (manual install on Windows) | Medium | Detect missing dep at startup of the provider path; show actionable install link |
| HF model revisions could drift between project versions | Medium | Pin commit hash/revision in settings.py; fail loudly on mismatch |
| Stripping or muting upstream safety artifacts (watermark, AI disclaimer) | High | Architectural prohibition; covered by code review and explicit test |
| Dependency bloat increases setup difficulty | Medium | Prefer stdlib + minimal libs; remove obsolete dependencies where possible; gate heavy deps (torch, transformers) to optional extras where feasible |

---

## 13. Dependencies and Tooling Changes

### Likely Dependency Direction
- keep: `openai`, `pydub`
- add: `pytest`, `huggingface_hub`
- add (Kokoro provider): `kokoro>=0.9.4`, `soundfile`
- add (VibeVoice provider): `transformers`, `torch`, `accelerate` (versions pinned from upstream `pyproject.toml` during impl)
- system dependency (Kokoro): `espeak-ng` (Windows: `.msi` from https://github.com/espeak-ng/espeak-ng/releases; Linux: `apt-get install espeak-ng`)
- possibly remove or reduce dependence on: `requests`
- re-evaluate: `moviepy`
- add or integrate with: Ollama local API client approach (lightweight HTTP or maintained Python package, depending implementation choice)
- consider gating heavy deps (`torch`, `transformers`) behind a `vibevoice` extras group so default install stays light

### Proposed Development Dependencies
- `pytest`
- optionally `pytest-mock` if helpful

---

## 14. Open Questions for Stakeholder Approval

These are the approved implementation assumptions for final planning:

1. **Ollama support:** connect to the local Ollama instance and load locally available models as selectable options in the UI.
2. **OpenAI model discovery:** use fully dynamic listing where possible, while still filtering to valid/current models appropriate for this app’s workflow.
3. **Real API smoke tests:** use a conservative default validation budget chosen by implementation planning.

### 14.1 Final planning assumptions
- **Ollama behavior:** the app should query the local Ollama API and show local models as available options. The implementation should still validate capabilities and warn or block when a selected local model cannot support the required generation flow. [Confirmed 2026-05-21]
- **OpenAI discovery behavior:** the app should dynamically retrieve current model options where technically feasible. Because dynamic listings can be broad, the implementation should apply validation rules so only valid/current models relevant to the app are shown or are clearly labeled. [Confirmed 2026-05-21]
- **Real smoke test budget/time cap:** default target should be **under $1 per validation run** and **under 5 minutes total runtime**. Smoke tests should use tiny sample inputs and minimize generated audio length. [Confirmed 2026-05-21]

### 14.2 Open questions added by HuggingFace provider expansion
1. **GPU availability:** does the target machine have a CUDA-capable GPU with sufficient VRAM for VibeVoice-1.5B (BF16, ~3B param)? If no, Phase 6C is skipped or deferred.
   **Decision (2026-05-21):** No GPU assumed in v0.1 target machines. Phase 6.3 (VibeVoice) deferred to v0.2. (resolution mode: bulk-accept-all-defaults; see `.paul/phases/00-discovery-and-approval/00-01-APPROVAL-PACKET.md`)
2. **VibeVoice license acceptance:** stakeholder confirmation that the upstream "research and development only" guidance is acceptable for this project's distribution model, OR explicit decision to keep VibeVoice out of scope.
   **Decision (2026-05-21):** Accept research/dev-use license; require first-run opt-in dialog; do NOT ship binaries that include weights. Moot for v0.1 because Phase 6.3 is deferred; position locked for v0.2 re-use. (deferred: VibeVoice work moved to v0.2)
3. **Disk budget:** ~6 GB for VibeVoice weights + a few hundred MB for Kokoro. Confirm acceptable cache footprint.
   **Decision (2026-05-21):** Accept ~6 GB for VibeVoice (only when Phase 6.3 is enabled in v0.2); Kokoro ~500 MB always OK in v0.1.
4. **HF cache location:** default to standard HF cache (`~/.cache/huggingface`) or project-local cache directory?
   **Decision (2026-05-21):** Default to standard `~/.cache/huggingface`; expose `HF_HOME` env var override. Implementation in Phase 6.2 (Kokoro).
5. **Multi-speaker UX:** for VibeVoice, do we expose multi-speaker scripting (e.g. `[S1] line / [S2] line`) in v1, or default to single-speaker mode?
   **Decision (2026-05-21):** Defer multi-speaker scripting to v0.2. Ship VibeVoice as single-speaker first if shipped at all. (deferred: tied to Phase 6.3)
6. **Provider default:** with four providers available, confirm the recommended default remains OpenAI for hosted-mode users and Kokoro for offline-mode users.
   **Decision (2026-05-21):** OpenAI is the default hosted provider; Kokoro is the recommended offline default. Drives Phase 4 GUI provider-default behavior.

---

## 15. Recommended Approval Path

### Recommended default decisions if you want the simplest modernization
- Keep the Tkinter UI.
- Allow small targeted UX improvements without redesigning the workflow.
- Keep both preset-based quality selection and direct model selection.
- Keep `key.txt` fallback, but recommend `OPENAI_API_KEY` first.
- Keep video generation in active scope.
- Include real API smoke tests in addition to mocked automated tests.
- Add Ollama as an optional local provider, with clear capability/quality caveats.
- Add Kokoro-82M as a recommended lightweight local provider (Apache 2.0, CPU-capable).
- Add VibeVoice-1.5B as an opt-in, GPU-only local provider, with explicit research/dev license dialog and preservation of upstream safety artifacts.
- Query Ollama dynamically for locally available models.
- Use dynamic OpenAI model discovery where feasible, with filtering/validation.
- Pin HF model revisions for reproducibility.
- Keep real smoke tests short and inexpensive by default (< $1, < 5 minutes).

---

## 16. Proposed Definition of Done

The modernization project is complete when all of the following are true:
- TTS uses the official OpenAI SDK
- model/voice behavior is config-driven
- chunking is improved and covered by tests
- retries and bounded concurrency are implemented
- automated unit tests exist and pass locally
- manual validation checklist exists for human-only review areas
- README/setup docs are updated (including espeak-ng setup, HF cache notes, VibeVoice license acknowledgement)
- Kokoro-82M provider works end-to-end with pinned revision and produces valid MP3 output
- VibeVoice-1.5B provider (if in approved scope) works end-to-end on GPU with watermark + audible disclaimer preserved
- stakeholder approves the resulting workflow and defaults

---

## 17. Implementation Readiness Summary

This project is a strong candidate for a lightweight modernization because the codebase is small and its weaknesses are concentrated in a few clear places. The best path is not a rewrite; it is a focused refactor with tests, config cleanup, and reliability improvements.

No code changes should begin until the stakeholder reviews this PRD and answers the open questions above.