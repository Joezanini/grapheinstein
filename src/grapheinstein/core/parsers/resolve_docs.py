"""Resolve documentation link targets to graph nodes for mentions edges."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse

import networkx as nx

from grapheinstein.core.graph import (
    add_heading,
    add_mentions_edge,
    add_section_of_edge,
    slugify_heading,
)
from grapheinstein.core.parsers.docs import HeadingFact, LinkFact


def _build_heading_stack(
    graph: nx.DiGraph,
    *,
    file_id: str,
    headings: list[HeadingFact],
) -> list[str]:
    """Create heading nodes and section_of edges. Returns list of heading node ids."""
    ids: list[str] = []
    stack: list[tuple[int, str]] = []  # (level, node_id)
    for heading in headings:
        node_id = add_heading(
            graph,
            file_id=file_id,
            name=heading.name,
            source=heading.source,
            start_line=heading.start_line,
            level=heading.level,
        )
        while stack and stack[-1][0] >= heading.level:
            stack.pop()
        parent = stack[-1][1] if stack else file_id
        add_section_of_edge(graph, node_id, parent)
        stack.append((heading.level, node_id))
        ids.append(node_id)
    return ids


def _resolve_target(
    graph: nx.DiGraph,
    *,
    file_id: str,
    raw_target: str,
    project_root: Path,
) -> str | None:
    target = raw_target.strip()
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return None

    parsed = urlparse(target)
    path_part = unquote(parsed.path or "")
    fragment = unquote(parsed.fragment or "")

    # Pure fragment → heading in same file
    if target.startswith("#") or (not path_part and fragment):
        frag = fragment or target.lstrip("#")
        return _unique_heading_by_slug(graph, file_id=file_id, slug=slugify_heading(frag))

    # Resolve relative path against document directory
    base_dir = Path(file_id).parent
    candidate = (base_dir / path_part).as_posix() if path_part else file_id
    # Normalize . and ..
    parts: list[str] = []
    for part in candidate.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    rel = "/".join(parts) if parts else "."

    file_hits = [rel] if rel in graph and graph.nodes[rel].get("type") == "file" else []
    # Also try basename uniqueness among indexed files
    if not file_hits and path_part and "/" not in path_part.rstrip("/"):
        name = Path(path_part).name
        matches = [
            n
            for n, attrs in graph.nodes(data=True)
            if attrs.get("type") == "file" and Path(n).name == name
        ]
        if len(matches) == 1:
            file_hits = matches

    if fragment and file_hits:
        heading = _unique_heading_by_slug(graph, file_id=file_hits[0], slug=slugify_heading(fragment))
        if heading:
            return heading
        # Fragment present but no heading — still allow file if unique
        return file_hits[0] if len(file_hits) == 1 else None

    if len(file_hits) == 1:
        return file_hits[0]
    return None


def _unique_heading_by_slug(graph: nx.DiGraph, *, file_id: str, slug: str) -> str | None:
    matches = []
    for node_id, attrs in graph.nodes(data=True):
        if attrs.get("type") != "heading":
            continue
        meta = attrs.get("metadata") or {}
        if meta.get("file") != file_id:
            continue
        if slugify_heading(str(meta.get("name", ""))) == slug:
            matches.append(node_id)
    if len(matches) == 1:
        return matches[0]
    return None


def resolve_and_emit_docs(
    graph: nx.DiGraph,
    *,
    file_id: str,
    headings: list[HeadingFact],
    links: list[LinkFact],
    project_root: Path,
) -> None:
    """Add heading nodes, section_of edges, and resolvable mentions for one doc file."""
    if file_id not in graph:
        return
    heading_ids = _build_heading_stack(graph, file_id=file_id, headings=headings)
    for link in links:
        resolved = _resolve_target(
            graph, file_id=file_id, raw_target=link.target, project_root=project_root
        )
        if not resolved:
            continue
        if link.section_index is not None and 0 <= link.section_index < len(heading_ids):
            source = heading_ids[link.section_index]
        else:
            source = file_id
        add_mentions_edge(graph, source, resolved)


__all__ = ["resolve_and_emit_docs"]
