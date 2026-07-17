from pathlib import Path

from grapheinstein.core.index import build_inventory_graph, discover_paths

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_project"


def test_gitignore_excludes_ignored_dir():
    paths = {rel: typ for rel, typ, _meta in discover_paths(FIXTURE)}
    assert "README.md" in paths
    assert "src/main.py" in paths
    assert "src" in paths
    assert "ignored_dir" not in paths
    assert "ignored_dir/secret.txt" not in paths


def test_parent_directory_nodes_created():
    graph = build_inventory_graph(FIXTURE)
    assert "." in graph
    assert "src" in graph.nodes
    assert graph.nodes["src"]["type"] == "dir"
    assert graph.has_edge(".", "src")
    assert graph.has_edge("src", "src/main.py")
    assert graph.edges["src", "src/main.py"]["provenance"] == "extracted"
    assert graph.edges["src", "src/main.py"]["type"] == "contains"
