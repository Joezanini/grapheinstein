import importlib.util
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "config_cache"
AUTH = Path(__file__).resolve().parents[1] / "fixtures" / "query_graphs" / "auth_chunks.json"

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("fastapi") is None
    or importlib.util.find_spec("httpx") is None,
    reason="serve extras (fastapi/httpx) not installed",
)


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from grapheinstein.serve import create_app

    return TestClient(create_app())


def test_http_index_and_query(client, tmp_path: Path):
    graph = tmp_path / "g.json"
    r = client.post(
        "/index",
        json={
            "project_path": str(FIXTURE),
            "output": str(graph),
            "include_docs": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert Path(body["output"]).exists()
    assert "stats" in body

    sub = tmp_path / "sub.json"
    r2 = client.post(
        "/query",
        json={
            "question": "How does authentication work?",
            "input": str(AUTH),
            "output": str(sub),
            "no_answer": True,
            "match_threshold": 0.3,
        },
    )
    assert r2.status_code == 200, r2.text
    qbody = r2.json()
    assert qbody["ok"] is True
    assert qbody["schema_version"] == "1.0.0"
    assert "hit_ids" in qbody
    assert "answer" in qbody


def test_http_index_validation_error(client):
    r = client.post("/index", json={})
    assert r.status_code in (400, 422)


def test_http_query_missing_input(client, tmp_path: Path):
    r = client.post(
        "/query",
        json={"question": "x", "input": str(tmp_path / "missing.json"), "no_answer": True},
    )
    assert r.status_code in (400, 404)
    body = r.json()
    assert body["ok"] is False
    assert "error" in body
