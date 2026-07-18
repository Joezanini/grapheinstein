"""Hybrid natural-language query: chunk retrieval + graph expand + cited answer."""

from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Sequence

from grapheinstein.core.explain import undirected_neighborhood
from grapheinstein.core.graph import (
    CONCEPT_NODE_TYPE,
    artifact_to_digraph,
    load_artifact,
    to_artifact_dict,
    write_artifact_dict,
)
from grapheinstein.core.match import (
    cosine_similarity,
    fuzzy_score,
    node_search_text,
    normalize_text,
)
from grapheinstein.core.parsers.llm_ollama import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    OllamaError,
    check_ready,
    chat_text,
    embed_texts,
)

AnswerStatus = Literal["ok", "skipped", "failed"]
ChunkSource = Literal["metadata_text", "composed"]

DEFAULT_QUERY_K = 20
MAX_QUERY_K = 200
DEFAULT_QUERY_HOPS = 1
DEFAULT_QUERY_MATCH_THRESHOLD = 0.40
DEFAULT_QUERY_NODE_CAP = 500
QUERY_ANSWER_SCHEMA_VERSION = "1.0.0"
_SAMPLE_HIT_LIMIT = 5

_NODE_CITE_RE = re.compile(r"\[node:([^\]]+)\]")
_EDGE_CITE_RE = re.compile(
    r"\[edge:([^\]\-]+)->([^\]:]+):([^\]]+)\]"
)

QUERY_SYSTEM_PROMPT = (
    "You answer a question about a software project using only the provided "
    "knowledge-graph evidence. Do not invent entities, files, or relations "
    "that are not listed. Cite supporting nodes as [node:<id>] and edges as "
    "[edge:<source>-><target>:<type>]. Be concise."
)


class QueryError(Exception):
    """Base error for query failures."""


class NoEvidenceError(QueryError):
    """Raised when no chunk/node scores above the match threshold."""


class EmptyCorpusError(QueryError):
    """Raised when the graph has no searchable chunk text."""


@dataclass(frozen=True)
class ChunkCandidate:
    node_id: str
    chunk_text: str
    node_type: str
    source: ChunkSource
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChunkHit:
    node_id: str
    fuzzy_score: float
    embedding_score: float | None
    final_score: float
    node_type: str
    source: ChunkSource


@dataclass(frozen=True)
class Citation:
    kind: Literal["node", "edge"]
    node_id: str | None = None
    source: str | None = None
    target: str | None = None
    edge_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.kind == "node":
            return {"kind": "node", "node_id": self.node_id}
        return {
            "kind": "edge",
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type,
        }


@dataclass(frozen=True)
class VisualizationSummary:
    node_count: int
    edge_count: int
    node_type_counts: dict[str, int]
    sample_hit_ids: tuple[str, ...]
    truncated: bool
    output_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "node_type_counts": dict(self.node_type_counts),
            "sample_hit_ids": list(self.sample_hit_ids),
            "truncated": self.truncated,
            "output_path": self.output_path,
        }

    def format_human(self) -> str:
        types = ", ".join(
            f"{t}={n}" for t, n in list(self.node_type_counts.items())[:8]
        )
        hits = ", ".join(self.sample_hit_ids) or "(none)"
        lines = [
            f"Supporting subgraph: {self.node_count} nodes, {self.edge_count} edges",
            f"Node types: {types or '(none)'}",
            f"Primary hits (sample): {hits}",
            f"Truncated: {'yes' if self.truncated else 'no'}",
            f"Output: {self.output_path}",
        ]
        return "\n".join(lines)


@dataclass(frozen=True)
class QueryResult:
    output_path: Path
    question: str
    hit_ids: tuple[str, ...]
    hit_scores: dict[str, float]
    k: int
    hops: int
    truncated: bool
    visualization: VisualizationSummary
    answer_status: AnswerStatus
    answer_text: str | None
    answer_detail: str | None
    citations: tuple[Citation, ...]
    embed_note: str | None
    answer_envelope: dict[str, Any]


