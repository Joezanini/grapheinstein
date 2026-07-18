import importlib.util

import pytest

from grapheinstein.serve import ServeExtrasError, ensure_serve_deps


def test_ensure_serve_deps_raises_with_install_hint(monkeypatch):
    real_find = importlib.util.find_spec

    def fake_find(name, package=None):
        if name in ("fastapi", "uvicorn"):
            return None
        return real_find(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find)
    with pytest.raises(ServeExtrasError) as exc:
        ensure_serve_deps()
    msg = str(exc.value)
    assert "grapheinstein[serve]" in msg
    assert "fastapi" in msg
    assert "uvicorn" in msg


def test_ensure_serve_deps_ok_when_present():
    # In CI with [serve] installed this passes; without, skip.
    fastapi_spec = importlib.util.find_spec("fastapi")
    uvicorn_spec = importlib.util.find_spec("uvicorn")
    if fastapi_spec is None or uvicorn_spec is None:
        pytest.skip("serve extras not installed")
    ensure_serve_deps()  # must not raise
