from pathlib import Path

from grapheinstein.core.graph import (
    add_media_text,
    add_node,
    add_related_to_edge,
    add_section_of_edge,
    add_transcript_chunk,
    media_text_id,
    new_inventory_graph,
    transcript_chunk_id,
)


def test_media_ids():
    assert media_text_id("a.png", 1) == "a.png::media_text::1"
    assert transcript_chunk_id("a.wav", 2) == "a.wav::transcript_chunk::2"


def test_add_media_text_and_section_of(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, "a.png", "file")
    mid = add_media_text(graph, file_id="a.png", text="Sign in with SSO")
    assert add_section_of_edge(graph, mid, "a.png")
    assert graph.nodes[mid]["type"] == "media_text"
    assert graph.nodes[mid]["metadata"]["text"] == "Sign in with SSO"
    assert graph.edges[mid, "a.png"]["provenance"] == "extracted"


def test_add_transcript_chunk(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, "a.wav", "file")
    cid = add_transcript_chunk(
        graph,
        file_id="a.wav",
        text="hello there",
        start_sec=0.0,
        end_sec=1.2,
        ordinal=1,
    )
    assert add_section_of_edge(graph, cid, "a.wav")
    assert graph.nodes[cid]["metadata"]["start_sec"] == 0.0
    assert graph.nodes[cid]["metadata"]["end_sec"] == 1.2


def test_related_to_inferred(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, "a.png", "file")
    add_node(graph, "a.py", "file")
    assert add_related_to_edge(graph, "a.png", "a.py", reason="filename")
    assert graph.edges["a.png", "a.py"]["type"] == "related_to"
    assert graph.edges["a.png", "a.py"]["provenance"] == "inferred"
    assert graph.edges["a.png", "a.py"]["reason"] == "filename"
    assert add_related_to_edge(graph, "a.png", "a.py") is False
