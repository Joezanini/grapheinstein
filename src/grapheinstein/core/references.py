"""Whole-token basename mention extraction for references edges."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import networkx as nx
from loguru import logger

from grapheinstein.core.graph import add_references_edge

# Path-token characters: lookarounds prevent `main` matching inside `main.py`
_TOKEN_CHAR = r"A-Za-z0-9._+\-"


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


def add_reference_edges(graph: nx.DiGraph, project_root: Path) -> int:
    """
    Scan UTF-8 text files for whole-token basename mentions and add references edges.
    Returns the number of new references edges added.
    """
    basename_to_id = unique_basename_targets(graph)
    if not basename_to_id:
        return 0

    added = 0
    root = project_root.resolve()
    for node_id, attrs in list(graph.nodes(data=True)):
        if attrs.get("type") != "file":
            continue
        if attrs.get("metadata", {}).get("symlink"):
            continue
        path = root / node_id
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.debug("Skipping non-UTF-8 file for references: {}", node_id)
            continue
        except OSError as exc:
            logger.warning("Skipping unreadable file for references {}: {}", node_id, exc)
            continue

        for target_id in find_referenced_targets(text, basename_to_id, source_id=node_id):
            if add_references_edge(graph, node_id, target_id):
                added += 1
    return added
