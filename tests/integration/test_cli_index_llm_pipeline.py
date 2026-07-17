import json
from pathlib import Path

from grapheinstein.core.graph import load_artifact
from grapheinstein.core.index import index_project

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "llm_project"


def _fake_chat(**_kwargs):
    return {
        "entities": [
            {
                "name": "Auth Middleware",
                "kind": "domain_term",
                "evidence": "Auth Middleware validates JWT on each request.",
                "confidence": 0.95,
            }
        ],
        "relations": [
            {
                "type": "implements",
                "subject": "validate_token",
                "object": "Auth Middleware",
                "evidence": "validate_token implements the Auth Middleware checks described above.",
                "confidence": 0.9,
            }
        ],
    }


def test_pipeline_retains_structural_edges(tmp_path: Path):
    out = tmp_path / "graph.json"
    index_project(
        FIXTURE,
        out,
        languages=["python"],
        include_docs=True,
        enrich_llm=True,
        llm_chat=_fake_chat,
    )
    data = load_artifact(out)
    assert any(link["type"] == "contains" for link in data["links"])
    assert any(link["type"] == "defines" for link in data["links"])
    assert any(n["type"] == "function" for n in data["nodes"])
    assert any(n["type"] == "concept" for n in data["nodes"])
    assert any(link["type"] == "implements" for link in data["links"])


def test_without_flag_zero_llm_side_effects(tmp_path: Path):
    calls = {"n": 0}

    def tracking(**_k):
        calls["n"] += 1
        return {"entities": [], "relations": []}

    out = tmp_path / "graph.json"
    index_project(
        FIXTURE,
        out,
        languages=["python"],
        enrich_llm=False,
        llm_chat=tracking,
    )
    assert calls["n"] == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "6.0.0"
