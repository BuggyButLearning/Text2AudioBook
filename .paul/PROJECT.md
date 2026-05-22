# Text2AudioBook

## What This Is

Text2AudioBook is a small Windows-first Python desktop utility (Tkinter GUI) that converts plain text files into spoken audiobook-style MP3s, with an optional pipeline to combine MP3s into a static-image video. The current modernization effort migrates the legacy raw-HTTP OpenAI TTS integration to the official OpenAI SDK and introduces a provider abstraction so the same workflow can target multiple TTS backends — hosted (OpenAI) and local (Ollama, Kokoro-82M, VibeVoice-1.5B) — while improving chunking, reliability, configuration, and test coverage.

## Core Value

A non-technical user can drop a text file into a desktop app and get back a high-quality audiobook MP3 — choosing between hosted OpenAI TTS or fully local Apache-licensed models — without editing code, juggling API payloads, or worrying about chunking and retries.

## Current State

| Attribute | Value |
|-----------|-------|
| Type | Application |
| Version | 0.0.0 |
| Status | Phases 0 + 1 + 2 + 2.1 + 3 complete; Phase 4 (GUI Reliability and UX) next |
| Last Updated | 2026-05-21 |

## Requirements

### Core Features

- Convert a text file to an audiobook-style MP3 via OpenAI TTS using the official SDK
- Provider abstraction across OpenAI (hosted), Ollama, Kokoro-82M, and VibeVoice-1.5B (local)
- Config-driven model and voice selection with quality presets (Best Quality / Balanced / Fast)
- Robust chunking with paragraph/sentence-aware splitting and bounded-concurrency retries
- Optional MP3→static-image video pipeline retained but isolated from the core flow

### Validated (Shipped)
- ✓ Modernization PRD drafted, audited, and approved (bulk: accept-all-defaults; 9 §14 decisions propagated; VibeVoice deferred to v0.2) — Phase 0
- ✓ Baseline characterization test suite (101 tests, 0.77s; pytest.ini strict config; autouse network block; .gitignore credential protection + meta-test) — Phase 0
- ✓ Conda env standard locked to named env `text2audiobook` (was `--prefix .conda`) — Phase 0
- ✓ `providers.py` immutable single-source-of-truth registry (3 providers: OpenAI / Ollama / Kokoro; VibeVoice deferred to v0.2) with MappingProxyType wrap, fail-fast regex + revision validation at module import, MILESTONE constant + docstring lock — Phase 1
- ✓ `settings.py` extended additively with HF_HOME_DEFAULT + _HFModelRevisionsView (derives from registry, no duplication) + get_provider_capability facade — Phase 1
- ✓ Conftest sys.path hack removed (00-02 audit D3 closes); regression net expanded 101 → 145 tests (44 new in `test_providers.py` and `TestPhase1Additions`) — Phase 1
- ✓ `tts_conversion.py` rewired to consume `providers.PROVIDER_REGISTRY` (module-level compiled regex constants; no inline capability duplication); `settings.OPENAI_FALLBACK_MODELS` ↔ registry consistency invariant locked by test — Phase 2
- ✓ OpenAI SDK migrated to non-deprecated `client.audio.speech.with_streaming_response.create(...)` context manager; zero DeprecationWarning in regression run; explicit `catch_warnings` test proves contract — Phase 2
- ✓ Per-provider concurrency clamp with three-branch policy-explicit logging (clamped / under-cap-local / hosted); structured chunk-level logging (provider/model/voice/attempt/elapsed) with api_key + full-chunk-text redaction; `_safe_status_callback` isolates UI failures from synthesis retry budget; regression net expanded 145 → 161 tests (+16 across `TestConcurrencyClamp`, `TestWithStreamingResponse`, `TestChunkLogging`, `TestStatusCallbackIsolation`, fallback-consistency + non-string-input tests) — Phase 2
- ✓ `model_discovery.py` module: frozen `DiscoveryResult` + `Source` enum (LIVE/FALLBACK/EMPTY); `discover_models` with `use_cache` + per-(provider, canonical-identity) cache; explicit `invalidate_cache(provider=None)` entry point for Phase 4's "Refresh Models" button; `_scrub_api_key` redacts credentials from discovery error logs + DiscoveryResult.error — Phase 2.1
- ✓ Ollama curated allowlist filter live (PRD §14.1(a)): registry pattern hides non-TTS models (llama3, mistral) from the discovery dropdown; canonical URL normalization in cache key (None ≡ default ≡ trailing-slash) — Phase 2.1
- ✓ Back-compat shims in `tts_conversion.py` preserve `list_openai_models` / `list_ollama_models` / `list_available_models` imports for main.py; regression net expanded 161 → 179 tests (+18 in new `test_model_discovery.py`); main.py untouched — Phase 2.1
- ✓ `text_processing.split_text` hardened with forward-only `find_cursor` (`_locate` helper): duplicate substrings now resolve to distinct source-ordered positions; reconstruction invariant locked by test; OPENAI_TTS_MAX_INPUT_CHARS=4096 + DEFAULT_CHUNK_MAX=3500 module-level constants; unicode + edge-case coverage; regression net expanded 179 → 195 tests (+16 across `TestSplitTextBudget`, `TestSplitTextPositions`, `TestSplitTextEdgeCases`); position-accuracy fix is bug fix not behavior shift (no characterization needed) — Phase 3

