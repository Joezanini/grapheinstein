from pathlib import Path

import networkx as nx

from grapheinstein.core.graph import add_node, new_inventory_graph
from grapheinstein.core.references import (
    find_referenced_targets,
    unique_basename_targets,
    add_reference_edges,
)


def test_whole_token_match_and_substring_negative():
    basename_to_id = {"main.py": "src/main.py", "main": "main"}
    text = "See main.py and also domain for context."
    targets = find_referenced_targets(text, basename_to_id, source_id="README.md")
    assert "src/main.py" in targets
    # `main` must not match inside `main.py` or `domain`
    assert "main" not in targets


def test_substring_inside_identifier_no_match():
    basename_to_id = {"main": "bin/main"}
    text = "calling domain() helper"
    targets = find_referenced_targets(text, basename_to_id, source_id="a.py")
    assert targets == set()


def test_ambiguous_basename_skipped():
    graph = nx.DiGraph()
    add_node(graph, "a/util.py", "file")
    add_node(graph, "b/util.py", "file")
    add_node(graph, "readme.md", "file")
    mapping = unique_basename_targets(graph)
    assert "util.py" not in mapping


def test_self_edge_skipped(tmp_path: Path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "a.py").write_text("mentions a.py here\n", encoding="utf-8")
    graph = new_inventory_graph(root)
    add_node(graph, "a.py", "file")
    add_reference_edges(graph, root)
    assert not graph.has_edge("a.py", "a.py")


def test_unique_mention_creates_references(tmp_path: Path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "README.md").write_text("See main.py please.\n", encoding="utf-8")
    (root / "main.py").write_text("print('hi')\n", encoding="utf-8")
    graph = new_inventory_graph(root)
    add_node(graph, "README.md", "file")
    add_node(graph, "main.py", "file")
    added = add_reference_edges(graph, root)
    assert added == 1
    assert graph.edges["README.md", "main.py"]["type"] == "references"
    assert graph.edges["README.md", "main.py"]["provenance"] == "extracted"
