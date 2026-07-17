from pathlib import Path

from grapheinstein.core.graph import SCHEMA_VERSION, to_artifact_dict
from grapheinstein.core.index import build_inventory_graph

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_project"


def test_graph_json_contract_shape(tmp_path: Path):
    graph = build_inventory_graph(FIXTURE)
    data = to_artifact_dict(graph)

    assert data["schema_version"] == SCHEMA_VERSION
    assert SCHEMA_VERSION == "4.0.0"
    assert data["directed"] is True
    assert data["multigraph"] is False
    assert "project_root" in data["graph"]
    assert "generated_at" in data["graph"]

    node_ids = set()
    for node in data["nodes"]:
        assert set(node) >= {"id", "type", "metadata"}
        assert node["type"] in {"file", "dir", "function", "class", "method", "heading"}
        assert isinstance(node["metadata"], dict)
        node_ids.add(node["id"])

    assert "ignored_dir" not in node_ids
    assert "ignored_dir/secret.txt" not in node_ids
    assert "README.md" in node_ids

    link_types = set()
    for link in data["links"]:
        assert set(link) >= {"source", "target", "type", "provenance"}
        assert link["type"] in {
            "contains",
            "references",
            "defines",
            "imports",
            "calls",
            "section_of",
            "mentions",
        }
        assert link["provenance"] in {"extracted", "inferred"}
        assert link["source"] in node_ids
        assert link["target"] in node_ids
        link_types.add(link["type"])

    assert "contains" in link_types
    assert data["graph"].get("include_docs") is False
    assert data["graph"].get("include_pdfs") is False
