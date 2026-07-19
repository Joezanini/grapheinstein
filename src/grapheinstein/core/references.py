"""Whole-token basename mention extraction for references edges."""

from __future__ import annotations

import re
import time
from collections import defaultdict
from pathlib import Path

import networkx as nx
from loguru import logger

from grapheinstein.core.graph import add_references_edge
from grapheinstein.core.parsers.registry import EXTENSION_MAP
from grapheinstein.utils import IndexTimeoutError

# Path-token characters: lookarounds prevent `main` matching inside `main.py`
_TOKEN_CHAR = r"A-Za-z0-9._+\-"
CODE_SUFFIXES = frozenset(EXTENSION_MAP.keys())
DEFAULT_MAX_REFERENCE_SCAN_BYTES = 262_144
_TIMEOUT_CHECK_EVERY = 32


def _whole_token_pattern(basename: str) -> re.Pattern[str]:
    escaped = re.escape(basename)
    return re.compile(rf"(?<![{_TOKEN_CHAR}]){escaped}(?![{_TOKEN_CHAR}])")


def unique_basename_targets(graph: nx.DiGraph) -> dict[str, str]:
    """
    Map basename -> file node id for basenames that appear exactly once.
    Ambiguous basenames are omitted.
    """
    by_base: dict[str, list[str]] = defaultdict(list)
    for node_id, attrs in graph.nodes(data=True):
        if attrs.get("type") != "file":
            continue
        if node_id == ".":
            continue
        base = Path(node_id).name
        by_base[base].append(node_id)
    return {base: ids[0] for base, ids in by_base.items() if len(ids) == 1}


def find_referenced_targets(
    text: str,
    basename_to_id: dict[str, str],
    *,
    source_id: str,
) -> set[str]:
    """Return target node ids mentioned as whole tokens in text (excluding self)."""
    targets: set[str] = set()
    for basename in sorted(basename_to_id.keys(), key=len, reverse=True):
        target_id = basename_to_id[basename]
        if target_id == source_id:
            continue
        if _whole_token_pattern(basename).search(text):
            targets.add(target_id)
    return targets


def is_reference_scan_eligible(
    node_id: str,
    attrs: dict,
    *,
    code_only: bool = False,
) -> bool:
    """Whether a file node's contents may be scanned for basename mentions."""
    if attrs.get("type") != "file":
        return False
    meta = attrs.get("metadata") or {}
    if meta.get("symlink"):
        return False
    if meta.get("skipped") == "oversize":
        return False
    if code_only and Path(node_id).suffix.lower() not in CODE_SUFFIXES:
        return False
    return True


def _read_capped_text(path: Path, max_bytes: int) -> str | None:
    try:
        with path.open("rb") as handle:
            raw = handle.read(max_bytes if max_bytes > 0 else None)
    except OSError as exc:
        logger.warning("Skipping unreadable file for references {}: {}", path, exc)
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        logger.debug("Skipping non-UTF-8 file for references: {}", path)
        return None


def add_reference_edges(
    graph: nx.DiGraph,
    project_root: Path,
    *,
    code_only: bool = False,
    max_reference_scan_bytes: int = DEFAULT_MAX_REFERENCE_SCAN_BYTES,
    deadline_monotonic: float | None = None,
    on_timeout_phase: str = "references",
) -> int:
    """
    Scan eligible UTF-8 text files for whole-token basename mentions and add
    references edges. Returns the number of new references edges added.
    """
    basename_to_id = unique_basename_targets(graph)
    if not basename_to_id:
        return 0

    added = 0
    root = project_root.resolve()
    checked = 0
    for node_id, attrs in list(graph.nodes(data=True)):
        if deadline_monotonic is not None:
            checked += 1
            if checked % _TIMEOUT_CHECK_EVERY == 0 and time.monotonic() > deadline_monotonic:
                raise IndexTimeoutError(
                    f"Indexing timed out during {on_timeout_phase}",
                    phase=on_timeout_phase,
                )
        if not is_reference_scan_eligible(node_id, attrs, code_only=code_only):
            continue
        path = root / node_id
        text = _read_capped_text(path, int(max_reference_scan_bytes))
        if text is None:
            continue

        for target_id in find_referenced_targets(text, basename_to_id, source_id=node_id):
            if add_references_edge(graph, node_id, target_id):
                added += 1
    return added
