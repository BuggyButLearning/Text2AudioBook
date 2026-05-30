# Text2AudioBook CLI Reference

Machine-callable entry point for the same TTS pipeline the GUI uses. Designed for AI agents and scripting: stable exit codes, optional `--json` JSON Lines output, every GUI setting overridable via flags.

## Invocation

After running the Windows installer (or `install.ps1`):

```sh
text2audiobook <command> [options]
```

Without installer, from repo:

```sh
conda activate text2audiobook
python cli.py <command> [options]
```

Global flag (must precede the subcommand): `--json` — switch output to JSON Lines.

### Help on no-args / `?`

Both of these print the top-level help and exit 0:

```sh
text2audiobook
text2audiobook ?
```

`?` also works after a subcommand (aliased to `-h`):

```sh
text2audiobook synthesize ?
text2audiobook list-providers ?
```

## Commands

| Command | Purpose |
|---------|---------|
| `list-providers` | Registry-driven provider list |
| `list-voices --provider P` | Capability voices for provider P |
| `list-models --provider P` | Live discovery (OpenAI / Ollama) or registry fallback (Kokoro) |
| `chunk-policy` | Show built-in chunk_max defaults + config overrides |
| `show-config` | Dump effective RuntimeSettings (after env / config / flags) |
| `synthesize` | Convert text/markdown file to MP3 |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | success |
| 1 | invalid arguments / validation failure |
| 2 | synthesis failure (chunk error, network) |
| 3 | provider not ready (e.g. Kokoro lib missing) |
| 4 | input file unreadable / empty |

## `list-providers`

Prints one provider per line; with `--json`, emits `{"providers": [...]}`.

```sh
python cli.py list-providers
# OpenAI
# Ollama
# Kokoro

python cli.py --json list-providers
# {"providers": ["OpenAI", "Ollama", "Kokoro"]}
```

## `list-voices --provider PROVIDER`

```sh
python cli.py list-voices --provider OpenAI
# alloy
# echo
# ...

python cli.py --json list-voices --provider Kokoro
# {"provider": "Kokoro", "voices": ["af_heart", "af_alloy", ...]}
```

## `list-models --provider PROVIDER [--refresh] [--openai-api-key KEY] [--ollama-base-url URL]`

Live discovery. Use `--refresh` to invalidate the per-provider cache.

```sh
python cli.py list-models --provider OpenAI --refresh
# tts-1
# tts-1-hd

python cli.py --json list-models --provider Ollama
# {"provider": "Ollama", "models": ["bark", ...], "source": "live", "error": null}
```

`source` values: `live` (fresh API), `fallback` (live failed, using registry), `empty` (no models matched filter).

## `chunk-policy [--provider P] [--model M]`

Shows research-backed chunk_max defaults. Optional `--provider` (and `--model`) resolves the effective value using your config's `chunk_overrides` map.

```sh
python cli.py chunk-policy
# Built-in defaults:
#   OpenAI     3500
#   Kokoro     2000
#   Ollama     1000
# Fallback: 3500

python cli.py --json chunk-policy --provider Kokoro --model kokoro-82m
# {"policy": {...}, "overrides": {}, "fallback": 3500,
#  "resolved": {"provider": "Kokoro", "model": "kokoro-82m", "chunk_max": 2000}}
```

### Built-in defaults

| Provider | chunk_max | Why |
|----------|----------:|-----|
| OpenAI (`tts-*`) | 3500 | API hard ceiling is 4096 chars/request; 3500 leaves headroom for whitespace normalization |
| Kokoro (`kokoro*`) | 2000 | KPipeline auto-splits internally at 510 phonemes (waterfall: `!.?…` then `:;` then `,—`). Larger app chunks reduce per-chunk model warmup overhead |
| Ollama (`bark*` / `tts*` / `speech*`) | 1000 | bark-style models commonly handle ~300 tokens before quality degrades |
| (fallback for unknown provider) | 3500 | safe choice; OpenAI-like |

### Overriding in `config.json`