def build_chunk_corpus(nodes: Sequence[dict[str, Any]]) -> list[ChunkCandidate]:
    """Build searchable chunk candidates from graph nodes."""
    corpus: list[ChunkCandidate] = []
    seen: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        node_type = node.get("type")
        if not isinstance(node_id, str) or not isinstance(node_type, str):
            continue
        if node_id in seen:
            continue
        meta = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
        text_raw = meta.get("text")
        if isinstance(text_raw, str) and text_raw.strip():
            chunk_text = normalize_text(text_raw)
            source: ChunkSource = "metadata_text"
        else:
            chunk_text = node_search_text(node_id, node_type, meta)
            source = "composed"
        if not chunk_text.strip():
            continue
        seen.add(node_id)
        corpus.append(
            ChunkCandidate(
                node_id=node_id,
                chunk_text=chunk_text,
                node_type=node_type,
                source=source,
                metadata=dict(meta),
            )
        )
    return corpus


def select_chunk_hits(
    corpus: Sequence[ChunkCandidate],
    question: str,
    *,
    k: int = DEFAULT_QUERY_K,
    threshold: float = DEFAULT_QUERY_MATCH_THRESHOLD,
    embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
    embed_prefilter: int = 200,
) -> tuple[list[ChunkHit], str | None]:
    """Score corpus and return up to ``k`` hits above ``threshold``."""
    if k < 1:
        raise QueryError("k must be >= 1")
    q = normalize_text(question)
    ranked: list[tuple[float, ChunkCandidate]] = []
    for cand in corpus:
        score = fuzzy_score(q, cand.node_id, cand.node_type, cand.metadata)
        # Also score against chunk body directly for long questions
        body_ratio = 0.0
        if cand.chunk_text:
            body_ratio = SequenceMatcher(None, q, cand.chunk_text).ratio()
            q_tokens = set(re.findall(r"[a-z0-9_]+", q))
            t_tokens = set(re.findall(r"[a-z0-9_]+", cand.chunk_text))
            if q_tokens and t_tokens:
                overlap = len(q_tokens & t_tokens) / max(len(q_tokens), 1)
                body_ratio = max(body_ratio, overlap)
                if q_tokens <= t_tokens:
                    body_ratio = max(body_ratio, 0.85)
        ranked.append((max(score, body_ratio), cand))

    ranked.sort(key=lambda item: item[0], reverse=True)
    embed_note: str | None = None
    embedding_by_id: dict[str, float] = {}

    if embed_fn is not None and ranked:
        pool = ranked[: max(1, embed_prefilter)]
        texts = [q] + [c.chunk_text for _, c in pool]
        try:
            vectors = embed_fn(texts)
            if len(vectors) != len(texts):
                raise ValueError(
                    f"embed_fn returned {len(vectors)} vectors for {len(texts)} texts"
                )
            q_vec = vectors[0]
            for vec, (_, cand) in zip(vectors[1:], pool):
                embedding_by_id[cand.node_id] = cosine_similarity(q_vec, vec)
        except Exception as exc:  # noqa: BLE001
            embed_note = f"Vector matching skipped: {exc}"

    hits: list[ChunkHit] = []
    for fuzzy, cand in ranked:
        emb = embedding_by_id.get(cand.node_id)
        final = max(fuzzy, emb if emb is not None else 0.0)
        hits.append(
            ChunkHit(
                node_id=cand.node_id,
                fuzzy_score=fuzzy,
                embedding_score=emb,
                final_score=final,
                node_type=cand.node_type,
                source=cand.source,
            )
        )

    eligible = [h for h in hits if h.final_score >= threshold]
    eligible.sort(
        key=lambda h: (
            -h.final_score,
            0 if h.source == "metadata_text" else 1,
            0 if h.node_type == CONCEPT_NODE_TYPE else 1,
            len(h.node_id),
            h.node_id,
        )
    )
    return eligible[: int(k)], embed_note


