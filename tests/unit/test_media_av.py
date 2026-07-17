from pathlib import Path

from grapheinstein.core.graph import add_node, new_inventory_graph
from grapheinstein.core.parsers.media_av import Segment, TranscriptionResult, merge_media_av


def test_av_injectable_transcribe(tmp_path: Path):
    root = tmp_path
    (root / "talk.wav").write_bytes(b"RIFF")
    graph = new_inventory_graph(root)
    add_node(graph, "talk.wav", "file")

    def transcribe(_path: Path) -> TranscriptionResult:
        return TranscriptionResult(
            segments=[Segment(0.0, 2.0, "First install the package with pip.")],
            duration=2.0,
        )

    skips = merge_media_av(graph, root, transcribe=transcribe)
    assert skips == 0
    chunks = [n for n, a in graph.nodes(data=True) if a.get("type") == "transcript_chunk"]
    assert len(chunks) == 1
    assert graph.edges[chunks[0], "talk.wav"]["type"] == "section_of"


def test_av_failure_skip(tmp_path: Path):
    root = tmp_path
    (root / "bad.mp3").write_bytes(b"x")
    graph = new_inventory_graph(root)
    add_node(graph, "bad.mp3", "file")

    def boom(_path: Path) -> TranscriptionResult:
        raise RuntimeError("decode fail")

    assert merge_media_av(graph, root, transcribe=boom) == 1
