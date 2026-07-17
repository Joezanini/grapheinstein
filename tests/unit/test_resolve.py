from pathlib import Path

import networkx as nx

from grapheinstein.core.graph import add_code_entity, add_node, new_inventory_graph
from grapheinstein.core.parsers.extract import ImportFact, CallFact
from grapheinstein.core.parsers.resolve import apply_edges, apply_entities, resolve_import_target
from grapheinstein.core.parsers.extract import CodeEntity


def test_resolve_unique_import_to_symbol():
    graph = new_inventory_graph(Path("/tmp/p"))
    add_node(graph, "src/app.py", "file")
    add_node(graph, "src/main.py", "file")
    add_code_entity(
        graph,
        file_id="src/app.py",
        kind="function",
        name="greet",
        start_line=1,
        language="python",
    )
    fact = ImportFact(module="app", names=["greet"])
    target = resolve_import_target(graph, fact, "src/main.py", "python")
    assert target == "src/app.py::function::greet::1"


def test_resolve_ambiguous_call_skipped():
    graph = new_inventory_graph(Path("/tmp/p"))
    add_node(graph, "a.py", "file")
    add_node(graph, "b.py", "file")
    add_code_entity(graph, file_id="a.py", kind="function", name="f", start_line=1, language="python")
    add_code_entity(graph, file_id="b.py", kind="function", name="f", start_line=1, language="python")
    apply_entities(
        graph,
        file_id="c.py",
        language="python",
        entities=[],
    )
    add_node(graph, "c.py", "file")
    before = graph.number_of_edges()
    apply_edges(
        graph,
        file_id="c.py",
        language="python",
        imports=[],
        calls=[CallFact(name="f", start_line=2, enclosing=None)],
        enclosing_map={},
    )
    # Ambiguous name → no calls edge
    assert graph.number_of_edges() == before


def test_external_import_omitted():
    graph = new_inventory_graph(Path("/tmp/p"))
    add_node(graph, "main.py", "file")
    fact = ImportFact(module="requests", names=[])
    assert resolve_import_target(graph, fact, "main.py", "python") is None
