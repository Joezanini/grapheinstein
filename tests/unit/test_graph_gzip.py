import gzip
import json
from pathlib import Path

from grapheinstein.core.graph import (
    add_node,
    load_artifact,
    new_inventory_graph,
    next_versioned_graph_path,
    resolve_graph_output_path,
    save_graph,
)


def test_resolve_appends_gz():
    assert resolve_graph_output_path(Path("graph.json"), compress=True) == Path("graph.json.gz")
    assert resolve_graph_output_path(Path("graph.json.gz"), compress=True) == Path("graph.json.gz")
    assert resolve_graph_output_path(Path("graph.json"), compress=False) == Path("graph.json")


def test_gzip_round_trip(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, ".", "dir")
    add_node(graph, "f.txt", "file", metadata={"x": 1})
    out = tmp_path / "graph.json"
    written = save_graph(graph, out, compress=True)
    assert written.name.endswith(".json.gz")
    assert written.exists()
    loaded = load_artifact(written)
    assert loaded["schema_version"] == "6.0.0"
    meta = next(n for n in loaded["nodes"] if n["id"] == "f.txt")["metadata"]
    assert meta["x"] == 1
    raw = gzip.open(written, "rt", encoding="utf-8").read()
    assert json.loads(raw)["schema_version"] == "6.0.0"


def test_next_versioned_numbering(tmp_path: Path):
    p1 = next_versioned_graph_path(tmp_path, compress=False)
    assert p1.name == "graph_v1.json"
    p1.write_text("{}", encoding="utf-8")
    p2 = next_versioned_graph_path(tmp_path, compress=False)
    assert p2.name == "graph_v2.json"
    gz = next_versioned_graph_path(tmp_path, compress=True)
    assert gz.name == "graph_v2.json.gz"
