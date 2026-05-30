---
phase: 08-cli-and-chunk-policy
plan: 01
subsystem: cli + chunking
tags: [cli, argparse, json-lines, chunk-policy, ai-callable, per-model-chunking]
requires: [02, 02.1, 03, 04, 05, 06, 06.2, 07]
provides:
  - cli.py argparse entry point (synthesize / list-providers / list-models / list-voices / chunk-policy / show-config)
  - chunk_policy.py per-(provider, model) chunk_max with config + caller overrides
  - docs/CLI.md machine-readable CLI reference
  - settings.RuntimeSettings.chunk_max field + build_runtime_settings(chunk_max=...) plumbing
  - main.py worker honors settings.chunk_max in split_text
  - --json JSON Lines output for AI agent integration
  - stable exit codes (0/1/2/3/4)
status: complete
duration: ~40min
started: 2026-05-22
completed: 2026-05-22
---

# 08-01 SUMMARY — CLI + Per-Model Chunk Policy

## Outcome
Two new features landed:

1. **`cli.py`** — argparse entry point with 6 subcommands (`synthesize`, `list-providers`, `list-models`, `list-voices`, `chunk-policy`, `show-config`). Every GUI setting overridable via flags. `--json` emits JSON Lines for AI agent consumption. Stable exit codes (0/1/2/3/4 documented in docs/CLI.md).
2. **`chunk_policy.py`** — research-backed `chunk_max` defaults per provider (OpenAI 3500, Kokoro 2000, Ollama 1000), overridable via `config.json` `chunk_overrides` map (`"Provider"` or `"Provider:model"` keys) or `--chunk-max` CLI flag. Both GUI and CLI consume.

Research source for Kokoro 2000: kokoro/pipeline.py shows internal waterfall splitter on `!.?…` then `:;` then `,—`, capped at **510 phonemes per segment**. App-level 2000-char chunks let the internal splitter do its work without per-chunk model warmup overhead. OpenAI 3500 unchanged (4096 hard ceiling, 15% headroom). Ollama 1000 conservative for bark-class models (~300 token quality cliff).

Regression: **340 passed, 7 skipped (all opt-in) in 1.23s**.

## AC Results

| AC | Title | Result |
|----|-------|--------|
| AC-1 | chunk_policy with research-backed defaults + override precedence | PASS — `TestBuiltinDefaults` (4) + `TestResolveChunkMax` (6) + `TestPolicySnapshot` (3) |
| AC-2 | split_text accepts chunk_max from caller | PASS — wired through main.py worker AND CLI synthesize path |
| AC-3 | CLI synthesize works end-to-end | PASS — dry-run + success + error paths in `TestSynthesizeDryRun` / `TestSynthesizeSuccess` / `TestSynthesizeErrorPaths` |
| AC-4 | CLI list-* commands work + --json | PASS — `TestListProviders` / `TestListVoices` / `TestListModels` |
| AC-5 | Exit codes stable | PASS — 0 success / 1 invalid args / 2 synthesis / 3 provider not ready / 4 input unreadable; all asserted via subprocess-equivalent calls |
| AC-6 | JSON Lines parseable | PASS — `TestSynthesizeSuccess` asserts each event individually JSON-parseable, start + complete present |
| AC-7 | docs/CLI.md comprehensive | PASS — every flag, every command, every exit code, JSON schema table, AI agent example |
| AC-8 | GUI uses chunk_policy | PASS — `build_runtime_settings` calls `resolve_chunk_max` when `chunk_max` arg is None; worker passes `settings.chunk_max` to `split_text` |
| AC-9 | Regression | PASS — 340 default tests + 7 opt-in (skipped) |

## Files Created/Modified

| File | Change |
|------|--------|
| `cli.py` | NEW (~250 lines) — argparse parser + 6 command handlers + JSON Lines emitter + exit codes |
| `chunk_policy.py` | NEW (~70 lines) — DEFAULT_CHUNK_MAX_BY_PROVIDER, resolve_chunk_max, policy_snapshot |
| `docs/CLI.md` | NEW (~180 lines) — full machine-readable reference |
| `settings.py` | Added `chunk_max` field to RuntimeSettings; `build_runtime_settings(chunk_max=...)` parameter; resolves via chunk_policy when None |
| `main.py` | Worker passes `settings.chunk_max` to `split_text(text, max_length=...)` |
| `README.md` | New CLI + Chunk policy section linking to docs/CLI.md |
| `tests/test_chunk_policy.py` | NEW — 13 tests (defaults, overrides, snapshot) |
| `tests/test_cli.py` | NEW — 17 tests across 7 classes (list-*, chunk-policy, show-config, synthesize, error paths, --chunk-max override) |

## Test Count

| Phase | Tests | Δ |
|-------|------:|---|
| 07-01 baseline | 310 | — |
| **08-01 add** | **340** | **+30** |

## Verified Behaviors (real, not mocked)

- `python cli.py list-providers` → 3 providers listed
- `python cli.py --json list-providers` → valid JSON
- `python cli.py chunk-policy` → human table
- `python cli.py --json chunk-policy --provider Kokoro --model kokoro-82m` → resolves to 2000
- `python cli.py --json synthesize --input X --output Y --provider OpenAI --dry-run` → emits `dry-run` event, returns 0
- `build_runtime_settings(provider='Kokoro')` → chunk_max=2000
- `build_runtime_settings(provider='OpenAI')` → chunk_max=3500
- `build_runtime_settings(provider='OpenAI', chunk_max=2500)` → chunk_max=2500

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| chunk_max lives on chunk_policy.py NOT ProviderCapability | providers.py is Phase 1 immutable single-source-of-truth for capability; chunk_max is a tuning knob (different deployments pick different values for same provider/model) — narrow contract |
| Override precedence: explicit > config[`P:M`] > config[`P`] > built-in | most-specific wins; matches user expectation; same pattern as VS Code settings |
| `--json` emits JSON Lines (one obj per line) not single array | stream-friendly: AI agents can tail + parse incrementally; partial output still parseable |
| Exit codes split synthesis (2) from provider-not-ready (3) from input-unreadable (4) | actionable error paths: agent can pick a retry/install/skip strategy per code |
| `python cli.py` not `python -m text2audiobook` | repo is flat scripts (not package); avoiding restructure for v0.1; can add `__main__.py` later |
| Markdown stripping happens in `read_text_from_file` regardless of CLI/GUI caller | single chokepoint; CLI doesn't need its own md handling |

## Deferred (low ROI)

- D1: `python -m text2audiobook` invocation — needs package restructure; cosmetic
- D2: Shell completions (bash/zsh/fish) — argparse-shell-completion add-on; Phase 9 polish
- D3: Progress bar with ETA — current per-chunk status is enough
- D4: Per-chunk JSON event with elapsed_ms — `status_callback` could be tightened; defer

## Loop Status
PLAN ✓ AUDIT (inline) ✓ APPLY ✓ UNIFY ✓ (2026-05-22)
