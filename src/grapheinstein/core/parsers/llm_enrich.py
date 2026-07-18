"""Merge local-LLM concept/relation enrichment into the project graph."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from loguru import logger

from grapheinstein.core.graph import (
    CODE_NODE_TYPES,
    add_concept,
    add_depends_on_edge,
    add_implements_edge,
    add_mentions_concept_edge,
    concept_id,
    slugify_concept,
)
from grapheinstein.core.parsers.llm_ollama import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    OllamaError,
    chat,
)

DEFAULT_MAX_CHARS = 12_000
DEFAULT_CONFIDENCE_THRESHOLD = 0.5
MAX_EVIDENCE_CHARS = 240

RELATION_TYPES = frozenset({"implements", "depends_on", "mentions"})
KIND_VALUES = frozenset({"domain_term", "library", "other"})

ChatFn = Callable[..., dict[str, Any]]


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def evidence_grounded(evidence: str, chunk: str) -> bool:
    """True if evidence appears in chunk (raw or whitespace-normalized)."""
    ev = (evidence or "").strip()
    if not ev:
        return False
    if len(ev) > MAX_EVIDENCE_CHARS:
        ev = ev[:MAX_EVIDENCE_CHARS]
    if ev in chunk:
        return True
    return _normalize_ws(ev) in _normalize_ws(chunk)


def _clip_evidence(evidence: str) -> str:
    ev = (evidence or "").strip()
    if len(ev) > MAX_EVIDENCE_CHARS:
        return ev[:MAX_EVIDENCE_CHARS]
    return ev


def build_chunk_text(path: Path, *, max_chars: int = DEFAULT_MAX_CHARS) -> tuple[str, bool]:
    """Read file text; return (text, truncated)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise OSError(f"Cannot read {path}: {exc}") from exc
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def _parse_confidence(raw: Any) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value < 0.0 or value > 1.0:
        return None
    return value


def _resolve_endpoint(
    graph,
    token: str,
    *,
    file_id: str,
    prefer_concept: bool = False,
) -> str | None:
    """Map a subject/object string to a graph node id."""
    token = (token or "").strip()
    if not token:
        return None
    if token in graph:
        return token
    # concept by name/slug
    slug = slugify_concept(token)
    cid = concept_id(slug)
    if cid in graph:
        return cid
    if prefer_concept:
        return None
    # code entity in same file by symbol name
    matches = []
    for nid, attrs in graph.nodes(data=True):
        if attrs.get("type") not in CODE_NODE_TYPES:
            continue
        meta = attrs.get("metadata") or {}
        if meta.get("file") != file_id:
            continue
        if meta.get("name") == token:
            matches.append(nid)
    if len(matches) == 1:
        return matches[0]
    # bare file id
    if token == file_id or token == Path(file_id).name:
        if file_id in graph:
            return file_id
    return None


def _ensure_concept(
    graph,
    name: str,
    *,
    kind: str | None = None,
) -> str | None:
    cleaned = (name or "").strip()
    if not cleaned:
        return None
    try:
        return add_concept(graph, name=cleaned, kind=kind)
    except ValueError:
        return None


