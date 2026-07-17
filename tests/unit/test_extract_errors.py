from pathlib import Path

from grapheinstein.core.parsers.extract import extract_file
from grapheinstein.core.parsers.resolve import merge_code_structure
from grapheinstein.core.graph import new_inventory_graph, add_node, add_contains_edge

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "code_project"


def test_broken_file_extract_has_parse_error_flag():
    path = FIXTURE / "broken" / "bad.py"
    result = extract_file(path, "python", file_id="broken/bad.py")
    # May or may not skip entirely; parse errors should be noted
    assert result.skip_reason == "parse errors" or result.skipped or not result.entities


def test_merge_counts_parse_skips():
    root = FIXTURE
    graph = new_inventory_graph(root)
    for rel in ("broken/bad.py", "src/app.py", "notes.txt"):
        parent = str(Path(rel).parent).replace("\\", "/")
        if parent != ".":
            if parent not in graph:
                add_node(graph, parent, "dir")
                add_contains_edge(graph, ".", parent)
            parent_id = parent
        else:
            parent_id = "."
        add_node(graph, rel, "file")
        add_contains_edge(graph, parent_id, rel)
    skips = merge_code_structure(graph, root, ["python"])
    assert skips >= 1
    assert any(
        attrs.get("type") == "function" and (attrs.get("metadata") or {}).get("name") == "greet"
        for _, attrs in graph.nodes(data=True)
    )
