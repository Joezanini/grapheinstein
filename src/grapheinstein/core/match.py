"""Concept matching: fuzzy text scoring and optional local embeddings."""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from grapheinstein.core.graph import CONCEPT_NODE_TYPE

_TOKEN_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)
_META_TEXT_KEYS = ("name", "text", "file", "language", "path", "kind")


@dataclass(frozen=True)
class MatchCandidate:
    node_id: str
    fuzzy_score: float
    embedding_score: float | None
    final_score: float
    node_type: str


def normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def node_search_text(node_id: str, node_type: str, metadata: dict[str, Any] | None) -> str:
    parts: list[str] = [str(node_id), str(node_type)]
    meta = metadata or {}
    for key in _META_TEXT_KEYS:
        raw = meta.get(key)
        if isinstance(raw, str) and raw.strip():
            parts.append(raw)
    return normalize_text(" ".join(parts))


def _tokens(text: str) -> set[str]:
    return {m.group(0).casefold() for m in _TOKEN_RE.finditer(text)}


def fuzzy_score(query: str, node_id: str, node_type: str, metadata: dict[str, Any] | None) -> float:
    """Score query against a node in [0.0, 1.0]."""
    q = normalize_text(query)
    if not q:
        return 0.0
    text = node_search_text(node_id, node_type, metadata)
    meta = metadata or {}
    name = normalize_text(str(meta.get("name") or ""))
    nid = normalize_text(str(node_id))

    if q == nid or (name and q == name):
        return 1.0

    ratio = SequenceMatcher(None, q, text).ratio() if text else 0.0
    name_ratio = SequenceMatcher(None, q, name).ratio() if name else 0.0
    id_ratio = SequenceMatcher(None, q, nid).ratio() if nid else 0.0

    q_tokens = _tokens(q)
    t_tokens = _tokens(text)
    token_score = 0.0
    if q_tokens and t_tokens:
        overlap = len(q_tokens & t_tokens) / max(len(q_tokens), 1)
        # Prefer containment either direction for partial phrases
        if q_tokens <= t_tokens or t_tokens <= q_tokens:
            token_score = max(overlap, 0.85)
        else:
            token_score = overlap
        # Near-miss tokens (typos) against individual node tokens / name
        best_tok = 0.0
        for qt in q_tokens:
            for tt in t_tokens:
                best_tok = max(best_tok, SequenceMatcher(None, qt, tt).ratio())
        if best_tok >= 0.8:
            token_score = max(token_score, best_tok * 0.95)

    substring = 0.0
    if q in text or (name and q in name) or q in nid:
        substring = 0.9
    elif text and (text in q or (name and name in q)):
        substring = 0.8

    return max(ratio, name_ratio, id_ratio, token_score, substring)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=True):
        dot += float(x) * float(y)
        na += float(x) * float(x)
        nb += float(y) * float(y)
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (math.sqrt(na) * math.sqrt(nb))))


def score_nodes(
    nodes: Sequence[dict[str, Any]],
    query: str,
    *,
    embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
    embed_prefilter: int = 200,
) -> tuple[list[MatchCandidate], str | None]:
    """
    Score all nodes. Returns (candidates, embed_skip_note).
    ``embed_skip_note`` is set when embeddings were requested/attempted but skipped.
    """
    fuzzy_ranked: list[tuple[float, str, str, dict[str, Any]]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        node_type = node.get("type")
        if not isinstance(node_id, str) or not isinstance(node_type, str):
            continue
        meta = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
        score = fuzzy_score(query, node_id, node_type, meta)
        fuzzy_ranked.append((score, node_id, node_type, meta))

    fuzzy_ranked.sort(key=lambda item: item[0], reverse=True)
    embed_note: str | None = None
    embedding_by_id: dict[str, float] = {}

    if embed_fn is not None and fuzzy_ranked:
        pool = fuzzy_ranked[: max(1, embed_prefilter)]
        texts = [normalize_text(query)] + [
            node_search_text(nid, ntype, meta) for _, nid, ntype, meta in pool
        ]
        try:
            vectors = embed_fn(texts)
            if len(vectors) != len(texts):
                raise ValueError(
                    f"embed_fn returned {len(vectors)} vectors for {len(texts)} texts"
                )
            q_vec = vectors[0]
            for vec, (_, nid, _, _) in zip(vectors[1:], pool, strict=True):
                embedding_by_id[nid] = cosine_similarity(q_vec, vec)
        except Exception as exc:  # noqa: BLE001 — soft-skip embeddings
            embed_note = f"Vector matching skipped: {exc}"

    candidates: list[MatchCandidate] = []
    for fuzzy, nid, ntype, _meta in fuzzy_ranked:
        emb = embedding_by_id.get(nid)
        final = max(fuzzy, emb if emb is not None else 0.0)
        candidates.append(
            MatchCandidate(
                node_id=nid,
                fuzzy_score=fuzzy,
                embedding_score=emb,
                final_score=final,
                node_type=ntype,
            )
        )
    return candidates, embed_note


def select_matches(
    candidates: Sequence[MatchCandidate],
    *,
    threshold: float = 0.55,
    top_n: int = 3,
) -> list[MatchCandidate]:
    """Select top-N candidates at/above threshold with concept tie-break."""
    eligible = [c for c in candidates if c.final_score >= threshold]
    eligible.sort(
        key=lambda c: (
            -c.final_score,
            0 if c.node_type == CONCEPT_NODE_TYPE else 1,
            len(c.node_id),
            c.node_id,
        )
    )
    n = max(1, int(top_n))
    return eligible[:n]


__all__ = [
    "MatchCandidate",
    "cosine_similarity",
    "fuzzy_score",
    "node_search_text",
    "normalize_text",
    "score_nodes",
    "select_matches",
]
