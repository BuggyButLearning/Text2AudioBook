import subprocess
import types

import combine_and_convert
from combine_and_convert import (
    combine_audio_files,
    get_media_height,
    is_gpu_encoding_available,
)


class TestCombineAudioFiles:
    def test_returns_combined_segment(self, monkeypatch):
        calls = []

        class FakeSegment:
            def __init__(self, name="x"):
                self.name = name

            def __iadd__(self, other):
                calls.append(other.name)
                return self

            def __add__(self, other):
                calls.append(other.name)
                return self

        monkeypatch.setattr(combine_and_convert.AudioSegment, "empty", lambda: FakeSegment("empty"))
        monkeypatch.setattr(combine_and_convert.AudioSegment, "from_mp3", lambda p: FakeSegment(str(p)))

        result = combine_audio_files(["one.mp3", "two.mp3", "three.mp3"])
        assert result is not None
        assert calls == ["one.mp3", "two.mp3", "three.mp3"]

    def test_empty_list_returns_empty_segment(self, monkeypatch):
        # CHARACTERIZED — current code returns AudioSegment.empty() on empty input
        # rather than raising. Phase 5 audit may change this.
        class FakeSegment:
            def __init__(self):
                self.iadds = 0

            def __iadd__(self, other):
                self.iadds += 1
                return self

        sentinel = FakeSegment()
        monkeypatch.setattr(combine_and_convert.AudioSegment, "empty", lambda: sentinel)
        result = combine_audio_files([])
        assert result is sentinel
        assert sentinel.iadds == 0


class TestIsGPUEncodingAvailable:
    def test_returns_true_when_nvenc_in_output(self, monkeypatch):
        fake_result = types.SimpleNamespace(stdout="h264_nvenc  V.....  NVIDIA NVENC")
        monkeypatch.setattr(combine_and_convert.subprocess, "run", lambda *_a, **_kw: fake_result)
        assert is_gpu_encoding_available() is True

    def test_returns_false_when_nvenc_absent(self, monkeypatch):
        fake_result = types.SimpleNamespace(stdout="libx264 only")
        monkeypatch.setattr(combine_and_convert.subprocess, "run", lambda *_a, **_kw: fake_result)
        assert is_gpu_encoding_available() is False

    def test_returns_false_on_subprocess_error(self, monkeypatch):
        def fake_run(*_args, **_kwargs):
            raise subprocess.CalledProcessError(returncode=1, cmd=["ffmpeg"])

        monkeypatch.setattr(combine_and_convert.subprocess, "run", fake_run)
        assert is_gpu_encoding_available() is False


class TestGetMediaHeight:
    def test_parses_integer_height(self, monkeypatch):
        fake_result = types.SimpleNamespace(stdout="2160\n")
        monkeypatch.setattr(combine_and_convert.subprocess, "run", lambda *_a, **_kw: fake_result)
        assert get_media_height("anything.jpg") == 2160

    def test_returns_none_on_empty_stdout(self, monkeypatch):
        fake_result = types.SimpleNamespace(stdout="")
        monkeypatch.setattr(combine_and_convert.subprocess, "run", lambda *_a, **_kw: fake_result)
        assert get_media_height("x") is None

    def test_returns_none_on_exception(self, monkeypatch):
        def boom(*_a, **_kw):
            raise RuntimeError("ffprobe missing")

        monkeypatch.setattr(combine_and_convert.subprocess, "run", boom)
        assert get_media_height("x") is None
