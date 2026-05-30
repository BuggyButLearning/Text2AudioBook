"""Opt-in real-OpenAI smoke test (Phase 7).

This test calls the real OpenAI TTS API. It is SKIPPED by default. To run it:

    OPENAI_SMOKE_TEST=1 OPENAI_API_KEY=sk-... conda run -n text2audiobook \
        python -m pytest tests/test_openai_smoke.py -v

Cost: ~$0.0001 per run (~20 characters synthesized via tts-1).
Runtime: < 5 seconds.

Bounded per PRD §14.1(c): <$1 per run, <5 min total.
"""
import os
import sys
from pathlib import Path

import pytest


SMOKE_GATE = os.getenv("OPENAI_SMOKE_TEST") == "1"
API_KEY = os.getenv("OPENAI_API_KEY")

pytestmark = pytest.mark.skipif(
    not SMOKE_GATE or not API_KEY,
    reason="opt-in real-API smoke test; set OPENAI_SMOKE_TEST=1 and OPENAI_API_KEY=sk-... to run",
)


def _is_valid_mp3_header(blob: bytes) -> bool:
    """ID3v2 tag header ('ID3') OR raw MPEG frame sync (0xFFF*) -- either is acceptable."""
    if blob.startswith(b"ID3"):
        return True
    if len(blob) >= 2 and blob[0] == 0xFF and (blob[1] & 0xE0) == 0xE0:
        return True
    return False


def test_openai_smoke_writes_valid_mp3(tmp_path):
    """Send ~20 chars to tts-1, assert MP3 file exists with valid header + size > 1 KB."""
    from tts_conversion import convert_text_chunk_to_speech
    from settings import build_runtime_settings

    settings = build_runtime_settings(provider="OpenAI", model="tts-1", voice="alloy")
    settings.openai_api_key = API_KEY  # ensure env-provided key wins

    chunk = "Smoke test ok."
    out_path = convert_text_chunk_to_speech(
        chunk, 0, settings, tmp_path, "smoke", retries=1,
    )
    assert out_path is not None, "synthesis returned None"
    out = Path(out_path)
    assert out.exists(), f"file not written: {out}"
    assert out.stat().st_size > 1024, f"file suspiciously small: {out.stat().st_size} bytes"
    with open(out, "rb") as f:
        header = f.read(4)
    assert _is_valid_mp3_header(header), f"not a valid MP3 header: {header!r}"
