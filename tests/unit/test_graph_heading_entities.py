from pathlib import Path

from grapheinstein.core.graph import (
    add_heading,
    add_mentions_edge,
    add_node,
    add_section_of_edge,
    heading_entity_id,
    new_inventory_graph,
    slugify_heading,
)


def test_slugify_and_heading_id():
    assert slugify_heading("Installation Steps") == "installation-steps"
    assert slugify_heading("!!!") == "untitled"
    assert heading_entity_id("docs/a.md", "Install", "3") == "docs/a.md::heading::install::3"


def test_add_heading_and_section_of(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, "docs/a.md", "file")
    h1 = add_heading(
        graph, file_id="docs/a.md", name="Guide", source="markdown", start_line=1, level=1
    )
    h2 = add_heading(
        graph,
        file_id="docs/a.md",
        name="Install",
        source="markdown",
        start_line=3,
        level=2,
    )
    assert add_section_of_edge(graph, h1, "docs/a.md")
    assert add_section_of_edge(graph, h2, h1)
    assert graph.nodes[h1]["type"] == "heading"
    assert graph.nodes[h1]["metadata"]["name"] == "Guide"
    assert graph.edges[h2, h1]["type"] == "section_of"
    assert graph.edges[h2, h1]["provenance"] == "extracted"


def test_mentions_edge(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, "docs/a.md", "file")
    add_node(graph, "README.md", "file")
    h = add_heading(
        graph, file_id="docs/a.md", name="Install", source="markdown", start_line=3, level=2
    )
    assert add_mentions_edge(graph, h, "README.md")
    assert graph.edges[h, "README.md"]["type"] == "mentions"
    assert add_mentions_edge(graph, h, "README.md") is False
