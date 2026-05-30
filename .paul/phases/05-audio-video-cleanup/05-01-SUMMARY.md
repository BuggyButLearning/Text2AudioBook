---
phase: 05-audio-video-cleanup
plan: 01
subsystem: audio-video
tags: [ffmpeg, video-pipeline, helper-extraction, validation, gpu-probe]
requires:
  - phase: 04-gui-reliability-and-ux
    provides: enumerated-validation message pattern
provides:
  - extracted `_validate_video_inputs(mp3_files, image_file, output_folder, output_filename)` → (ok, missing)
  - extracted `_build_ffmpeg_create_video_command(...)` → argv list (pure-Python, testable encoder selection)
  - `is_gpu_encoding_available(ffmpeg_runner=None)` injection seam; tolerant of `FileNotFoundError`/`OSError` (audit S2)
  - default_output_folder fallback in `start_conversion` for parity with main.py (audit S1)
  - enumerated validation errors ("Please provide: MP3 Files, Background Image")
affects: []
tech-stack:
  added: []
  patterns:
    - "Subprocess-runner injection seam: accept optional callable parameter, default to subprocess.run, tests inject fakes"
    - "Command-builder helpers separate from invocation: tests assert argv composition without running the binary"
status: complete
duration: ~15min
started: 2026-05-22
completed: 2026-05-22
---

# 05-01 SUMMARY — Audio/Video Cleanup

## Outcome
Audited `combine_and_convert.py` and confirmed the direct-ffmpeg approach is correct (no MoviePy needed per PRD §FR-7). Extracted `_validate_video_inputs` and `_build_ffmpeg_create_video_command` as pure-Python helpers, added `ffmpeg_runner` injection seam to `is_gpu_encoding_available`, widened the exception catch to include `FileNotFoundError` + `OSError` so the probe is robust to ffmpeg-missing-from-PATH. `create_video` now delegates argv construction to the builder (DRY — was duplicated across GPU branch + CPU fallback). Regression suite: **243 passed in 0.91s, exit 0**.

## AC Results

| AC | Title | Result |
|----|-------|--------|
| AC-1 | `_build_ffmpeg_create_video_command` builder | PASS — `TestBuildFfmpegCommand` covers GPU/CPU branches, required flags, fps stringification, path stringification |
| AC-2 | `_validate_video_inputs` enumerated validation | PASS — `TestValidateVideoInputs` covers all-populated, single-empty, all-empty, whitespace, None, stable order |
| AC-3 | Enumerated error in `start_conversion` | PASS — replaced "Please provide all required inputs" with `f"Please provide: {', '.join(missing)}"` |
| AC-4 | `is_gpu_encoding_available(ffmpeg_runner=None)` seam | PASS — `TestGpuProbeInjectionSeam` covers FileNotFoundError, OSError, injection-seam-used |
| AC-5 | ≥ 10 tests | PASS — +15 new tests across 3 classes |
| AC-6 | Regression green | PASS — 243 tests, 0.91s, exit 0; no edits to providers/settings/model_discovery/tts_conversion/text_processing/main |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `combine_and_convert.py` | Added `_VIDEO_VALIDATION_LABELS`, `_validate_video_inputs`, `_build_ffmpeg_create_video_command`, `default_output_folder`; modified `is_gpu_encoding_available` (injection seam + widened exception catch); modified `create_video` (calls builder for both GPU + CPU branches); modified `start_conversion` (enumerated validation + default_output_folder fallback) | Phase 5 extraction + audit S1/S2 |
| `tests/test_combine_and_convert.py` | Appended 3 new test classes (15 tests total: 6 validation + 6 command-builder + 3 probe-injection-seam) | Locks extracted helpers + ffmpeg-missing tolerance |

## Test Count

| Phase | Tests | Δ |
|-------|------:|---|
| 04-01 baseline | 228 | — |
| **05-01 add** | **243** | **+15** |

## Audit Findings Applied

- **S1 (parity with main.py):** `start_conversion` now defaults empty output_folder to `script_directory / "output"` before validation, so the validator never sees an unintentional empty.
- **S2 (ffmpeg-missing tolerance):** `is_gpu_encoding_available` widened from `except CalledProcessError` to `except (CalledProcessError, FileNotFoundError, OSError)`. Test class `TestGpuProbeInjectionSeam` locks both error paths.

## Deferred

- D1: Mid-encode cancellation (no SIGINT to long ffmpeg process). Out of v0.1.
- D2: GUI threading for `combine_and_convert.start_conversion` (separate-window utility; Phase 4 threading not propagated). Phase 7 polish.

## Loop Status

- PLAN ✓ AUDIT ✓ APPLY ✓ UNIFY ✓ (2026-05-22)
