"""Opt-in network test: confirms the pinned Kokoro revision is still alive on HF.

Skipped by default. To run:

    HF_REVISION_CHECK=1 conda run -n text2audiobook \
        python -m pytest tests/test_hf_revision_alive.py -v

Catches drift if HF garbage-collects the pinned SHA or the repo is renamed.
No download — just hits the metadata API endpoint.
"""
import os

import pytest


GATE = os.getenv("HF_REVISION_CHECK") == "1"

pytestmark = pytest.mark.skipif(
    not GATE,
    reason="opt-in network test; set HF_REVISION_CHECK=1 to run",
)


@pytest.mark.allow_network
def test_kokoro_pinned_revision_resolves_on_hf():
    import requests
    from providers import PROVIDER_REGISTRY

    cap = PROVIDER_REGISTRY["Kokoro"]
    url = f"https://huggingface.co/api/models/{cap.hf_model_repo}/revision/{cap.hf_model_revision}"
    r = requests.get(url, timeout=10)
    assert r.status_code == 200, (
        f"HF returned {r.status_code} for {url}\n"
        f"Body: {r.text[:500]}\n"
        f"Update providers.py + tests/test_providers.py::test_pinned_revision_is_the_known_good_value "
        f"with the current SHA from https://huggingface.co/api/models/{cap.hf_model_repo}"
    )
    payload = r.json()
    assert payload.get("sha") == cap.hf_model_revision, (
        f"HF reports sha={payload.get('sha')!r}, registry has {cap.hf_model_revision!r}"
    )
