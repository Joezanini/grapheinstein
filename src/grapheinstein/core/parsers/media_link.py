"""Inferred related_to edges from media to code/docs (filename + content)."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import networkx as nx

from grapheinstein.core.graph import add_related_to_edge

_TOKEN_RE = re.compile(r"[a-z0-9]{4,}", re.IGNORECASE)
CODE_DOC_TYPES = frozenset({"file", "heading", "function", "class", "method"})
CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".go",
        ".rs",
        ".c",
        ".cc",
        ".cpp",
        ".h",
        ".hpp",
        ".sql",
        ".md",
        ".markdown",
        ".txt",
        ".rst",
        ".rest",
        ".pdf",
    }
)
MEDIA_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
        ".tif",
        ".tiff",
        ".bmp",
        ".mp3",
        ".wav",
        ".m4a",
        ".flac",
        ".ogg",
        ".aac",
        ".mp4",
        ".mov",
        ".mkv",
        ".webm",
    }
)


def _is_media_file(node_id: str) -> bool:
    return Path(node_id).suffix.lower() in MEDIA_EXTENSIONS


def _is_code_or_doc_file(node_id: str) -> bool:
    return Path(node_id).suffix.lower() in CODE_EXTENSIONS


def unique_stem_targets(graph: nx.DiGraph) -> dict[str, str]:
    """Map lowercase stem → file id for unique stems among code/doc files."""
    by_stem: dict[str, list[str]] = defaultdict(list)
    for node_id, attrs in graph.nodes(data=True):
        if attrs.get("type") != "file":
            continue
        if not _is_code_or_doc_file(node_id):
            continue
        stem = Path(node_id).stem.lower()
        by_stem[stem].append(node_id)
    return {stem: ids[0] for stem, ids in by_stem.items() if len(ids) == 1}


def link_by_filename(graph: nx.DiGraph) -> int:
    """Create related_to edges from media files to unique stem-matched code/doc files."""
    targets = unique_stem_targets(graph)
    added = 0
    for node_id, attrs in list(graph.nodes(data=True)):
        if attrs.get("type") != "file":
            continue
        if not _is_media_file(node_id):
            continue
        stem = Path(node_id).stem.lower()
        target = targets.get(stem)
        if target is None or target == node_id:
            continue
        if add_related_to_edge(graph, node_id, target, reason="filename"):
            added += 1
    return added


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")}


def _node_text(attrs: dict) -> str:
    meta = attrs.get("metadata") or {}
    parts: list[str] = []
    for key in ("text", "name", "qualified_name"):
        val = meta.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val)
    return " ".join(parts)


def link_by_content(graph: nx.DiGraph, *, min_overlap: int = 3) -> int:
    """
    Link media_text / transcript_chunk to unique target when token overlap is distinctive.
    Conservative: only link when exactly one candidate clears the threshold.
    """
    media_nodes: list[tuple[str, set[str]]] = []
    for node_id, attrs in graph.nodes(data=True):
        if attrs.get("type") not in {"media_text", "transcript_chunk"}:
            continue
        toks = _tokens(_node_text(attrs))
        if toks:
            media_nodes.append((node_id, toks))

    candidates: list[tuple[str, set[str]]] = []
    for node_id, attrs in graph.nodes(data=True):
        ntype = attrs.get("type")
        if ntype == "file" and _is_code_or_doc_file(node_id):
            # Prefer reading heading/code text already in graph; file body not scanned here
            continue
        if ntype in {"heading", "function", "class", "method"}:
            toks = _tokens(_node_text(attrs))
            if toks:
                candidates.append((node_id, toks))

    # Also index file nodes that have media-adjacent heading/code children already covered;
    # add file basenames as weak tokens
    for node_id, attrs in graph.nodes(data=True):
        if attrs.get("type") != "file" or not _is_code_or_doc_file(node_id):
            continue
        toks = _tokens(Path(node_id).stem.replace("_", " ").replace("-", " "))
        if toks:
            candidates.append((node_id, toks))

    added = 0
    for media_id, media_toks in media_nodes:
        hits: list[str] = []
        for cand_id, cand_toks in candidates:
            if cand_id == media_id:
                continue
            overlap = len(media_toks & cand_toks)
            if overlap >= min_overlap:
                hits.append(cand_id)
        # Deduplicate while preserving order
        uniq: list[str] = []
        seen: set[str] = set()
        for h in hits:
            if h not in seen:
                seen.add(h)
                uniq.append(h)
        if len(uniq) == 1:
            if add_related_to_edge(graph, media_id, uniq[0], reason="content"):
                added += 1
    return added


def merge_media_links(graph: nx.DiGraph) -> int:
    """Emit inferred related_to edges. Returns number of new edges."""
    return link_by_filename(graph) + link_by_content(graph)
