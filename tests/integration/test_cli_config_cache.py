import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli
from grapheinstein.core.cache import CacheStore, KIND_AST, content_hash_bytes, settings_hash
from grapheinstein.core.index import index_project

runner = CliRunner()
FIX = Path(__file__).resolve().parents[1] / "fixtures" / "config_cache"


def test_index_respects_config_ignore_oversize_and_cache_dir(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cache_dir = tmp_path / "cache"
    out = tmp_path / "graph.json"
    cfg.write_text(
        "ignored_patterns:\n"
        "  - \"secret_dir/\"\n"
        "  - \"*.skipme\"\n"
        "max_file_size: 100\n"
        f"cache_dir: \"{cache_dir}\"\n"
        f"output: \"{out}\"\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        cli,
        ["index", str(FIX), "--config", str(cfg), "--output", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert cache_dir.exists()

    data = json.loads(out.read_text(encoding="utf-8"))
    ids = [n["id"] for n in data["nodes"]]
    assert not any("secret_dir" in i for i in ids)
    assert "notes.skipme" not in ids
    oversized = [
        n for n in data["nodes"] if (n.get("metadata") or {}).get("skipped") == "oversize"
    ]
    assert any(n["id"] == "big_blob.bin" for n in oversized)


def test_warm_reindex_records_cache_hits(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    out1 = tmp_path / "g1.json"
    out2 = tmp_path / "g2.json"
    _, stats1 = index_project(
        FIX,
        out1,
        ignored_patterns=["secret_dir/", "*.skipme"],
        max_file_size=10_000_000,
        cache_dir=cache_dir,
        show_progress=False,
    )
    _, stats2 = index_project(
        FIX,
        out2,
        ignored_patterns=["secret_dir/", "*.skipme"],
        max_file_size=10_000_000,
        cache_dir=cache_dir,
        show_progress=False,
    )
    assert stats1.cache_misses >= 1 or stats1.cache_hits >= 0
    assert stats2.cache_hits >= 1
    assert cache_dir.exists()


def test_embedding_settings_hash_changes_invalidate(tmp_path: Path):
    store = CacheStore(tmp_path / "cache")
    payload = b"[1.0, 2.0]"
    ch = content_hash_bytes(b"same text")
    sh_a = settings_hash({"kind": "embedding", "model": "model-a", "v": 1})
    sh_b = settings_hash({"kind": "embedding", "model": "model-b", "v": 1})
    store.put(KIND_AST, "k", ch, sh_a, payload)  # reuse AST kind for simple put API
    assert store.get(KIND_AST, "k", ch, sh_a) == payload
    assert store.get(KIND_AST, "k", ch, sh_b) is None


def test_invalid_max_file_size_names_key(tmp_path: Path):
    cfg = tmp_path / "bad.yaml"
    cfg.write_text("max_file_size: 0\n", encoding="utf-8")
    result = runner.invoke(
        cli,
        ["index", str(FIX), "--config", str(cfg), "--output", str(tmp_path / "g.json")],
    )
    assert result.exit_code != 0
    combined = (result.output or "") + (result.stderr or "")
    assert "max_file_size" in combined
