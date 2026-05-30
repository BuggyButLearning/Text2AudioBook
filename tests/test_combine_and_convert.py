import subprocess
import types

import combine_and_convert
from combine_and_convert import (
    _build_ffmpeg_create_video_command,
    _validate_video_inputs,
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


class TestValidateVideoInputs:
    """Phase 5: pure-Python validation, mirror of main.py's _validate_conversion_inputs."""

    def test_all_populated_returns_ok(self):
        ok, missing = _validate_video_inputs(["a.mp3"], "img.png", "/tmp", "out")
        assert ok is True
        assert missing == []

    def test_empty_mp3_list_flags_field(self):
        ok, missing = _validate_video_inputs([], "img.png", "/tmp", "out")
        assert ok is False
        assert missing == ["MP3 Files"]

    def test_all_empty_returns_all_fields(self):
        ok, missing = _validate_video_inputs([], "", "", "")
        assert ok is False
        assert missing == ["MP3 Files", "Background Image", "Output Folder", "Output File Name"]

    def test_whitespace_image_counts_as_empty(self):
        ok, missing = _validate_video_inputs(["a.mp3"], "   ", "/tmp", "out")
        assert ok is False
        assert "Background Image" in missing

    def test_none_image_counts_as_empty(self):
        ok, missing = _validate_video_inputs(["a.mp3"], None, "/tmp", "out")
        assert ok is False
        assert "Background Image" in missing

    def test_field_order_stable(self):
        ok, missing = _validate_video_inputs([], "", "/tmp", "out")
        assert missing == ["MP3 Files", "Background Image"]


class TestBuildFfmpegCommand:
    """Phase 5: extracted command builder so encoder selection and flag order
    are testable without invoking ffmpeg."""

    def test_gpu_branch_uses_h264_nvenc(self):
        argv = _build_ffmpeg_create_video_command("a.mp3", "img.png", "out.mp4", 24, use_gpu=True)
        assert "h264_nvenc" in argv
        assert "libx264" not in argv

    def test_cpu_branch_uses_libx264(self):
        argv = _build_ffmpeg_create_video_command("a.mp3", "img.png", "out.mp4", 24, use_gpu=False)
        assert "libx264" in argv
        assert "h264_nvenc" not in argv

    def test_required_flags_present(self):
        argv = _build_ffmpeg_create_video_command("a.mp3", "img.png", "out.mp4", 24, use_gpu=False)
        for flag in ["-tune", "stillimage", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-shortest", "-y", "-loop", "1"]:
            assert flag in argv

    def test_fps_interpolated_as_string(self):
        argv = _build_ffmpeg_create_video_command("a.mp3", "img.png", "out.mp4", 30, use_gpu=False)
        idx = argv.index("-r")
        assert argv[idx + 1] == "30"

    def test_paths_stringified(self):
        from pathlib import Path
        argv = _build_ffmpeg_create_video_command(Path("a.mp3"), Path("img.png"), Path("out.mp4"), 24, use_gpu=False)
        assert "a.mp3" in argv
        assert "img.png" in argv
        assert "out.mp4" in argv

    def test_ffmpeg_is_first(self):
        argv = _build_ffmpeg_create_video_command("a.mp3", "img.png", "out.mp4", 24, use_gpu=True)
        assert argv[0] == "ffmpeg"


class TestGpuProbeInjectionSeam:
    """Phase 5: is_gpu_encoding_available now accepts ffmpeg_runner injection
    for tests, AND tolerates ffmpeg-missing-from-PATH (audit S2)."""

    def test_returns_false_when_ffmpeg_missing(self):
        def fake_runner(*_a, **_kw):
            raise FileNotFoundError("ffmpeg not found")
        assert is_gpu_encoding_available(ffmpeg_runner=fake_runner) is False

    def test_returns_false_on_os_error(self):
        def fake_runner(*_a, **_kw):
            raise OSError("permission denied")
        assert is_gpu_encoding_available(ffmpeg_runner=fake_runner) is False

    def test_injection_seam_used_when_provided(self):
        def fake_runner(*_a, **_kw):
            return types.SimpleNamespace(stdout="h264_nvenc available", returncode=0)
        assert is_gpu_encoding_available(ffmpeg_runner=fake_runner) is True
