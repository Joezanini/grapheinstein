from pathlib import Path

from grapheinstein.core.graph import SCHEMA_VERSION, load_artifact, to_artifact_dict
from grapheinstein.core.index import build_inventory_graph, index_project

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_project"
OLD = Path(__file__).resolve().parents[1] / "fixtures" / "old_schema_v1_graph.json"
OLD_V2 = Path(__file__).resolve().parents[1] / "fixtures" / "old_schema_v2_graph.json"


def test_v3_nodes_and_edge_provenance(tmp_path: Path):
    out = tmp_path / "graph.json"
    index_project(FIXTURE, out, languages=["python"])
    data = load_artifact(out)

    assert data["schema_version"] == "6.0.0"
    assert SCHEMA_VERSION == "6.0.0"

    for node in data["nodes"]:
        assert "kind" not in node
        assert node["type"] in {"file", "dir", "function", "class", "method", "heading"}
        assert isinstance(node["metadata"], dict)

    contains = [link for link in data["links"] if link["type"] == "contains"]
    references = [link for link in data["links"] if link["type"] == "references"]
    assert contains
    for link in contains + references:
        assert link["provenance"] == "extracted"

    assert any(
        link["source"] == "README.md" and link["target"] == "src/main.py"
        for link in references
    )


def test_reject_old_schema():
    import pytest

    from grapheinstein.core.graph import GraphError

    with pytest.raises(GraphError, match="unsupported|Re-index|pre-2.0.0|schema_version"):
        load_artifact(OLD)


def test_reject_schema_v2():
    import pytest

    from grapheinstein.core.graph import GraphError

    with pytest.raises(GraphError, match="unsupported|Re-index|schema_version"):
        load_artifact(OLD_V2)


def test_in_memory_artifact_matches_contract():
    graph = build_inventory_graph(FIXTURE, languages=["python"])
    data = to_artifact_dict(graph)
    assert data["schema_version"] == "6.0.0"
    assert all("type" in n and "metadata" in n for n in data["nodes"])
