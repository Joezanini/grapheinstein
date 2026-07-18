from pathlib import Path

import pytest

from grapheinstein.core.graph import (
    GraphError,
    add_contains_edge,
    add_node,
    load_artifact,
    new_inventory_graph,
    save_graph,
    to_artifact_dict,
    validate_artifact,
    write_artifact_dict,
)


def test_save_graph_validates_before_write(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, ".", "dir")
    out = tmp_path / "graph.json"
    written = save_graph(graph, out)
    assert written.exists()
    data = load_artifact(written)
    assert data["schema_version"] == "6.0.0"
    assert all("metadata" in n for n in data["nodes"])


def test_write_rejects_invalid_artifact(tmp_path: Path):
    bad = {
        "schema_version": "6.0.0",
        "directed": True,
        "multigraph": False,
        "graph": {"project_root": "/x", "generated_at": "2026-07-17T00:00:00Z"},
        "nodes": [{"id": ".", "type": "dir"}],  # missing metadata
        "links": [],
    }
    out = tmp_path / "bad.json"
    with pytest.raises(GraphError):
        write_artifact_dict(bad, out)
    assert not out.exists()


def test_atomic_write_preserves_prior_on_validation_failure(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, ".", "dir")
    out = tmp_path / "graph.json"
    save_graph(graph, out)
    prior = out.read_text(encoding="utf-8")

    bad = {
        "schema_version": "9.9.9",
        "directed": True,
        "multigraph": False,
        "graph": {},
        "nodes": [],
        "links": [],
    }
    with pytest.raises(GraphError):
        write_artifact_dict(bad, out)
    assert out.read_text(encoding="utf-8") == prior


def test_to_artifact_preserves_contains_and_metadata(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, ".", "dir")
    add_node(graph, "a.txt", "file", metadata={"kept": True})
    add_contains_edge(graph, ".", "a.txt")
    data = to_artifact_dict(graph)
    validate_artifact(data, Path("<mem>"))
    node = next(n for n in data["nodes"] if n["id"] == "a.txt")
    assert node["metadata"]["kept"] is True
    link = next(edge for edge in data["links"] if edge["type"] == "contains")
    assert link["provenance"] == "extracted"