### Active (In Progress)
- [ ] Phase 4 — GUI Reliability and UX (next up)

### Planned (Next)
- Phase 1: settings/config module + provider abstraction + key precedence
- Phase 2: OpenAI SDK migration + retries + bounded concurrency
- Phase 2A: OpenAI/Ollama model discovery + Refresh Models UI
- Phase 3: improved text chunking
- Phase 4: GUI progress/disable-while-running + validation messaging
- Phase 5: audio/video pipeline cleanup
- Phase 6: Ollama local provider
- Phase 6B: Kokoro-82M local provider (recommended local default)
- Phase 6C: VibeVoice-1.5B local provider (opt-in, GPU-only, research-license)
- Phase 7: tests, smoke tests, README/docs

### Out of Scope
- Web app / SaaS conversion — out per PRD §3.2
- Databases, user accounts, authentication, cloud sync — out per PRD §3.2
- Plugin architecture — out per PRD §3.2
- UI framework migration off Tkinter — out per PRD §3.2
- Heavy NLP dependencies without clear justification — out per PRD §3.2
- Stripping or muting upstream-baked safety artifacts (VibeVoice watermark + audible AI disclaimer) — architecturally prohibited
- VibeVoice-1.5B provider (Phase 6.3) — **deferred to v0.2** per §14.2(1) decision 2026-05-21 (no GPU assumed in v0.1 target machines)
- Multi-speaker scripting UX — **deferred to v0.2** per §14.2(5) decision 2026-05-21 (tied to Phase 6.3 deferral)

## Target Users

**Primary:** Individual creators converting text into audiobook-style audio
- Prefer a desktop GUI over scripts/CLI
- Want a simple OpenAI TTS workflow without editing code
- May want a fully-local Apache-licensed option (Kokoro) to avoid per-character API costs
- Windows-first environment

**Secondary:** Small-scale content producers experimenting with multi-speaker/long-form output via VibeVoice (research/dev use only)

## Context

**Business Context:**
Solo-developer hobby/utility project. No commercial distribution model yet. The VibeVoice provider is upstream-restricted to research/development use, which constrains how that path can be presented and used.

**Technical Context:**
Existing Python codebase: `main.py` (Tkinter entry), `text_processing.py`, `tts_conversion.py`, `combine_and_convert.py`, `settings.py`. Conda environment lives at `.conda/` per CONDA_ENV_RULE.md. Currently uses raw `requests.post()` against `/v1/audio/speech` and hardcodes `tts-1`; needs SDK migration. `key.txt` API key file exists as a legacy fallback.

## Constraints

### Technical Constraints
- Windows-first desktop runtime; conda-managed Python 3.11 environment at `.conda/`
- Keep dependency footprint light; gate heavy deps (`torch`, `transformers`) behind optional extras
- Kokoro provider requires `espeak-ng` as a system dependency (Windows: `.msi` installer; Linux: `apt`)
- VibeVoice provider requires a CUDA-capable GPU with enough VRAM for ~3B-param BF16 model (~6 GB download)
- Pin HuggingFace model revisions/commit hashes to prevent silent model swaps
- Do not strip, alter, or disable VibeVoice's upstream audible AI disclaimer or imperceptible watermark
- Bounded concurrency required; default 1 for local GPU/CPU-bound providers

### Business Constraints
- VibeVoice upstream license: research/development use only — must surface to user before first download
- Real OpenAI smoke tests must stay under $1 per validation run and under 5 minutes runtime (PRD §14.1)
- No GitHub attribution to Claude per global rule

### Compliance Constraints
- VibeVoice safety artifacts (watermark + audible disclaimer) must remain in output

## Key Decisions

