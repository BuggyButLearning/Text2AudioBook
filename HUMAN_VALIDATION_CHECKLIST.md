# Human Validation Checklist — Text2AudioBook v0.1

Pre-release walkthrough. Run on a clean machine (or fresh conda env) before tagging v0.1.0.

## 0. Clean checkout

- [ ] `git clone` into a fresh directory
- [ ] No `.conda/`, no `__pycache__/`, no `output/` left over

## 1. Environment

- [ ] `conda env create --file environment.yml` succeeds
- [ ] `conda activate text2audiobook` succeeds
- [ ] `python --version` reports 3.11
- [ ] `ffmpeg -version` resolves (system PATH OK)

## 2. Regression suite (no real API, no real download)

- [ ] `python -m pytest tests -q` reports **≥ 266 passed, 1 skipped** in **< 5s**
- [ ] Zero `DeprecationWarning`, zero `SyntaxWarning` in the run
- [ ] Skipped test is `tests/test_openai_smoke.py` (opt-in)

## 3. GUI sanity

- [ ] `python main.py` opens the window with title "Text to Speech Converter"
- [ ] Provider dropdown shows **OpenAI**, **Ollama**, **Kokoro** (3 entries; no VibeVoice)
- [ ] Voice dropdown shows the 6 OpenAI voices by default

## 4. OpenAI path (requires `key.txt` or `OPENAI_API_KEY` env var)

- [ ] Refresh Models → status shows "Loaded N OpenAI models" (or "OpenAI discovery failed (...) -- using fallback list" if API down; both are acceptable)
- [ ] Pick a short `.txt` file (1-2 paragraphs), name "smoke", click Start
- [ ] Window stays draggable during synthesis
- [ ] Status label visibly ticks: Reading input → Preparing text → Converting N chunk(s) → Merging audio → Conversion completed
- [ ] Provider/Quality/Model/Voice dropdowns are GREYED OUT during synthesis
- [ ] Success dialog appears with output path
- [ ] `output/smoke.mp3` plays back as the input text in the chosen voice
- [ ] `output/smoke_chunk_positions.txt` lists chunk boundaries

## 5. Validation errors

- [ ] Clear all fields, click Start → dialog reads "Please provide: Input File, Output File Name, Model"
- [ ] Fast-double-click Start during an in-flight conversion → no second worker spawns (silent rejection per audit S1)

## 6. Ollama path (requires Ollama installed and running)

- [ ] Switch Provider → Ollama
- [ ] Refresh Models →
  - if running: status shows "Loaded N Ollama models" with TTS-only filter (no `llama3` / `mistral` in dropdown)
  - if not running: status shows "No Ollama models available -- connection refused (...) -- Is `ollama serve` running?" + warning dialog
- [ ] Pick a "supported" Ollama model (matching `bark|kokoro|tts|speech`), click Start → error dialog mentions "use the Kokoro provider" (Phase 6 documented limitation)

## 7. Kokoro path (optional — requires `pip install kokoro soundfile huggingface_hub` + espeak-ng)

- [ ] Switch Provider → Kokoro; voice dropdown repopulates with `af_heart`, `am_michael`, etc. (20 voices)
- [ ] If kokoro lib missing: Start → error dialog reads "kokoro package not importable. Install: `pip install kokoro soundfile huggingface_hub`"
- [ ] If espeak-ng missing: Start → error dialog reads "espeak-ng not found on PATH. Install from https://github.com/espeak-ng/espeak-ng/releases ..."
- [ ] When both ready: pick same text file, click Start
- [ ] First run downloads pinned model revision to `~/.cache/huggingface` (~500 MB; ~30-60s on broadband)
- [ ] Subsequent runs skip the download
- [ ] Output MP3 plays back the text in the chosen Kokoro voice (American English)

## 8. Real OpenAI smoke (opt-in, costs ~$0.0001)

- [ ] `OPENAI_SMOKE_TEST=1 OPENAI_API_KEY=sk-... python -m pytest tests/test_openai_smoke.py -v`
- [ ] Reports `PASSED` in < 5 seconds
- [ ] Cost on OpenAI dashboard < $0.01

## 9. Combine + Video utility (optional)

- [ ] `python combine_and_convert.py` opens the second window
- [ ] Pick 2+ MP3s + a background image + output folder + name; click Start
- [ ] Output `.mp4` plays with image + concatenated audio
- [ ] Validation: clear all fields → error "Please provide: MP3 Files, Background Image, Output Folder, Output File Name"

## 10. Credential hygiene

- [ ] `git ls-files | grep key.txt` returns nothing
- [ ] `pytest tests/test_repo_hygiene.py` passes (enforces `key.txt` not tracked)
- [ ] If OpenAI auth fails in step 4, logs show `***REDACTED***` not the raw key value

## 11. Sign-off

- [ ] All boxes checked OR documented exception in release notes
- [ ] Tag `v0.1.0`
- [ ] Push
