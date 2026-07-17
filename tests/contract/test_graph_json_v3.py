import json
from pathlib import Path

from grapheinstein.core.graph import SCHEMA_VERSION, load_artifact
from grapheinstein.core.index import index_project

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "code_project"
OLD_V2 = Path(__file__).resolve().parents[1] / "fixtures" / "old_schema_v2_graph.json"


def test_v3_code_nodes_and_provenance(tmp_path: Path):
    out = tmp_path / "graph.json"
    index_project(FIXTURE, out, languages=["python", "go"])
    data = load_artifact(out)
    assert data["schema_version"] == "5.0.0"
    assert SCHEMA_VERSION == "5.0.0"

    functions = [n for n in data["nodes"] if n["type"] == "function"]
    assert any(n["metadata"]["name"] == "greet" and n["metadata"]["start_line"] == 1 for n in functions)
    assert any(n["metadata"]["name"] == "Add" for n in functions)

    for link in data["links"]:
        if link["type"] in {"defines", "imports", "calls"}:
            assert link["provenance"] == "extracted"

    assert any(link["type"] == "defines" for link in data["links"])
    assert any(link["type"] == "imports" for link in data["links"])
    assert any(link["type"] == "calls" for link in data["links"])


def test_reject_v2_artifact():
    import pytest
    from grapheinstein.core.graph import GraphError

    with pytest.raises(GraphError, match="unsupported|Re-index|schema_version"):
        load_artifact(OLD_V2)
