from pathlib import Path

from grapheinstein.core.graph import add_media_text, add_node, new_inventory_graph
from grapheinstein.core.parsers.media_link import link_by_content


def test_content_no_hit(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, "a.png", "file")
    add_node(graph, "b.py", "file")
    add_media_text(graph, file_id="a.png", text="zzzz unique gibberish xyzzy")
    assert link_by_content(graph, min_overlap=3) == 0


def test_content_ambiguous_skip(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, "a.png", "file")
    add_node(graph, "one.py", "file")
    add_node(graph, "two.py", "file")
    # Both files share stem tokens that will also appear in OCR text via stem tokens
    # Use headings with identical distinctive tokens so two candidates clear threshold
    from grapheinstein.core.graph import add_heading

    add_heading(
        graph,
        file_id="one.py",
        name="alpha beta gamma delta",
        source="markdown",
        start_line=1,
    )
    add_heading(
        graph,
        file_id="two.py",
        name="alpha beta gamma delta",
        source="markdown",
        start_line=1,
    )
    add_media_text(graph, file_id="a.png", text="alpha beta gamma delta epsilon")
    assert link_by_content(graph, min_overlap=3) == 0
