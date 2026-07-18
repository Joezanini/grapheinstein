import importlib.util
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "config_cache"
AUTH = Path(__file__).resolve().parents[1] / "fixtures" / "query_graphs" / "auth_chunks.json"

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("fastapi") is None
    or importlib.util.find_spec("httpx") is None,
    reason="serve extras not installed",
)


def test_serve_roundtrip_index_query(tmp_path: Path):
    from fastapi.testclient import TestClient

    from grapheinstein.serve import create_app

    client = TestClient(create_app())
    graph = tmp_path / "http-graph.json"
    r = client.post(
        "/index",
        json={"project_path": str(FIXTURE), "output": str(graph), "include_docs": True},
    )
    assert r.status_code == 200
    assert graph.exists()

    sub = tmp_path / "http-sub.json"
    r2 = client.post(
        "/query",
        json={
            "question": "configuration",
            "input": str(AUTH),
            "output": str(sub),
            "no_answer": True,
            "match_threshold": 0.3,
        },
    )
    assert r2.status_code == 200
    assert r2.json()["ok"] is True
    assert sub.exists() or r2.json().get("output")
