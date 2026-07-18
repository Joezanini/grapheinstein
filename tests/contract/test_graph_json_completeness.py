import json
from pathlib import Path

from grapheinstein.core.graph import add_node, load_artifact, new_inventory_graph, save_graph


def test_contract_completeness_after_save(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, ".", "dir")
    add_node(graph, "readme.md", "file", metadata={"note": "keep"})
    out = tmp_path / "graph.json"
    save_graph(graph, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "6.0.0"
    assert "nodes" in data and "links" in data
    assert data["graph"]["project_root"]
    assert data["graph"]["generated_at"]
    for node in data["nodes"]:
        assert "id" in node and "type" in node and "metadata" in node
    for link in data["links"]:
        assert "source" in link and "target" in link
        assert "type" in link and "provenance" in link
    loaded = load_artifact(out)
    assert loaded["nodes"][1]["metadata"]["note"] == "keep"
