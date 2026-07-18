"""Local, content-addressed cache for parse/chunk/embedding artifacts.

Layout under a resolved ``cache_dir``::

    {root}/index.sqlite       -- metadata: kind, key, content_hash, settings_hash, blob_path, ...
    {root}/blobs/{aa}/{hash}  -- opaque payload files, named by SHA-256 of their own bytes

A cache hit requires an exact match on ``(kind, key, content_hash, settings_hash)``.
Any other combination (missing row, hash mismatch, unreadable/corrupt blob) is a miss,
so callers can safely recompute and ``put`` a fresh value without failing the run.
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import sqlite3
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger

KIND_AST = "ast"
KIND_CHUNK = "chunk"
KIND_EMBEDDING = "embedding"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache_entries (
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    settings_hash TEXT NOT NULL,
    blob_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    PRIMARY KEY (kind, key)
);
"""


class CacheError(Exception):
    """Raised for unrecoverable cache I/O failures (disk full, permission denied, ...)."""


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    corrupt_recovered: int = 0


def content_hash_bytes(data: bytes) -> str:
    """SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def content_hash_text(text: str) -> str:
    """SHA-256 hex digest of UTF-8 encoded text."""
    return content_hash_bytes(text.encode("utf-8"))


def settings_hash(obj: dict[str, Any]) -> str:
    """SHA-256 hex digest of a stable (sorted-key) JSON encoding of ``obj``."""
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return content_hash_text(canonical)


def pickle_dumps(obj: Any) -> bytes:
    return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)


def pickle_loads(data: bytes) -> Any:
    return pickle.loads(data)


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


class CacheStore:
    """SQLite index + content-addressed blob files under ``root``."""

    def __init__(self, root: Path):
        self.root = Path(root).expanduser()
        self.db_path = self.root / "index.sqlite"
        self.blobs_dir = self.root / "blobs"
        self._stats = CacheStats()
        self._conn: sqlite3.Connection | None = None

    def __enter__(self) -> CacheStore:
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def _ensure_root(self) -> None:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            self.blobs_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CacheError(f"Cannot create cache directory {self.root}: {exc}") from exc

    def _connect(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        self._ensure_root()
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(_SCHEMA)
            conn.commit()
        except sqlite3.Error as exc:
            raise CacheError(f"Cannot open cache database {self.db_path}: {exc}") from exc
        self._conn = conn
        return conn

    def _blob_path(self, payload_hash: str) -> Path:
        return self.blobs_dir / payload_hash[:2] / payload_hash

    def _delete_row(self, kind: str, key: str) -> None:
        try:
            conn = self._connect()
            conn.execute("DELETE FROM cache_entries WHERE kind = ? AND key = ?", (kind, key))
            conn.commit()
        except sqlite3.Error as exc:
            logger.warning("Could not remove stale cache row {}/{}: {}", kind, key, exc)

    def get(self, kind: str, key: str, content_hash: str, settings_hash: str) -> bytes | None:
        """Return the cached payload, or None on miss/corruption (never raises)."""
        try:
            conn = self._connect()
            row = conn.execute(
                "SELECT content_hash, settings_hash, blob_path FROM cache_entries "
                "WHERE kind = ? AND key = ?",
                (kind, key),
            ).fetchone()
        except (sqlite3.Error, CacheError) as exc:
            logger.warning("Cache index read failed for {}/{}: {}", kind, key, exc)
            self._stats.misses += 1
            return None

        if row is None:
            self._stats.misses += 1
            return None

        row_content_hash, row_settings_hash, blob_rel = row
        if row_content_hash != content_hash or row_settings_hash != settings_hash:
            self._stats.misses += 1
            return None

        blob_path = self.root / blob_rel
        try:
            payload = blob_path.read_bytes()
        except OSError as exc:
            logger.warning(
                "Cache blob missing/unreadable for {}/{} ({}) — recomputing", kind, key, exc
            )
            self._delete_row(kind, key)
            self._stats.corrupt_recovered += 1
            return None

        if content_hash_bytes(payload) != blob_path.name:
            logger.warning("Cache blob corrupted for {}/{} — recomputing", kind, key)
            self._delete_row(kind, key)
            self._stats.corrupt_recovered += 1
            return None

        self._stats.hits += 1
        return payload

    def put(self, kind: str, key: str, content_hash: str, settings_hash: str, payload: bytes) -> None:
        """Write (or replace) the cache entry for ``(kind, key)``."""
        self._ensure_root()
        payload_hash = content_hash_bytes(payload)
        blob_path = self._blob_path(payload_hash)
        if not blob_path.exists():
            try:
                blob_path.parent.mkdir(parents=True, exist_ok=True)
                fd, tmp_name = tempfile.mkstemp(
                    dir=str(blob_path.parent), prefix=".tmp-", suffix=".blob"
                )
                try:
                    with os.fdopen(fd, "wb") as fh:
                        fh.write(payload)
                        fh.flush()
                        os.fsync(fh.fileno())
                    os.replace(tmp_name, blob_path)
                except OSError:
                    try:
                        os.unlink(tmp_name)
                    except OSError:
                        pass
                    raise
            except OSError as exc:
                raise CacheError(
                    f"Cannot write cache blob under {self.blobs_dir}: {exc}"
                ) from exc

        blob_rel = blob_path.relative_to(self.root).as_posix()
        try:
            conn = self._connect()
            conn.execute(
                "INSERT INTO cache_entries "
                "(kind, key, content_hash, settings_hash, blob_path, created_at, size_bytes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(kind, key) DO UPDATE SET "
                "content_hash=excluded.content_hash, "
                "settings_hash=excluded.settings_hash, "
                "blob_path=excluded.blob_path, "
                "created_at=excluded.created_at, "
                "size_bytes=excluded.size_bytes",
                (kind, key, content_hash, settings_hash, blob_rel, _utcnow_iso(), len(payload)),
            )
            conn.commit()
        except (sqlite3.Error, CacheError) as exc:
            raise CacheError(f"Cannot write cache index entry {kind}/{key}: {exc}") from exc

    def stats(self) -> CacheStats:
        return CacheStats(
            hits=self._stats.hits,
            misses=self._stats.misses,
            corrupt_recovered=self._stats.corrupt_recovered,
        )


def get_or_compute(
    store: CacheStore | None,
    kind: str,
    key: str,
    content_hash: str,
    settings_hash: str,
    compute_fn: Callable[[], Any],
) -> Any:
    """Return a cached (unpickled) value, or compute, cache, and return it.

    Passing ``store=None`` disables caching transparently (always computes).
    """
    if store is None:
        return compute_fn()

    cached = store.get(kind, key, content_hash, settings_hash)
    if cached is not None:
        try:
            return pickle_loads(cached)
        except (pickle.PickleError, EOFError, AttributeError, ImportError, ValueError) as exc:
            logger.warning(
                "Cache payload for {}/{} failed to deserialize: {} — recomputing", kind, key, exc
            )
            store._stats.hits = max(0, store._stats.hits - 1)
            store._stats.corrupt_recovered += 1

    value = compute_fn()
    try:
        store.put(kind, key, content_hash, settings_hash, pickle_dumps(value))
    except CacheError as exc:
        logger.warning("Cache write failed for {}/{}: {}", kind, key, exc)
    return value


__all__ = [
    "KIND_AST",
    "KIND_CHUNK",
    "KIND_EMBEDDING",
    "CacheError",
    "CacheStats",
    "CacheStore",
    "content_hash_bytes",
    "content_hash_text",
    "get_or_compute",
    "pickle_dumps",
    "pickle_loads",
    "settings_hash",
]
