from pathlib import Path

from grapheinstein.core.graph import (
    add_heading,
    add_media_text,
    add_node,
    new_inventory_graph,
)
from grapheinstein.core.parsers.media_link import (
    link_by_content,
    link_by_filename,
    merge_media_links,
)


def test_filename_unique_stem(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, "assets/login.png", "file")
    add_node(graph, "src/login.py", "file")
    assert link_by_filename(graph) == 1
    edge = graph.edges["assets/login.png", "src/login.py"]
    assert edge["type"] == "related_to"
    assert edge["provenance"] == "inferred"


def test_filename_ambiguous_skip(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, "assets/login.png", "file")
    add_node(graph, "src/login.py", "file")
    add_node(graph, "docs/login.md", "file")
    assert link_by_filename(graph) == 0


def test_content_overlap_unique(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, "assets/shot.png", "file")
    add_node(graph, "docs/install.md", "file")
    add_heading(
        graph,
        file_id="docs/install.md",
        name="Pip install grapheinstein package",
        source="markdown",
        start_line=1,
    )
    add_media_text(
        graph,
        file_id="assets/shot.png",
        text="pip install grapheinstein package instructions",
    )
    assert link_by_content(graph, min_overlap=3) >= 1
    assert merge_media_links(graph) >= 0
