# Text2AudioBook
![Text2AudioBook](https://github.com/BuggyButLearning/Text2AudioBook/assets/162375864/7bc5c288-308f-459f-957c-04f97da146bb)

Convert plain text files into spoken audiobook MP3s via a multi-provider TTS pipeline. Windows-first desktop GUI (Tkinter + ttkbootstrap). v0.1 ships three providers — hosted OpenAI plus two local options — under one config surface.

## Provider Matrix (v0.1)

| Provider | Kind | License | Setup cost | Voices | Notes |
|----------|------|---------|-----------|--------|-------|
| **OpenAI** | hosted API | per-character billing | API key only | 6 (alloy / echo / fable / onyx / nova / shimmer) | Recommended starting point |
| **Ollama** | local discovery | varies per model | `ollama serve` + TTS-capable model | n/a | **Discovery only** — standard Ollama exposes no general TTS endpoint; for local synthesis use Kokoro |
| **Kokoro-82M** | local synthesis | Apache 2.0 | `pip install kokoro soundfile` + `espeak-ng` system binary | 20 American English (v0.1) | Recommended local default; CPU-capable, ~500 MB HF download |
| ~~VibeVoice-1.5B~~ | local synthesis | research/dev | (GPU required) | n/a | **Deferred to v0.2** — no GPU assumed in v0.1 target machines |

The Provider dropdown in the GUI reads from `providers.PROVIDER_REGISTRY` so it always reflects what's available.

## Features

- Accepts `.txt`, `.md`, and `.markdown` input files; Markdown syntax (headers, emphasis, code blocks, links, lists, tables, HTML tags) stripped before TTS so the engine speaks the prose, not the punctuation
- Background-threaded conversion (window stays responsive)
- Refresh Models button that truly invalidates the discovery cache
- Per-provider model discovery (live API for OpenAI, `/api/tags` for Ollama, registry fallback for Kokoro)
- Curated Ollama allowlist filter (hides non-TTS models like `llama3` / `mistral` from the dropdown)
- Paragraph-aware text chunking with sentence-aware fallback; OPENAI char budget enforced (≤4096)
- Bounded concurrency clamped per provider (local: 1; hosted: 2)
- Pinned HuggingFace model revisions (Kokoro); no silent upstream swaps
- Optional MP3 → static-image video pipeline in `combine_and_convert.py`

## Installation

### Option A: Windows installer (.exe, recommended)

Download `text2audiobook-setup-v0.1.0.exe` (built from `installer/text2audiobook.iss` — see [installer/README.md](installer/README.md)). Run it.

- Per-user install, no UAC prompt
- Add/Remove Programs entry
- Start menu shortcut for the GUI
- `text2audiobook` CLI on USER PATH from any new shell
- Prompts to create the `text2audiobook` conda env on first install if missing

Requires Miniconda/Anaconda already on PATH ([install](https://docs.conda.io/en/latest/miniconda.html)).

### Option B: Manual install script (no .exe)

From a cloned repo, run in PowerShell:

```sh
powershell -ExecutionPolicy Bypass -File install.ps1
```

Same outcome as Option A minus the Add/Remove Programs + Start menu entries. Run `uninstall.ps1` to reverse.

### Option C: Just use `python cli.py` directly

Skip the installer; `conda activate text2audiobook && python cli.py ...` works fine. Continue with the manual conda setup below.

### 1. Conda environment

```sh
conda env create --file environment.yml
conda activate text2audiobook
```

Update after `environment.yml` changes:

```sh
conda env update --name text2audiobook --file environment.yml --prune
```

### 2. FFmpeg

- **Windows:** install FFmpeg from <https://ffmpeg.org/download.html>, add `bin/` to PATH
- **macOS:** `brew install ffmpeg`
- **Linux:** `apt install ffmpeg`

`environment.yml` includes the conda-forge ffmpeg package — usually enough on Linux/macOS.

### 3. OpenAI credentials (optional — only if you'll use OpenAI provider)

Either set `OPENAI_API_KEY` in your environment OR drop the key into `key.txt` in the project root. Env var wins if both present.

### 4. Kokoro local synthesis (optional — only if you'll use Kokoro provider)

**One-click install (recommended):** pick Kokoro in the Provider dropdown and click Start. The GUI prompts to install the `kokoro` / `soundfile` / `huggingface_hub` packages AND prefetch the pinned ~500 MB model snapshot. Status label ticks through "Installing kokoro packages (pip)..." → "Downloading Kokoro-82M model weights..." → "Kokoro runtime ready." Window stays responsive (background thread).

**Manual install:** if you prefer the terminal:

```sh
conda activate text2audiobook
pip install kokoro soundfile huggingface_hub  # already in requirements.txt
```

Either way, espeak-ng must be installed separately (system dep, not a pip package):

- **Windows:** download `.msi` from <https://github.com/espeak-ng/espeak-ng/releases> and run
- **macOS:** `brew install espeak-ng`
- **Linux:** `apt install espeak-ng`

The first Kokoro synthesis downloads the pinned model revision (~500 MB) into `~/.cache/huggingface` (or `$HF_HOME` if set).

### 5. Ollama local discovery (optional — only if you'll use Ollama provider)

Install and start Ollama from <https://ollama.com/>. The app probes `http://localhost:11434` by default; override with `OLLAMA_BASE_URL`. Pull at least one TTS-capable model (matching `bark|kokoro|tts|speech`) for it to surface in the dropdown.

## Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `OPENAI_API_KEY` | — | OpenAI Bearer token. Falls back to `key.txt`. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Override Ollama endpoint. |
| `HF_HOME` | `~/.cache/huggingface` | HuggingFace model cache directory (Kokoro). |
| `TTS_MAX_CONCURRENCY` | `2` | Max parallel chunks for hosted providers. Local providers clamp to 1 regardless. |
| `OPENAI_SMOKE_TEST` | — | Set to `1` to enable the opt-in real-API smoke test in `tests/test_openai_smoke.py`. |

## Running

GUI:

```sh
python main.py
```

Optional MP3-merge + image-to-video GUI:

```sh
python combine_and_convert.py
```

## Tests

```sh
python -m pytest tests
```

266+ tests pass in under 1 second on a modern laptop. All tests are deterministic — no network, no real model downloads. The opt-in OpenAI smoke test (`tests/test_openai_smoke.py`) is skipped by default; enable with `OPENAI_SMOKE_TEST=1` + a real API key.

## CLI (machine-callable)

For AI agents and scripting. Same TTS pipeline as the GUI. Stable exit codes, optional `--json` JSON Lines output, every GUI setting overridable.

```sh
python cli.py synthesize --input book.md --output book.mp3 \
    --provider OpenAI --voice nova --quality "Best Quality"

python cli.py --json list-models --provider OpenAI --refresh
python cli.py chunk-policy
```

Full reference: [docs/CLI.md](docs/CLI.md). Covers all commands, flags, JSON event schemas, exit codes, AI integration example.

### Chunk size per provider

Research-backed defaults (override per-provider or per-model via `config.json` `chunk_overrides`):

| Provider | chunk_max | Why |
|----------|----------:|-----|
| OpenAI | 3500 chars | 4096 API hard ceiling; leaves headroom |
| Kokoro | 2000 chars | KPipeline auto-splits at 510 phonemes internally; larger app chunks cut warmup overhead |
| Ollama | 1000 chars | bark-style models degrade past ~300 tokens |

Override:
```json
{
  "chunk_overrides": {
    "OpenAI": 4000,
    "Kokoro:kokoro-82m": 3000
  }
}
```
Or via CLI: `--chunk-max 2500`.

## Validation Walkthrough

See [HUMAN_VALIDATION_CHECKLIST.md](HUMAN_VALIDATION_CHECKLIST.md) for the pre-release walkthrough.

## Module Layout

| File | Purpose |
|------|---------|
| `main.py` | Tkinter GUI entry point. Threaded synthesis. |
| `providers.py` | Immutable provider capability registry (single source of truth). |
| `settings.py` | Runtime settings, config IO, OpenAI key precedence. |
| `model_discovery.py` | `discover_models` + `ollama_reachable` + per-(provider, identity) cache. |
| `tts_conversion.py` | Chunk-level synthesis dispatch (OpenAI / Ollama-error / Kokoro). |
| `text_processing.py` | Paragraph/sentence-aware chunker; forward-cursor position metadata. |
| `kokoro_synthesis.py` | Kokoro lazy-import wrapper + espeak-ng probe + `_write_kokoro_speech`. |
| `combine_and_convert.py` | Separate MP3-merge + image→video utility. |

## Troubleshooting

- **`OpenAI discovery failed (...) -- using fallback list`** — your `OPENAI_API_KEY` is invalid or unreachable. The credential is automatically redacted from logs as `***REDACTED***`. Fix the key and click Refresh Models.
- **`No Ollama models available -- connection refused -- Is ollama serve running?`** — start `ollama serve`. If running but still empty, pull a TTS-capable model: `ollama pull bark`.
- **`Kokoro not ready: kokoro package not importable`** — `pip install kokoro soundfile huggingface_hub` inside the conda env.
- **`Kokoro not ready: espeak-ng not found on PATH`** — install the system binary (see Installation §4).
- **`Conversion failed -- ... not available through standard Ollama endpoints`** — Ollama exposes no general TTS endpoint. Use the Kokoro provider for local synthesis.

## Contributing

Fork → branch → PR. Follow existing test patterns (deterministic, no real network, lazy-import for optional deps). Don't add deps without justifying in the PR description.

## License

MIT. See [LICENSE](LICENSE).

VibeVoice (Phase 6.3, v0.2) is upstream-restricted to research/dev use and ships a baked watermark + audible AI disclaimer that v0.2 will never strip.