def build_supporting_subgraph(
    source: dict[str, Any],
    *,
    node_ids: set[str],
    question: str,
    hit_ids: list[str],
    hit_scores: dict[str, float],
    k: int,
    hops: int,
    truncated: bool,
) -> dict[str, Any]:
    """Build a schema 6.0.0 supporting subgraph artifact dict."""
    graph = artifact_to_digraph(source)
    sub = graph.subgraph(node_ids).copy()
    sub.graph.clear()
    project_root = ""
    src_graph = source.get("graph") if isinstance(source.get("graph"), dict) else {}
    if isinstance(src_graph.get("project_root"), str):
        project_root = src_graph["project_root"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sub.graph["project_root"] = project_root
    sub.graph["generated_at"] = now
    sub.graph["query_question"] = question
    sub.graph["query_hit_ids"] = list(hit_ids)
    sub.graph["query_k"] = int(k)
    sub.graph["query_hops"] = int(hops)
    sub.graph["query_hit_scores"] = {kid: float(v) for kid, v in hit_scores.items()}
    if truncated:
        sub.graph["query_truncated"] = True

    artifact = to_artifact_dict(sub)
    gmeta = artifact.setdefault("graph", {})
    gmeta["query_question"] = question
    gmeta["query_hit_ids"] = list(hit_ids)
    gmeta["query_k"] = int(k)
    gmeta["query_hops"] = int(hops)
    gmeta["generated_at"] = now
    gmeta["query_hit_scores"] = {kid: float(v) for kid, v in hit_scores.items()}
    if truncated:
        gmeta["query_truncated"] = True
    if project_root:
        gmeta["project_root"] = project_root
    return artifact


def format_visualization_summary(
    artifact: dict[str, Any],
    *,
    hit_ids: Sequence[str],
    truncated: bool,
    output_path: Path | str,
) -> VisualizationSummary:
    nodes = [n for n in (artifact.get("nodes") or []) if isinstance(n, dict)]
    links = [e for e in (artifact.get("links") or []) if isinstance(e, dict)]
    type_counts = Counter(
        str(n.get("type") or "unknown") for n in nodes if n.get("type")
    )
    sample = tuple(list(hit_ids)[:_SAMPLE_HIT_LIMIT])
    return VisualizationSummary(
        node_count=len(nodes),
        edge_count=len(links),
        node_type_counts=dict(sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        sample_hit_ids=sample,
        truncated=truncated,
        output_path=str(output_path),
    )


def _compact_evidence_facts(artifact: dict[str, Any], *, max_chars: int = 12000) -> str:
    lines: list[str] = ["Nodes:"]
    for node in artifact.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        meta = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
        name = meta.get("name") or ""
        text = meta.get("text") or ""
        excerpt = ""
        if isinstance(text, str) and text.strip():
            excerpt = text.strip().replace("\n", " ")[:200]
        lines.append(
            f"- {node.get('id')} (type={node.get('type')}, name={name}"
            + (f", text={excerpt}" if excerpt else "")
            + ")"
        )
    lines.append("Edges:")
    for link in artifact.get("links") or []:
        if not isinstance(link, dict):
            continue
        lines.append(
            f"- {link.get('source')} -[{link.get('type')}/{link.get('provenance')}]-> "
            f"{link.get('target')}"
        )
    text = "\n".join(lines)
    if len(text) > max_chars:
        return text[: max_chars - 20] + "\n...[truncated]"
    return text


def _subgraph_indexes(
    artifact: dict[str, Any],
) -> tuple[set[str], set[tuple[str, str, str]]]:
    node_ids = {
        str(n["id"])
        for n in (artifact.get("nodes") or [])
        if isinstance(n, dict) and isinstance(n.get("id"), str)
    }
    edges: set[tuple[str, str, str]] = set()
    for link in artifact.get("links") or []:
        if not isinstance(link, dict):
            continue
        src, tgt, et = link.get("source"), link.get("target"), link.get("type")
        if isinstance(src, str) and isinstance(tgt, str) and isinstance(et, str):
            edges.add((src, tgt, et))
    return node_ids, edges


def parse_and_filter_citations(
    text: str,
    artifact: dict[str, Any],
) -> list[Citation]:
    """Extract citations from model text; keep only those present in the subgraph."""
    node_ids, edges = _subgraph_indexes(artifact)
    found: list[Citation] = []
    seen: set[tuple[Any, ...]] = set()

    for match in _NODE_CITE_RE.finditer(text or ""):
        nid = match.group(1).strip()
        key = ("node", nid)
        if nid in node_ids and key not in seen:
            seen.add(key)
            found.append(Citation(kind="node", node_id=nid))

    for match in _EDGE_CITE_RE.finditer(text or ""):
        src = match.group(1).strip()
        tgt = match.group(2).strip()
        et = match.group(3).strip()
        key = ("edge", src, tgt, et)
        if (src, tgt, et) in edges and key not in seen:
            seen.add(key)
            found.append(
                Citation(kind="edge", source=src, target=tgt, edge_type=et)
            )
    return found


def fallback_citations(
    artifact: dict[str, Any],
    hit_ids: Sequence[str],
    *,
    max_nodes: int = 5,
    max_edges: int = 3,
) -> list[Citation]:
    """Deterministic Sources list from primary hits when the model cites nothing valid."""
    node_ids, edges = _subgraph_indexes(artifact)
    cites: list[Citation] = []
    for nid in hit_ids:
        if nid in node_ids:
            cites.append(Citation(kind="node", node_id=nid))
        if len(cites) >= max_nodes:
            break
    edge_count = 0
    for src, tgt, et in sorted(edges):
        if src in hit_ids or tgt in hit_ids:
            cites.append(Citation(kind="edge", source=src, target=tgt, edge_type=et))
            edge_count += 1
            if edge_count >= max_edges:
                break
    return cites


def generate_cited_answer(
    *,
    question: str,
    artifact: dict[str, Any],
    hit_ids: Sequence[str],
    model: str,
    base_url: str,
    chat_fn: Callable[..., str] | None = None,
    list_models_fn: Callable[[str], list[str]] | None = None,
) -> tuple[AnswerStatus, str | None, str | None, list[Citation]]:
    """Return (status, text, detail, citations)."""
    ready, msg = check_ready(model=model, base_url=base_url, list_models_fn=list_models_fn)
    if not ready:
        return (
            "skipped",
            None,
            msg.replace("LLM enrichment skipped", "Answer skipped"),
            [],
        )

    facts = _compact_evidence_facts(artifact)
    user_content = (
        f"Question: {question}\n"
        f"Primary hit ids: {list(hit_ids)}\n"
        f"Evidence:\n{facts}\n"
        "Answer the question and include [node:…] / [edge:…] citations."
    )
    fn = chat_fn or chat_text
    try:
        text = fn(
            model=model,
            user_content=user_content,
            base_url=base_url,
            system=QUERY_SYSTEM_PROMPT,
        )
    except OllamaError as exc:
        return "failed", None, f"Answer failed: {exc}", []
    except Exception as exc:  # noqa: BLE001
        return "failed", None, f"Answer failed: {exc}", []
    if not isinstance(text, str) or not text.strip():
        return "failed", None, "Answer failed: empty model response", []

    answer = text.strip()
    citations = parse_and_filter_citations(answer, artifact)
    if not citations:
        citations = fallback_citations(artifact, hit_ids)
        sources = ", ".join(
            c.node_id if c.kind == "node" else f"{c.source}->{c.target}:{c.edge_type}"
            for c in citations
        )
        if sources:
            answer = f"{answer}\n\nSources: {sources}"
    return "ok", answer, None, citations


def query_answer_to_dict(result: QueryResult) -> dict[str, Any]:
    """Serialize a QueryResult to the query-answer JSON envelope."""
    return {
        "schema_version": QUERY_ANSWER_SCHEMA_VERSION,
        "question": result.question,
        "output": str(result.output_path),
        "k": result.k,
        "hops": result.hops,
        "hit_ids": list(result.hit_ids),
        "truncated": result.truncated,
        "embed_note": result.embed_note,
        "visualization": result.visualization.to_dict(),
        "answer": {
            "status": result.answer_status,
            "text": result.answer_text,
            "detail": result.answer_detail,
            "citations": [c.to_dict() for c in result.citations],
        },
    }


def run_query(
    question: str,
    input_path: Path,
    output_path: Path,
    *,
    k: int = DEFAULT_QUERY_K,
    hops: int = DEFAULT_QUERY_HOPS,
    match_threshold: float = DEFAULT_QUERY_MATCH_THRESHOLD,
    node_cap: int = DEFAULT_QUERY_NODE_CAP,
    want_answer: bool = True,
    llm_model: str = DEFAULT_MODEL,
    llm_base_url: str = DEFAULT_BASE_URL,
    embedding_model: str | None = None,
    use_embeddings: bool = True,
    chat_fn: Callable[..., str] | None = None,
    embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
    list_models_fn: Callable[[str], list[str]] | None = None,
    cache=None,
) -> QueryResult:
    """
    Hybrid retrieve, write supporting subgraph, visualize, optionally answer.
    Raises NoEvidenceError / EmptyCorpusError / QueryError / GraphError / FileNotFoundError.
    """
    q = question.strip()
    if not q:
        raise QueryError("Question must be a non-empty string")
    if hops not in (1, 2):
        raise QueryError(f"hops must be 1 or 2, got {hops}")
    if not (1 <= int(k) <= MAX_QUERY_K):
        raise QueryError(f"k must be between 1 and {MAX_QUERY_K}, got {k}")
    if not (0.0 <= match_threshold <= 1.0):
        raise QueryError("match_threshold must be in [0.0, 1.0]")
    if node_cap < 1:
        raise QueryError("node_cap must be >= 1")

    source = load_artifact(input_path.expanduser())
    nodes = source.get("nodes") or []
    if not isinstance(nodes, list) or not nodes:
        raise EmptyCorpusError("Input graph has no searchable chunk content")

    corpus = build_chunk_corpus(nodes)
    if not corpus:
        raise EmptyCorpusError("Input graph has no searchable chunk content")

    active_embed: Callable[[list[str]], list[list[float]]] | None = None
    embed_note: str | None = None
    embed_model = embedding_model or llm_model
    if use_embeddings:
        if embed_fn is not None:
            active_embed = embed_fn
        else:
            ready, ready_msg = check_ready(
                model=embed_model,
                base_url=llm_base_url,
                list_models_fn=list_models_fn,
            )
            if ready:

                def _default_embed(texts: list[str]) -> list[list[float]]:
                    return embed_texts(
                        texts,
                        model=embed_model,
                        base_url=llm_base_url,
                        cache=cache,
                    )

                active_embed = _default_embed
            else:
                embed_note = ready_msg.replace(
                    "LLM enrichment skipped", "Vector matching skipped"
                )

    hits, scored_note = select_chunk_hits(
        corpus,
        q,
        k=int(k),
        threshold=match_threshold,
        embed_fn=active_embed,
    )
    if scored_note:
        embed_note = scored_note
    if not hits:
        raise NoEvidenceError(
            f"No evidence matched question {q!r} above threshold {match_threshold}"
        )

    hit_ids = [h.node_id for h in hits]
    hit_scores = {h.node_id: h.final_score for h in hits}
    digraph = artifact_to_digraph(source)
    node_ids, truncated = undirected_neighborhood(
        digraph, hit_ids, hops=hops, node_cap=node_cap
    )
    artifact = build_supporting_subgraph(
        source,
        node_ids=node_ids,
        question=q,
        hit_ids=hit_ids,
        hit_scores=hit_scores,
        k=int(k),
        hops=hops,
        truncated=truncated,
    )
    written = write_artifact_dict(artifact, output_path.expanduser(), compress=False)
    viz = format_visualization_summary(
        artifact, hit_ids=hit_ids, truncated=truncated, output_path=written
    )

    answer_status: AnswerStatus = "skipped"
    answer_text: str | None = None
    answer_detail: str | None = None
    citations: list[Citation] = []
    if want_answer:
        answer_status, answer_text, answer_detail, citations = generate_cited_answer(
            question=q,
            artifact=artifact,
            hit_ids=hit_ids,
            model=llm_model,
            base_url=llm_base_url,
            chat_fn=chat_fn,
            list_models_fn=list_models_fn,
        )
    else:
        answer_detail = "Answer skipped: --no-answer"

    result = QueryResult(
        output_path=written,
        question=q,
        hit_ids=tuple(hit_ids),
        hit_scores=hit_scores,
        k=int(k),
        hops=hops,
        truncated=truncated,
        visualization=viz,
        answer_status=answer_status,
        answer_text=answer_text,
        answer_detail=answer_detail,
        citations=tuple(citations),
        embed_note=embed_note,
        answer_envelope={},
    )
    envelope = query_answer_to_dict(result)
    return QueryResult(
        output_path=result.output_path,
        question=result.question,
        hit_ids=result.hit_ids,
        hit_scores=result.hit_scores,
        k=result.k,
        hops=result.hops,
        truncated=result.truncated,
        visualization=result.visualization,
        answer_status=result.answer_status,
        answer_text=result.answer_text,
        answer_detail=result.answer_detail,
        citations=result.citations,
        embed_note=result.embed_note,
        answer_envelope=envelope,
    )


__all__ = [
    "AnswerStatus",
    "ChunkCandidate",
    "ChunkHit",
    "Citation",
    "DEFAULT_QUERY_HOPS",
    "DEFAULT_QUERY_K",
    "DEFAULT_QUERY_MATCH_THRESHOLD",
    "DEFAULT_QUERY_NODE_CAP",
    "EmptyCorpusError",
    "MAX_QUERY_K",
    "NoEvidenceError",
    "QUERY_ANSWER_SCHEMA_VERSION",
    "QUERY_SYSTEM_PROMPT",
    "QueryError",
    "QueryResult",
    "VisualizationSummary",
    "build_chunk_corpus",
    "build_supporting_subgraph",
    "fallback_citations",
    "format_visualization_summary",
    "generate_cited_answer",
    "parse_and_filter_citations",
    "query_answer_to_dict",
    "run_query",
    "select_chunk_hits",
]
