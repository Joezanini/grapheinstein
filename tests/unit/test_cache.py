import pickle
from pathlib import Path

from grapheinstein.core.cache import (
    KIND_AST,
    KIND_EMBEDDING,
    CacheStore,
    content_hash_bytes,
    get_or_compute,
    settings_hash,
)


def test_cache_hit_miss_and_settings_invalidation(tmp_path: Path):
    store = CacheStore(tmp_path / "cache")
    content = b"hello"
    ch = content_hash_bytes(content)
    sh = settings_hash({"model": "a", "v": 1})
    assert store.get(KIND_AST, "src/a.py", ch, sh) is None
    assert store.stats().misses == 1

    store.put(KIND_AST, "src/a.py", ch, sh, pickle.dumps({"ok": True}))
    hit = store.get(KIND_AST, "src/a.py", ch, sh)
    assert hit is not None
    assert pickle.loads(hit) == {"ok": True}
    assert store.stats().hits == 1

    other = settings_hash({"model": "b", "v": 1})
    assert store.get(KIND_AST, "src/a.py", ch, other) is None


def test_corrupt_blob_recovers(tmp_path: Path):
    store = CacheStore(tmp_path / "cache")
    ch = content_hash_bytes(b"x")
    sh = settings_hash({"k": 1})
    store.put(KIND_EMBEDDING, "t1", ch, sh, b'{"v":[1.0]}')
    # Corrupt the blob file on disk
    blob_files = list((tmp_path / "cache" / "blobs").rglob("*"))
    blob_files = [p for p in blob_files if p.is_file()]
    assert blob_files
    blob_files[0].write_bytes(b"not-valid-for-this-test")
    # Truncate/replace with empty so size mismatch or unreadable content
    blob_files[0].write_bytes(b"")

    assert store.get(KIND_EMBEDDING, "t1", ch, sh) is None
    assert store.stats().corrupt_recovered >= 1


def test_get_or_compute(tmp_path: Path):
    store = CacheStore(tmp_path / "cache")
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return [0.1, 0.2]

    ch = content_hash_bytes(b"text")
    sh = settings_hash({"model": "m"})
    a = get_or_compute(store, KIND_EMBEDDING, "k", ch, sh, compute)
    b = get_or_compute(store, KIND_EMBEDDING, "k", ch, sh, compute)
    assert a == b == [0.1, 0.2]
    assert calls["n"] == 1