```json
{
  "chunk_overrides": {
    "OpenAI": 4000,
    "Kokoro:kokoro-82m": 3000,
    "Ollama:bark-small": 800
  }
}
```

Precedence (most specific wins): `"Provider:model"` > `"Provider"` > built-in default.

## `show-config [--provider P] [--quality Q] [--model M] [--voice V]`

Dumps the effective RuntimeSettings after merging env vars, `config.json`, and CLI flags. Useful for debugging an AI integration.

```sh
python cli.py --json show-config --provider Kokoro
# {"provider": "Kokoro", "model": "kokoro-82m", "voice": "af_heart", ...,
#  "chunk_max": 2000, "openai_api_key_present": true}
```

## `synthesize` (main command)

```sh
python cli.py synthesize --input book.md --output audiobook.mp3 \
    --provider OpenAI --model tts-1 --voice nova --quality "Best Quality"
```

### Flags

| Flag | Required | Default | Notes |
|------|----------|---------|-------|
| `--input PATH` | yes | — | `.txt` / `.md` / `.markdown`. Markdown stripped of syntax. |
| `--output PATH` | yes | — | `.mp3`. Parent dir created if missing. |
| `--provider {OpenAI,Ollama,Kokoro}` | no | from config | |
| `--model NAME` | no | provider default | |
| `--voice NAME` | no | provider default | |
| `--quality {Balanced,"Best Quality",Fast}` | no | Balanced | OpenAI: changes model + speed |
| `--chunk-max N` | no | resolved via chunk_policy | overrides any other source |
| `--speed FLOAT` | no | preset value | post-applied |
| `--max-concurrency N` | no | 2 | clamped to 1 for local providers |
| `--openai-api-key KEY` | no | env / key.txt | |
| `--ollama-base-url URL` | no | env / default | |
| `--quiet` | no | false | suppress per-chunk status |
| `--dry-run` | no | false | validate + print plan, don't synthesize |

### JSON Lines events (`--json synthesize`)

| event | fields | when |
|-------|--------|------|
| `start` | provider, model, voice, chunks, chunk_max, output | once at start |
| `dry-run` | same as start, plus event=`dry-run` | replaces start when `--dry-run` |
| `status` | message | per chunk-level status (unless `--quiet`) |
| `complete` | output, duration_ms, chunks | once at end on success |
| `error` | stage, message | on any failure; stage ∈ {input, validation, provider, synthesis} |

Each event is one parseable JSON object per line. Stream-friendly for tail+parse.

### Example: dry-run

```sh
python cli.py --json synthesize \
    --input chapter1.md --output chapter1.mp3 \
    --provider Kokoro --voice af_heart --dry-run
# {"event": "dry-run", "provider": "Kokoro", "model": "kokoro-82m", "voice": "af_heart",
#  "chunks": 14, "chunk_max": 2000, "output": "chapter1.mp3"}
```

### Example: AI agent integration

```python
import json, subprocess
proc = subprocess.run(
    ["python", "cli.py", "--json", "synthesize",
     "--input", "draft.md", "--output", "draft.mp3",
     "--provider", "OpenAI", "--voice", "nova"],
    capture_output=True, text=True, check=False,
)
for line in proc.stdout.splitlines():
    event = json.loads(line)
    if event["event"] == "complete":
        print(f"Done in {event['duration_ms']}ms")
    elif event["event"] == "error":
        raise RuntimeError(event["message"])
if proc.returncode != 0:
    raise SystemExit(proc.returncode)
```

## Environment variables

| Var | Purpose |
|-----|---------|
| `OPENAI_API_KEY` | OpenAI Bearer token (else `key.txt`) |
| `OLLAMA_BASE_URL` | Ollama endpoint (default `http://localhost:11434`) |
| `HF_HOME` | HuggingFace cache (Kokoro model location) |
| `TTS_MAX_CONCURRENCY` | Max parallel chunks for hosted providers |

CLI flags override env vars override `config.json` override built-in defaults.
