from pathlib import Path

import networkx as nx

from grapheinstein.core.graph import add_node, new_inventory_graph
from grapheinstein.core.references import (
    add_reference_edges,
    find_referenced_targets,
    unique_basename_targets,
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


def test_oversize_skipped_for_references(tmp_path: Path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "big.py").write_text("See small.py please.\n", encoding="utf-8")
    (root / "small.py").write_text("x=1\n", encoding="utf-8")
    graph = new_inventory_graph(root)
    add_node(graph, "big.py", "file", metadata={"skipped": "oversize", "size_bytes": 99999})
    add_node(graph, "small.py", "file")
    added = add_reference_edges(graph, root)
    assert added == 0
    assert not graph.has_edge("big.py", "small.py")


def test_code_only_skips_non_code_sources(tmp_path: Path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "page.html").write_text("See util.py please.\n", encoding="utf-8")
    (root / "util.py").write_text("x=1\n", encoding="utf-8")
    (root / "app.py").write_text("See util.py please.\n", encoding="utf-8")
    graph = new_inventory_graph(root)
    add_node(graph, "page.html", "file")
    add_node(graph, "util.py", "file")
    add_node(graph, "app.py", "file")
    added = add_reference_edges(graph, root, code_only=True)
    assert added == 1
    assert graph.has_edge("app.py", "util.py")
    assert not graph.has_edge("page.html", "util.py")


def test_max_reference_scan_bytes_cap(tmp_path: Path):
    root = tmp_path / "proj"
    root.mkdir()
    # Mention only after the cap
    (root / "src.py").write_text("x" * 50 + "\nother.py\n", encoding="utf-8")
    (root / "other.py").write_text("y=1\n", encoding="utf-8")
    graph = new_inventory_graph(root)
    add_node(graph, "src.py", "file")
    add_node(graph, "other.py", "file")
    added = add_reference_edges(graph, root, max_reference_scan_bytes=40)
    assert added == 0
    # Within cap
    (root / "src.py").write_text("other.py\n" + "x" * 50, encoding="utf-8")
    graph2 = new_inventory_graph(root)
    add_node(graph2, "src.py", "file")
    add_node(graph2, "other.py", "file")
    added2 = add_reference_edges(graph2, root, max_reference_scan_bytes=40)
    assert added2 == 1
    assert graph2.has_edge("src.py", "other.py")