def apply_enrichment_payload(
    graph,
    payload: dict[str, Any],
    *,
    file_id: str,
    chunk: str,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> tuple[int, int]:
    """
    Merge entities/relations from one chunk response.
    Returns (edges_added, dropped_count).
    """
    entities = payload.get("entities") if isinstance(payload, dict) else None
    relations = payload.get("relations") if isinstance(payload, dict) else None
    if not isinstance(entities, list):
        entities = []
    if not isinstance(relations, list):
        relations = []

    dropped = 0
    added = 0

    for ent in entities:
        if not isinstance(ent, dict):
            dropped += 1
            continue
        name = ent.get("name")
        conf = _parse_confidence(ent.get("confidence"))
        evidence = _clip_evidence(str(ent.get("evidence") or ""))
        if not isinstance(name, str) or not name.strip() or conf is None:
            dropped += 1
            continue
        if conf < confidence_threshold:
            dropped += 1
            continue
        if not evidence_grounded(evidence, chunk):
            dropped += 1
            continue
        kind_raw = ent.get("kind")
        kind = kind_raw if kind_raw in KIND_VALUES else None
        cid = _ensure_concept(graph, name.strip(), kind=kind)
        if not cid:
            dropped += 1
            continue
        if add_mentions_concept_edge(
            graph, file_id, cid, confidence=conf, evidence=evidence
        ):
            added += 1

    for rel in relations:
        if not isinstance(rel, dict):
            dropped += 1
            continue
        rel_type = rel.get("type")
        if rel_type not in RELATION_TYPES:
            dropped += 1
            continue
        conf = _parse_confidence(rel.get("confidence"))
        evidence = _clip_evidence(str(rel.get("evidence") or ""))
        subject = rel.get("subject")
        obj = rel.get("object")
        if (
            conf is None
            or not isinstance(subject, str)
            or not isinstance(obj, str)
            or not evidence
        ):
            dropped += 1
            continue
        if conf < confidence_threshold:
            dropped += 1
            continue
        if not evidence_grounded(evidence, chunk):
            dropped += 1
            continue

        # Ensure object concept exists for concept targets
        obj_concept = _ensure_concept(
            graph,
            obj.strip(),
            kind="library" if rel_type == "depends_on" else "domain_term",
        )
        source_id = _resolve_endpoint(graph, subject, file_id=file_id)
        if source_id is None and rel_type == "mentions":
            source_id = file_id if file_id in graph else None
        if source_id is None:
            # subject might be a new concept name for mentions only
            if rel_type == "mentions":
                source_id = file_id if file_id in graph else None
            else:
                dropped += 1
                continue

        target_id = obj_concept or _resolve_endpoint(
            graph, obj, file_id=file_id, prefer_concept=True
        )
        if target_id is None:
            dropped += 1
            continue

        ok = False
        if rel_type == "implements":
            src_type = graph.nodes[source_id].get("type") if source_id in graph else None
            if src_type not in CODE_NODE_TYPES:
                dropped += 1
                continue
            ok = add_implements_edge(
                graph, source_id, target_id, confidence=conf, evidence=evidence
            )
        elif rel_type == "depends_on":
            ok = add_depends_on_edge(
                graph, source_id, target_id, confidence=conf, evidence=evidence
            )
        elif rel_type == "mentions":
            ok = add_mentions_concept_edge(
                graph, source_id, target_id, confidence=conf, evidence=evidence
            )
        if ok:
            added += 1
        else:
            # already present or invalid endpoints
            pass

    return added, dropped


def _eligible_file_ids(graph, project_root: Path) -> list[str]:
    """Non-symlink text-ish files already in the inventory graph."""
    text_ext = {
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
        ".txt",
        ".rst",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".sh",
        ".bash",
        ".zsh",
    }
    result = []
    for nid, attrs in graph.nodes(data=True):
        if attrs.get("type") != "file":
            continue
        meta = attrs.get("metadata") or {}
        if meta.get("symlink"):
            continue
        if meta.get("skipped"):
            continue
        path = project_root / nid
        if path.suffix.lower() not in text_ext and path.suffix.lower() not in {".pdf"}:
            # still allow files without extension that look like source? skip unknown
            if path.suffix:
                continue
        if not path.is_file():
            continue
        result.append(nid)
    return sorted(result)


def merge_llm_enrichment(
    graph,
    project_root: Path,
    *,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    max_chars: int = DEFAULT_MAX_CHARS,
    llm_chat: ChatFn | None = None,
    progress_every: int = 1,
) -> int:
    """
    Enrich graph with concepts/relations via local LLM.
    Returns skip count (failed/truncated-warning files still count as processed;
    skips are failures only).
    """
    root = project_root
    chat_fn = llm_chat or chat
    skips = 0
    files = _eligible_file_ids(graph, root)
    total = len(files)
    for index, file_id in enumerate(files, start=1):
        if progress_every > 0 and (index == 1 or index % progress_every == 0 or index == total):
            logger.info("LLM enrichment {}/{}: {}", index, total, file_id)
        path = root / file_id
        try:
            chunk, truncated = build_chunk_text(path, max_chars=max_chars)
        except OSError as exc:
            logger.warning("LLM enrichment skip {}: {}", file_id, exc)
            skips += 1
            continue
        if truncated:
            logger.warning(
                "LLM enrichment truncating {} to {} chars", file_id, max_chars
            )
        if not chunk.strip():
            continue
        user_content = (
            f"File: {file_id}\n\n-----\n{chunk}\n-----\n"
            "Extract entities and relations from the chunk above."
        )
        try:
            payload = chat_fn(
                model=model,
                user_content=user_content,
                base_url=base_url,
            )
        except OllamaError as exc:
            logger.warning("LLM enrichment skip {}: {}", file_id, exc)
            skips += 1
            continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM enrichment skip {}: {}", file_id, exc)
            skips += 1
            continue
        try:
            apply_enrichment_payload(
                graph,
                payload,
                file_id=file_id,
                chunk=chunk,
                confidence_threshold=confidence_threshold,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM enrichment merge failed for {}: {}", file_id, exc)
            skips += 1
            continue
    return skips


__all__ = [
    "DEFAULT_CONFIDENCE_THRESHOLD",
    "DEFAULT_MAX_CHARS",
    "apply_enrichment_payload",
    "build_chunk_text",
    "evidence_grounded",
    "merge_llm_enrichment",
]
