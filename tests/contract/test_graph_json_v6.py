import json
from pathlib import Path

import pytest

from grapheinstein.core.graph import SCHEMA_VERSION, GraphError, load_artifact
from grapheinstein.core.index import index_project

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "llm_project"
OLD_V5 = Path(__file__).resolve().parents[1] / "fixtures" / "old_schema_v5_graph.json"


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


def test_v6_concept_and_enrichment_edges(tmp_path: Path):
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
    assert data["schema_version"] == "6.0.0"
    assert SCHEMA_VERSION == "6.0.0"
    assert data["graph"]["enrich_llm"] is True
    concepts = [n for n in data["nodes"] if n["type"] == "concept"]
    assert concepts
    enrichment = [
        link
        for link in data["links"]
        if link["type"] in {"implements", "depends_on"}
        or (link["type"] == "mentions" and "confidence" in link)
    ]
    assert enrichment
    for link in enrichment:
        assert link["provenance"] in {"extracted", "inferred"}
        assert 0.0 <= float(link["confidence"]) <= 1.0
        assert link["evidence"].strip()
    impl = [link for link in enrichment if link["type"] == "implements"]
    assert impl
    assert all(link["provenance"] == "inferred" for link in impl)


def test_reject_v5_artifact():
    with pytest.raises(GraphError, match="unsupported|Re-index|schema_version"):
        load_artifact(OLD_V5)


def test_enrich_llm_false_metadata(tmp_path: Path):
    out = tmp_path / "graph.json"
    index_project(FIXTURE, out, languages=[], enrich_llm=False)
    data = json.loads(out.read_text())
    assert data["schema_version"] == "6.0.0"
    assert data["graph"].get("enrich_llm") is False
    assert not any(n["type"] == "concept" for n in data["nodes"])