| Decision | Rationale | Date | Status |
|----------|-----------|------|--------|
| Keep Tkinter UI; modernize behavior under the hood | Stakeholder approved minimal UX disruption (PRD §7.1) | 2026-05-21 | Active |
| Prefer `OPENAI_API_KEY` env var with `key.txt` as fallback | Modernize credential loading without breaking existing users (PRD §FR-2) | 2026-05-21 | Active |
| Provider abstraction with four providers: OpenAI / Ollama / Kokoro / VibeVoice | Enable local + hosted flows behind one config surface (PRD §FR-1A) | 2026-05-21 | Active |
| Kokoro-82M as recommended local default; VibeVoice as opt-in GPU-only path | Apache 2.0 license + CPU-capable + audiobook-narrator fit; VibeVoice restricted to research/dev | 2026-05-21 | Active |
| Pin HF model revisions in settings | Prevent silent upstream model swaps from breaking pipeline | 2026-05-21 | Active |
| Real smoke tests bounded at <$1 / <5 min | Stakeholder budget for ongoing validation runs (PRD §14.1) | 2026-05-21 | Active |
| Keep MP3→video pipeline in active scope but isolated | Stakeholder approved video as secondary feature (PRD §FR-7) | 2026-05-21 | Active |
| Use conda env named `text2audiobook` (`conda activate text2audiobook`) for all commands | Per CONDA_ENV_RULE.md; do not use base interpreter or the legacy `--prefix .conda` form | 2026-05-21 | Active |
| §14.1(a) Ollama behavior: query local API, validate capabilities, warn/block unsupported models | Confirmed during 00-01 approval (see .paul/phases/00-discovery-and-approval/00-01-APPROVAL-PACKET.md) | 2026-05-21 | Active |
| §14.1(b) OpenAI discovery: dynamic listing with allowlist filter to known TTS models | Confirmed during 00-01 approval (see .paul/phases/00-discovery-and-approval/00-01-APPROVAL-PACKET.md) | 2026-05-21 | Active |
| §14.1(c) Real smoke test budget: <$1 per run, <5 min total | Confirmed during 00-01 approval (see .paul/phases/00-discovery-and-approval/00-01-APPROVAL-PACKET.md) | 2026-05-21 | Active |
| §14.2(1) Phase 6.3 VibeVoice deferred from v0.1 to v0.2 | No GPU assumed in v0.1 target machines (see .paul/phases/00-discovery-and-approval/00-01-APPROVAL-PACKET.md) | 2026-05-21 | Active |
| §14.2(2) VibeVoice research/dev license accepted with first-run opt-in + no shipped weights | Pre-approved position for v0.2 (see .paul/phases/00-discovery-and-approval/00-01-APPROVAL-PACKET.md) | 2026-05-21 | Active |
| §14.2(3) Disk budget: Kokoro ~500 MB in v0.1; VibeVoice ~6 GB only when Phase 6.3 enabled (v0.2) | Confirmed during 00-01 approval (see .paul/phases/00-discovery-and-approval/00-01-APPROVAL-PACKET.md) | 2026-05-21 | Active |
| §14.2(4) HF cache: default `~/.cache/huggingface`; `HF_HOME` env override exposed | Confirmed during 00-01 approval (see .paul/phases/00-discovery-and-approval/00-01-APPROVAL-PACKET.md) | 2026-05-21 | Active |
| §14.2(5) Multi-speaker scripting deferred to v0.2 | Tied to Phase 6.3 deferral (see .paul/phases/00-discovery-and-approval/00-01-APPROVAL-PACKET.md) | 2026-05-21 | Active |
| §14.2(6) Default provider: OpenAI hosted; Kokoro offline | Confirmed during 00-01 approval (see .paul/phases/00-discovery-and-approval/00-01-APPROVAL-PACKET.md) | 2026-05-21 | Active |
| Phase 2: tts_conversion.py consumes the immutable providers.PROVIDER_REGISTRY as single source of truth; settings.OPENAI_FALLBACK_MODELS retained as parallel facade with drift-lock test | Avoids the Phase 1 G1/M2 defect class (HF revision drift) for OpenAI fallback models | 2026-05-21 | Active |
| Phase 2: OpenAI SDK uses `with_streaming_response.create(...)` context manager; non-streaming `create()` actively asserted against in tests | Eliminates DeprecationWarning + future-proofs against openai 3.x removal of `response.stream_to_file()` direct call | 2026-05-21 | Active |
| Phase 2: Local-provider concurrency clamped at registry default; hosted honors user-requested value; clamp event always logged with explicit policy message | Local synthesis is memory-bound; hosted is rate-limit-bound — split policy correctly. Auditor sees clamp decisions at a glance | 2026-05-21 | Active |
| Phase 2: status_callback failures isolated via `_safe_status_callback` (logged WARNING, never abort chunk synthesis) | Realistic trigger is Tkinter "main thread not in main loop" after GUI close; UI bugs must not consume retry budget | 2026-05-21 | Active |
| Phase 2.1: Discovery extracted into `model_discovery.py`; `tts_conversion.py` keeps thin shims preserving `main.py`'s import path | Discovery has distinct concerns (HTTP, cache, error reporting) from synthesis; Phase 4 GUI imports only the surface it needs | 2026-05-21 | Active |
| Phase 2.1: FALLBACK and EMPTY discovery results are cached identically to LIVE; sticky-until-invalidate semantics | Predictable UX for a desktop app; "Refresh Models" is the only recovery path; no surprise refresh storms | 2026-05-21 | Active |
| Phase 2.1: `Source.EMPTY` distinguishes "upstream responded but yielded nothing useful" from `Source.FALLBACK` (exception path) | Phase 4 GUI can route messaging correctly (red "down" banner vs yellow "no models" banner) | 2026-05-21 | Active |
| Phase 2.1: Ollama discovery canonicalizes URL once; None ≡ default ≡ trailing-slash all collapse to one cache entry | Prevents drift between cache key and underlying network call | 2026-05-21 | Active |
| Phase 2.1: `_scrub_api_key` redacts credentials from discovery error logs + DiscoveryResult.error | Discovery introduces new logging surface; Phase 2 set the synthesis-side invariant — Phase 2.1 propagates it to discovery | 2026-05-21 | Active |
| Phase 3: `text_processing.split_text` uses forward-only `find_cursor` so duplicate substrings resolve to distinct, source-ordered positions | Prevents `text.find` from collapsing repeated phrases (e.g. "He said." appearing twice) onto a single offset; Phase 4 progress bar can rely on positions | 2026-05-21 | Active |
| Phase 3: `OPENAI_TTS_MAX_INPUT_CHARS=4096` + `DEFAULT_CHUNK_MAX=3500` exposed as module-level constants in text_processing.py | Names the OpenAI hard ceiling and safe margin so future contributors cannot quietly raise the default past the API limit; per-provider char limits deferred to Phase 6 / 6.2 | 2026-05-21 | Active |

