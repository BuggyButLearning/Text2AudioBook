import pathlib
import socket
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def _block_network(monkeypatch, request):
    if "allow_network" in request.keywords:
        return

    def _blocked(*_args, **_kwargs):
        raise RuntimeError("Network access blocked in tests (audit S2)")

    monkeypatch.setattr("socket.socket.connect", _blocked)


@pytest.fixture
def clean_env(monkeypatch):
    for var in ("OPENAI_API_KEY", "OLLAMA_BASE_URL", "TTS_MAX_CONCURRENCY", "HF_HOME"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def no_key_file(tmp_path, monkeypatch):
    import settings
    monkeypatch.setattr(settings, "KEY_FILE", tmp_path / "no-such-key.txt")


@pytest.fixture
def tmp_key_file(tmp_path, monkeypatch):
    import settings

    def _make(contents: str):
        path = tmp_path / "key.txt"
        path.write_text(contents, encoding="utf-8")
        monkeypatch.setattr(settings, "KEY_FILE", path)
        return path

    return _make


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    import settings
    cfg = tmp_path / "config.json"
    monkeypatch.setattr(settings, "CONFIG_FILE", cfg)
    return cfg
