from pathlib import Path

from grapheinstein.core.graph import add_node, new_inventory_graph
from grapheinstein.core.parsers.media_ocr import merge_media_ocr


def test_ocr_injectable_engine(tmp_path: Path):
    root = tmp_path
    (root / "a.png").write_bytes(b"fake")
    (root / "blank.png").write_bytes(b"fake")
    graph = new_inventory_graph(root)
    add_node(graph, "a.png", "file")
    add_node(graph, "blank.png", "file")

    def extract(path: Path) -> str:
        if path.name == "a.png":
            return "Sign in with SSO"
        return ""

    skips = merge_media_ocr(graph, root, extract_text=extract)
    assert skips == 0
    texts = [n for n, a in graph.nodes(data=True) if a.get("type") == "media_text"]
    assert len(texts) == 1
    assert "a.png::media_text::1" in graph
    assert graph.edges["a.png::media_text::1", "a.png"]["type"] == "section_of"


def test_ocr_failure_increments_skip(tmp_path: Path):
    root = tmp_path
    (root / "bad.png").write_bytes(b"x")
    graph = new_inventory_graph(root)
    add_node(graph, "bad.png", "file")

    def boom(_path: Path) -> str:
        raise RuntimeError("ocr down")

    skips = merge_media_ocr(graph, root, extract_text=boom)
    assert skips == 1
    assert not any(a.get("type") == "media_text" for _, a in graph.nodes(data=True))
