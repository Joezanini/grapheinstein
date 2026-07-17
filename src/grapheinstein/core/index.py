"""Ignore-aware project discovery and inventory indexing."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import pathspec
from loguru import logger

from grapheinstein.core.graph import (
    add_contains_edge,
    add_node,
    ensure_directory_chain,
    new_inventory_graph,
    save_graph,
    stats_from_artifact,
    to_artifact_dict,
)
from grapheinstein.core.parsers import DEFAULT_LANGUAGES, merge_code_structure
from grapheinstein.core.parsers.docs import merge_docs_structure
from grapheinstein.core.parsers.pdf import merge_pdf_structure
from grapheinstein.core.references import add_reference_edges
from grapheinstein.utils import resolve_project_path


def load_gitignore_spec(project_root: Path) -> pathspec.PathSpec | None:
    gitignore = project_root / ".gitignore"
    if not gitignore.exists():
        return None
    try:
        lines = gitignore.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning(
            "Could not read .gitignore at {}: {} — continuing without ignores",
            gitignore,
            exc,
        )
        return None
    try:
        return pathspec.PathSpec.from_lines("gitignore", lines)
    except Exception as exc:  # noqa: BLE001 - best-effort ignore handling
        logger.warning(
            "Broken .gitignore at {}: {} — continuing without ignores",
            gitignore,
            exc,
        )
        return None


def _to_posix_relative(project_root: Path, path: Path) -> str:
    rel = path.relative_to(project_root).as_posix()
    return "." if rel == "." else rel


def _is_ignored(spec: pathspec.PathSpec | None, relative: str, *, is_dir: bool) -> bool:
    if spec is None or relative in {"", "."}:
        return False
    candidates = [relative]
    if is_dir and not relative.endswith("/"):
        candidates.append(relative + "/")
    return any(spec.match_file(candidate) for candidate in candidates)


def discover_paths(project_root: Path) -> list[tuple[str, str, dict[str, Any]]]:
    """
    Return list of (relative_id, type, metadata) for non-ignored files and directories.
    Always includes root "." as dir. Symlinks are type file with metadata.symlink=True
    and are not followed.
    """
    root = resolve_project_path(project_root)
    spec = load_gitignore_spec(root)
    found: dict[str, tuple[str, dict[str, Any]]] = {".": ("dir", {})}

    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name)
        except OSError as exc:
            logger.warning("Skipping unreadable directory {}: {}", current, exc)
            continue

        for entry in entries:
            if entry.name == ".git":
                continue
            rel = _to_posix_relative(root, entry)

            if entry.is_symlink():
                if _is_ignored(spec, rel, is_dir=False):
                    logger.debug("Ignoring {}", rel)
                    continue
                found[rel] = ("file", {"symlink": True})
                continue

            is_dir = entry.is_dir()
            if _is_ignored(spec, rel, is_dir=is_dir):
                logger.debug("Ignoring {}", rel)
                continue
            if is_dir:
                found[rel] = ("dir", {})
                stack.append(entry)
            elif entry.is_file():
                found[rel] = ("file", {})
            else:
                logger.debug("Skipping non-file/non-dir {}", rel)

    items = [(rel, typ, meta) for rel, (typ, meta) in found.items()]
    return sorted(items, key=lambda item: (0 if item[1] == "dir" else 1, item[0]))


def build_inventory_graph(
    project_root: Path,
    *,
    languages: Sequence[str] | None = None,
    include_docs: bool = False,
    include_pdfs: bool = False,
):
    root = resolve_project_path(project_root)
    graph = new_inventory_graph(root)
    for rel, node_type, metadata in discover_paths(root):
        if rel == ".":
            continue
        if node_type == "dir":
            ensure_directory_chain(graph, rel)
        else:
            parent = Path(rel).parent.as_posix()
            if parent == ".":
                parent_id = "."
            else:
                ensure_directory_chain(graph, parent)
                parent_id = parent
            if rel not in graph:
                add_node(graph, rel, "file", metadata=metadata)
                add_contains_edge(graph, parent_id, rel)
    add_reference_edges(graph, root)
    enabled = list(languages) if languages is not None else list(DEFAULT_LANGUAGES)
    skips = merge_code_structure(graph, root, enabled)
    graph.graph["languages"] = list(enabled)
    graph.graph["include_docs"] = bool(include_docs)
    graph.graph["include_pdfs"] = bool(include_pdfs)
    if include_docs:
        skips += merge_docs_structure(graph, root)
    if include_pdfs:
        skips += merge_pdf_structure(graph, root)
    graph.graph["parse_skips"] = skips
    return graph


def index_project(
    project_root: Path,
    output_path: Path,
    *,
    languages: Sequence[str] | None = None,
    include_docs: bool = False,
    include_pdfs: bool = False,
):
    """Index project and write graph.json artifact. Returns (path, stats)."""
    root = resolve_project_path(project_root)
    graph = build_inventory_graph(
        root,
        languages=languages,
        include_docs=include_docs,
        include_pdfs=include_pdfs,
    )
    written = save_graph(graph, output_path)
    artifact = to_artifact_dict(graph)
    parse_skips = int(graph.graph.get("parse_skips") or 0)
    stats = stats_from_artifact(artifact, written, parse_skips=parse_skips)
    return written, stats
