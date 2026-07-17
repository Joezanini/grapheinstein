from pathlib import Path

from loguru import logger

from grapheinstein.core.graph import add_node, new_inventory_graph
from grapheinstein.core.parsers.media_av import Segment, TranscriptionResult, merge_media_av
from grapheinstein.core.parsers.media_ocr import LONG_FILE_BYTES, merge_media_ocr


def test_long_file_size_warn_ocr(tmp_path: Path, caplog):
    root = tmp_path
    big = root / "huge.png"
    # Avoid writing 100MB: temporarily lower threshold via monkeypatch in caller
    big.write_bytes(b"x" * 10)
    graph = new_inventory_graph(root)
    add_node(graph, "huge.png", "file")

    messages: list[str] = []

    def sink(message):
        messages.append(message.record["message"])

    handler_id = logger.add(sink, level="WARNING")
    try:
        import grapheinstein.core.parsers.media_ocr as ocr_mod

        original = ocr_mod.LONG_FILE_BYTES
        ocr_mod.LONG_FILE_BYTES = 5
        try:
            merge_media_ocr(graph, root, extract_text=lambda p: "hi")
        finally:
            ocr_mod.LONG_FILE_BYTES = original
    finally:
        logger.remove(handler_id)

    assert any("Long media file" in m and "huge.png" in m for m in messages)


def test_long_duration_warn_av(tmp_path: Path):
    root = tmp_path
    (root / "long.wav").write_bytes(b"RIFF")
    graph = new_inventory_graph(root)
    add_node(graph, "long.wav", "file")
    messages: list[str] = []

    def sink(message):
        messages.append(message.record["message"])

    handler_id = logger.add(sink, level="WARNING")
    try:

        def transcribe(_p: Path) -> TranscriptionResult:
            return TranscriptionResult(
                segments=[Segment(0.0, 1.0, "hi")],
                duration=900.0,
            )

        merge_media_av(graph, root, transcribe=transcribe)
    finally:
        logger.remove(handler_id)

    assert any("Long media file" in m and "long.wav" in m for m in messages)
    # Still produced a chunk (warn-and-continue)
    assert any(a.get("type") == "transcript_chunk" for _, a in graph.nodes(data=True))
