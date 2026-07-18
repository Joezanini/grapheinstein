from pathlib import Path

from grapheinstein.core.index import build_inventory_graph, discover_paths

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "config_cache"


def test_config_ignored_patterns_exclude_secret_dir():
    paths = discover_paths(FIX, ignored_patterns=["secret_dir/", "*.skipme"])
    ids = {rel for rel, _typ, _meta in paths}
    assert "src/main.py" in ids
    assert not any(i.startswith("secret_dir") for i in ids)
    assert "notes.skipme" not in ids
    assert not any(i.startswith("ignored_by_git") for i in ids)


def test_oversize_marked_on_inventory():
    graph = build_inventory_graph(
        FIX,
        ignored_patterns=["secret_dir/", "*.skipme"],
        max_file_size=100,
        cache_dir=None,
        show_progress=False,
    )
    assert graph.nodes["big_blob.bin"]["metadata"].get("skipped") == "oversize"
    assert graph.nodes["big_blob.bin"]["metadata"].get("size_bytes") == 250
    assert graph.graph.get("skipped_oversize", 0) >= 1
    # No structure children from oversize file
    children = [
        t
        for s, t, d in graph.edges(data=True)
        if s == "big_blob.bin" or (isinstance(t, str) and t.startswith("big_blob.bin#"))
    ]
    assert not children