## Success Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| OpenAI SDK migration | TTS path runs via official SDK, no raw `requests.post` to `/v1/audio/speech` | Live (with_streaming_response context manager; 0 DeprecationWarning) | ✓ Phase 2 |
| Provider parity | OpenAI + Kokoro paths both produce playable MP3 from same text input | Not started | Not started |
| Test coverage on deterministic logic | Unit tests cover chunking, config precedence, provider dispatch, retry decision logic | None | Not started |
| Real OpenAI smoke test | <$1 cost, <5 min runtime, produces valid MP3 | Not run | Not started |
| VibeVoice safety artifacts preserved | Audible disclaimer + watermark present in 100% of sampled outputs | Not run | Not started |
| Phase exit criteria satisfied | All PRD §9 phases marked complete with validation blocks | 5 / 10 | In progress |

## Tech Stack / Tools

| Layer | Technology | Notes |
|-------|------------|-------|
| Runtime | Python 3.11 (conda) | Env name `text2audiobook` (per `environment.yml`); activate with `conda activate text2audiobook` |
| GUI | Tkinter + `ttkbootstrap>=1.10.1` | Keep existing single-window layout |
| Hosted TTS | `openai>=1.0.0` (official SDK) | Migrating off raw `requests.post` |
| Audio merge | `pydub>=0.25.1` | + `ffmpeg` system dep (conda-forge) |
| Test runner | `pytest>=8.0.0` (+ optional `pytest-mock`) | Mocks for API, fixtures for filesystem |
| Local TTS — Ollama | local HTTP API at `http://localhost:11434` | Currently uses `requests`; model discovery via `/api/tags` |
| Local TTS — Kokoro | `kokoro>=0.9.4`, `soundfile`, `huggingface_hub` | Apache 2.0; needs `espeak-ng` system dep |
| Local TTS — VibeVoice | `transformers`, `torch`, `accelerate`, `huggingface_hub` | MIT weights, research-only license; GPU required; ~6 GB |
| Video (optional) | `moviepy` (under re-evaluation) | May replace parts with FFmpeg calls |
| Config | `config.json` + env vars (`OPENAI_API_KEY`, `OLLAMA_BASE_URL`, `TTS_MAX_CONCURRENCY`) | Precedence: UI > env > config file > code defaults |

## Links

| Resource | URL |
|----------|-----|
| Repository | (local) c:\Users\ME\Documents\Projects\Text2AudioBook |
| PRD | MODERNIZATION_PRD.md |
| Conda env rule | CONDA_ENV_RULE.md |
| Research notes (TTS) | tmp/hf_tts_research_notes.md |
| Kokoro model card | https://huggingface.co/hexgrad/Kokoro-82M |
| VibeVoice model card | https://huggingface.co/microsoft/VibeVoice-1.5B |

---
*PROJECT.md — Updated when requirements or context change*
*Last updated: 2026-05-21 after Phase 3*
