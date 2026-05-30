# 05-01 AUDIT — Audio/Video Cleanup

**Verdict:** Conditionally acceptable. 0 must-have. 2 strongly-recommended applied.

## Findings

### Strongly Recommended (applied)

**S1 — Default `output_folder` to script directory if empty (parity with main.py)**
Today empty `output_folder` is a validation failure. main.py defaults to `script_directory / "output"`. For parity and friendlier UX, `_validate_video_inputs` STILL flags empty output_folder, but `start_conversion` should mirror main.py: `output_folder = folder_entry.get() or str(default_output_folder)` so the validator never sees an unintentional empty. **Applied:** added default_output_folder constant and fallback in start_conversion.

**S2 — Test for ffmpeg-not-installed path**
`is_gpu_encoding_available` swallows `CalledProcessError`. It does NOT handle `FileNotFoundError` (ffmpeg not on PATH). Add a test that injects a runner raising FileNotFoundError; probe should return False (not crash). **Applied:** widened except to `(CalledProcessError, FileNotFoundError, OSError)`.

### Deferred

- D1: Mid-encode cancellation (no kill of long ffmpeg process). Out of v0.1.
- D2: GUI threading on `start_conversion` (separate-window utility; Phase 4 threading not propagated to combine_and_convert). Phase 7 polish.
