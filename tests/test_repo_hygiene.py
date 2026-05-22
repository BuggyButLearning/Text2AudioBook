import pathlib
import shutil
import subprocess

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
REQUIRED_GITIGNORE_PATTERNS = ["key.txt", "tmp/", "*.mp3", "*.wav"]


def test_gitignore_exists():
    assert (PROJECT_ROOT / ".gitignore").is_file()


@pytest.mark.parametrize("pattern", REQUIRED_GITIGNORE_PATTERNS)
def test_gitignore_contains_required_pattern(pattern):
    contents = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    stripped = [line.strip() for line in contents]
    assert pattern in stripped, f"Missing required .gitignore pattern: {pattern}"


def test_key_txt_not_tracked_by_git():
    if shutil.which("git") is None:
        pytest.xfail("git CLI not available in this env; cannot verify tracked files")

    result = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "ls-files", "key.txt"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.xfail(f"git ls-files failed: {result.stderr.strip()}")

    tracked = result.stdout.strip()
    assert tracked == "", f"key.txt is tracked by git: {tracked!r}"
