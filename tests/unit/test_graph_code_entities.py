from pathlib import Path

from grapheinstein.core.graph import (
    add_code_entity,
    add_defines_edge,
    code_entity_id,
    new_inventory_graph,
    add_node,
)


def test_code_entity_id_and_metadata():
    graph = new_inventory_graph(Path("/tmp/p"))
    add_node(graph, "a.py", "file")
    nid = add_code_entity(
        graph,
        file_id="a.py",
        kind="function",
        name="foo",
        start_line=3,
        language="python",
    )
    assert nid == code_entity_id("a.py", "function", "foo", 3)
    assert graph.nodes[nid]["type"] == "function"
    meta = graph.nodes[nid]["metadata"]
    assert meta["name"] == "foo"
    assert meta["file"] == "a.py"
    assert meta["start_line"] == 3
    assert meta["language"] == "python"
    assert add_defines_edge(graph, "a.py", nid) is True
    assert graph.edges["a.py", nid]["type"] == "defines"
    assert graph.edges["a.py", nid]["provenance"] == "extracted"
