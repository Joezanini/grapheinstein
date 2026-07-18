"""Resolve extract facts into graph nodes and edges."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import networkx as nx
from loguru import logger

from grapheinstein.core.cache import (
    KIND_AST,
    content_hash_bytes,
    pickle_dumps,
    pickle_loads,
    settings_hash,
)
from grapheinstein.core.graph import (
    add_calls_edge,
    add_code_entity,
    add_defines_edge,
    add_imports_edge,
)
from grapheinstein.core.parsers.extract import (
    CallFact,
    CodeEntity,
    ExtractResult,
    ImportFact,
    extract_file,
)
from grapheinstein.core.parsers.registry import language_for_path

if TYPE_CHECKING:
    from grapheinstein.core.cache import CacheStore

_AST_PARSER_VERSION = "tree-sitter-v1"


def _module_to_candidates(module: str, source_file: str, language: str) -> list[str]:
    """Map import module string to possible project-relative file ids."""
    candidates: list[str] = []
    if not module:
        return candidates

    if language in {"javascript", "typescript"}:
        if module.startswith("."):
            resolved = Path(source_file).parent
            for part in Path(module).parts:
                if part in {".", ""}:
                    continue
                if part == "..":
                    resolved = resolved.parent
                else:
                    resolved = resolved / part
            target = resolved.as_posix()
            if Path(target).suffix:
                candidates.append(target)
            else:
                for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
                    candidates.append(f"{target}{ext}")
                    candidates.append(f"{target}/index{ext}")
        return list(dict.fromkeys(candidates))

    if language == "python":
        if module.startswith("."):
            dots = len(module) - len(module.lstrip("."))
            rest = module.lstrip(".")
            parent = Path(source_file).parent
            for _ in range(max(dots - 1, 0)):
                parent = parent.parent
            if rest:
                base = parent / rest.replace(".", "/")
            else:
                base = parent
            base_s = base.as_posix()
            candidates.extend([f"{base_s}.py", f"{base_s}/__init__.py"])
        else:
            rel = module.replace(".", "/")
            parent = Path(source_file).parent.as_posix()
            leaf = rel.split("/")[-1]
            candidates.extend(
                [
                    f"{rel}.py",
                    f"{rel}/__init__.py",
                    f"{parent}/{leaf}.py",
                ]
            )
        return list(dict.fromkeys(candidates))

    cleaned = module.strip().strip('"').strip("'")
    candidates.append(cleaned)
    return list(dict.fromkeys(candidates))


def resolve_import_target(
    graph: nx.DiGraph,
    fact: ImportFact,
    source_file: str,
    language: str,
) -> str | None:
    if not fact.module and not fact.names:
        return None
    module = fact.module or (fact.names[0] if fact.names else "")
    candidates = _module_to_candidates(module, source_file, language)
    hits = [c for c in candidates if c in graph and graph.nodes[c].get("type") == "file"]
    if len(hits) != 1:
        return None
    file_hit = hits[0]
    if fact.names:
        symbol_hits: list[str] = []
        for name in fact.names:
            for nid, attrs in graph.nodes(data=True):
                if attrs.get("type") in {"function", "class", "method"}:
                    meta = attrs.get("metadata") or {}
                    if meta.get("file") == file_hit and meta.get("name") == name:
                        symbol_hits.append(nid)
        if len(symbol_hits) == 1:
            return symbol_hits[0]
    return file_hit


def _index_entities_by_name(graph: nx.DiGraph) -> dict[str, list[str]]:
    by_name: dict[str, list[str]] = {}
    for nid, attrs in graph.nodes(data=True):
        if attrs.get("type") in {"function", "class", "method"}:
            name = (attrs.get("metadata") or {}).get("name")
            if isinstance(name, str):
                by_name.setdefault(name, []).append(nid)
    return by_name


def _entities_in_file(graph: nx.DiGraph, file_id: str) -> dict[str, list[str]]:
    by_name: dict[str, list[str]] = {}
    for nid, attrs in graph.nodes(data=True):
        if attrs.get("type") in {"function", "class", "method"}:
            meta = attrs.get("metadata") or {}
            if meta.get("file") == file_id:
                name = meta.get("name")
                if isinstance(name, str):
                    by_name.setdefault(name, []).append(nid)
    return by_name


def apply_entities(
    graph: nx.DiGraph,
    *,
    file_id: str,
    language: str,
    entities: list[CodeEntity],
) -> dict[str, str]:
    """Add entity nodes and defines edges. Returns enclosing key → node id."""
    enclosing_map: dict[str, str] = {}
    class_ids: dict[str, str] = {}

    for ent in entities:
        if ent.kind != "class":
            continue
        nid = add_code_entity(
            graph,
            file_id=file_id,
            kind="class",
            name=ent.name,
            start_line=ent.start_line,
            language=language,
            end_line=ent.end_line,
        )
        class_ids[ent.name] = nid
        add_defines_edge(graph, file_id, nid)
        enclosing_map[f"class:{ent.name}:{ent.start_line}"] = nid

    for ent in entities:
        if ent.kind == "class":
            continue
        nid = add_code_entity(
            graph,
            file_id=file_id,
            kind=ent.kind,
            name=ent.name,
            start_line=ent.start_line,
            language=language,
            end_line=ent.end_line,
            qualified_name=f"{ent.parent_class}.{ent.name}" if ent.parent_class else None,
        )
        add_defines_edge(graph, file_id, nid)
        if ent.kind == "method" and ent.parent_class and ent.parent_class in class_ids:
            add_defines_edge(graph, class_ids[ent.parent_class], nid)
        enclosing_map[f"{ent.kind}:{ent.name}:{ent.start_line}"] = nid

    return enclosing_map


def apply_edges(
    graph: nx.DiGraph,
    *,
    file_id: str,
    language: str,
    imports: list[ImportFact],
    calls: list[CallFact],
    enclosing_map: dict[str, str],
) -> None:
    for fact in imports:
        target = resolve_import_target(graph, fact, file_id, language)
        if target:
            add_imports_edge(graph, file_id, target)

    by_name_global = _index_entities_by_name(graph)
    by_name_file = _entities_in_file(graph, file_id)
    for call in calls:
        targets = by_name_file.get(call.name) or []
        if len(targets) != 1:
            targets = by_name_global.get(call.name) or []
        if len(targets) != 1:
            continue
        callee = targets[0]
        source = enclosing_map.get(call.enclosing or "") or file_id
        add_calls_edge(graph, source, callee)


def _extract_file_cached(
    path: Path,
    lang: str,
    *,
    file_id: str,
    cache: CacheStore | None,
) -> ExtractResult:
    if cache is None:
        return extract_file(path, lang, file_id=file_id)

    try:
        raw = path.read_bytes()
    except OSError:
        return extract_file(path, lang, file_id=file_id)

    content_hash = content_hash_bytes(raw)
    settings = settings_hash(
        {"kind": KIND_AST, "language": lang, "parser": _AST_PARSER_VERSION}
    )
    cached = cache.get(KIND_AST, file_id, content_hash, settings)
    if cached is not None:
        try:
            return pickle_loads(cached)
        except Exception as exc:  # noqa: BLE001
            logger.warning("AST cache payload for {} failed to load: {}", file_id, exc)

    result = extract_file(path, lang, file_id=file_id)
    try:
        cache.put(KIND_AST, file_id, content_hash, settings, pickle_dumps(result))
    except Exception as exc:  # noqa: BLE001
        logger.warning("AST cache write failed for {}: {}", file_id, exc)
    return result


def merge_code_structure(
    graph: nx.DiGraph,
    project_root: Path,
    enabled_languages: list[str],
    cache: CacheStore | None = None,
) -> int:
    """
    Walk file nodes, extract structure for enabled languages, merge into graph.
    Returns number of skipped files.
    """
    skips = 0
    file_nodes = [
        nid
        for nid, attrs in graph.nodes(data=True)
        if attrs.get("type") == "file"
        and not (attrs.get("metadata") or {}).get("symlink")
        and not (attrs.get("metadata") or {}).get("skipped")
    ]

    pending: list[tuple[str, str, ExtractResult, dict[str, str]]] = []
    for file_id in sorted(file_nodes):
        lang = language_for_path(file_id, enabled_languages)
        if lang is None:
            continue
        path = project_root / file_id
        try:
            result = _extract_file_cached(path, lang, file_id=file_id, cache=cache)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Structure extract failed for {}: {}", file_id, exc)
            skips += 1
            continue
        if result.skipped:
            skips += 1
            logger.warning(
                "Skipped structure extraction for {} ({})",
                file_id,
                result.skip_reason or "unknown",
            )
            continue
        if result.skip_reason == "parse errors":
            skips += 1
        enclosing = apply_entities(
            graph, file_id=file_id, language=lang, entities=result.entities
        )
        pending.append((file_id, lang, result, enclosing))

    for file_id, lang, result, enclosing in pending:
        apply_edges(
            graph,
            file_id=file_id,
            language=lang,
            imports=result.imports,
            calls=result.calls,
            enclosing_map=enclosing,
        )

    graph.graph["languages"] = list(enabled_languages)
    return skips
