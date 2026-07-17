from pathlib import Path

from grapheinstein.core.graph import add_node, new_inventory_graph, next_versioned_graph_path, save_graph


def test_versioned_snapshots_do_not_overwrite(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, ".", "dir")
    primary = tmp_path / "graph.json"
    save_graph(graph, primary, versioned=True)
    v1 = tmp_path / "graph_v1.json"
    assert primary.exists() and v1.exists()
    v1_text = v1.read_text(encoding="utf-8")
    save_graph(graph, primary, versioned=True)
    v2 = tmp_path / "graph_v2.json"
    assert v2.exists()
    assert v1.read_text(encoding="utf-8") == v1_text
    save_graph(graph, primary, versioned=True)
    assert (tmp_path / "graph_v3.json").exists()


def test_versioned_compress_names(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, ".", "dir")
    primary = tmp_path / "graph.json"
    written = save_graph(graph, primary, compress=True, versioned=True)
    assert written.name.endswith(".json.gz")
    assert (tmp_path / "graph_v1.json.gz").exists()
    assert next_versioned_graph_path(tmp_path, compress=True).name == "graph_v2.json.gz"
