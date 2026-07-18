"""Path between concepts: weighted shortest path + path-answer JSON."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import networkx as nx

from grapheinstein.core.graph import GraphError, artifact_to_digraph, load_artifact
from grapheinstein.core.match import MatchCandidate, score_nodes, select_matches
from grapheinstein.core.parsers.llm_ollama import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    chat_text,
    check_ready,
    embed_texts,
)

PATH_ANSWER_KIND = "path_answer"
PATH_ANSWER_VERSION = "1.0.0"
INPUT_SCHEMA_VERSION = "6.0.0"

DEFAULT_MATCH_THRESHOLD = 0.55
DEFAULT_MAX_HOPS = 32
DEFAULT_CONFIDENCE = 0.5
DEFAULT_CONFIDENCE_FLOOR = 0.35
DEFAULT_INFERRED_FACTOR = 1.75

TYPE_BASE: dict[str, float] = {
    "implements": 1.0,
    "depends_on": 1.0,
    "calls": 1.0,
    "imports": 1.0,
    "mentions": 1.25,
    "references": 1.25,
    "related_to": 1.25,
    "defines": 1.25,
    "section_of": 1.5,
    "contains": 2.0,
}
DEFAULT_TYPE_BASE = 1.5

ExplanationMode = Literal["deterministic", "llm"]
ExplanationStatus = Literal["ok", "skipped", "failed"]

PATH_SYSTEM_PROMPT = (
    "You rewrite a knowledge-graph path explanation for clarity. "
    "Use only the provided steps (node ids, edge types, provenance). "
    "Do not invent relations. Keep it to one or two short sentences."
)


class PathError(Exception):
    """Base error for path-query failures."""


class EndpointUnresolvedError(PathError):
    """Raised when start and/or end cannot be matched."""

    def __init__(self, message: str, *, failed: Sequence[str]) -> None:
        super().__init__(message)
        self.failed = tuple(failed)


class NoPathError(PathError):
    """Raised when no directed path exists between endpoints."""


class PathTooLongError(PathError):
    """Raised when the found path exceeds max_hops."""


@dataclass(frozen=True)
class PathStep:
    source: str
    target: str
    type: str
    provenance: str
    confidence: float | None
    cost: float


@dataclass(frozen=True)
class EndpointInfo:
    query: str
    node_id: str
    score: float
    node_type: str


@dataclass(frozen=True)
class PathAnswer:
    start: EndpointInfo
    end: EndpointInfo
    nodes: tuple[str, ...]
    steps: tuple[PathStep, ...]
    hop_count: int
    total_cost: float
    explanation: str
    explanation_mode: ExplanationMode
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return path_answer_to_dict(self)


@dataclass(frozen=True)
class PathResult:
    answer: PathAnswer
    embed_note: str | None
    explanation_status: ExplanationStatus
    explanation_detail: str | None
    output_path: Path | None


def edge_cost(
    data: dict[str, Any],
    *,
    confidence_default: float = DEFAULT_CONFIDENCE,
    confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR,
    inferred_factor: float = DEFAULT_INFERRED_FACTOR,
    type_base: dict[str, float] | None = None,
) -> float:
    """Positive edge weight; lower is preferred."""
    bases = type_base if type_base is not None else TYPE_BASE
    edge_type = str(data.get("type") or "")
    base = float(bases.get(edge_type, DEFAULT_TYPE_BASE))
    provenance = str(data.get("provenance") or "inferred")
    prov_factor = 1.0 if provenance == "extracted" else float(inferred_factor)
    raw_conf = data.get("confidence")
    if raw_conf is None:
        conf = float(confidence_default)
    else:
        try:
            conf = float(raw_conf)
        except (TypeError, ValueError):
            conf = float(confidence_default)
    conf = max(conf, float(confidence_floor))
    return base * prov_factor / conf


def _weight_fn(
    _u: Any,
    _v: Any,
    data: dict[str, Any],
    *,
    confidence_default: float,
    confidence_floor: float,
    inferred_factor: float,
) -> float:
    return edge_cost(
        data,
        confidence_default=confidence_default,
        confidence_floor=confidence_floor,
        inferred_factor=inferred_factor,
    )


def resolve_endpoint(
    nodes: Sequence[dict[str, Any]],
    query: str,
    *,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
) -> tuple[MatchCandidate | None, str | None]:
    """Resolve a single best node for ``query``. Returns (match|None, embed_note)."""
    text = query.strip()
    if not text:
        return None, None
    candidates, embed_note = score_nodes(nodes, text, embed_fn=embed_fn)
    selected = select_matches(candidates, threshold=threshold, top_n=1)
    if not selected:
        return None, embed_note
    return selected[0], embed_note


def find_weighted_path(
    graph: nx.DiGraph,
    start_id: str,
    end_id: str,
    *,
    max_hops: int = DEFAULT_MAX_HOPS,
    confidence_default: float = DEFAULT_CONFIDENCE,
    confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR,
    inferred_factor: float = DEFAULT_INFERRED_FACTOR,
) -> tuple[list[str], list[PathStep], float]:
    """
    Return (nodes, steps, total_cost) for the preferred directed path.
    Raises NoPathError / PathTooLongError.
    """
    if start_id not in graph:
        raise PathError(f"Start node not in graph: {start_id}")
    if end_id not in graph:
        raise PathError(f"End node not in graph: {end_id}")

    if start_id == end_id:
        return [start_id], [], 0.0

    def weight(u: Any, v: Any, data: dict[str, Any]) -> float:
        return _weight_fn(
            u,
            v,
            data,
            confidence_default=confidence_default,
            confidence_floor=confidence_floor,
            inferred_factor=inferred_factor,
        )

    try:
        node_list = nx.shortest_path(graph, start_id, end_id, weight=weight)
    except nx.NetworkXNoPath as exc:
        raise NoPathError(
            f"No directed path from {start_id!r} to {end_id!r}"
        ) from exc

    hops = len(node_list) - 1
    if hops > max_hops:
        raise PathTooLongError(
            f"Path has {hops} edges, exceeding max_hops={max_hops}"
        )

    steps: list[PathStep] = []
    total = 0.0
    for i in range(hops):
        u, v = node_list[i], node_list[i + 1]
        data = dict(graph.edges[u, v])
        cost = edge_cost(
            data,
            confidence_default=confidence_default,
            confidence_floor=confidence_floor,
            inferred_factor=inferred_factor,
        )
        raw_conf = data.get("confidence")
        conf: float | None
        if raw_conf is None:
            conf = None
        else:
            try:
                conf = float(raw_conf)
            except (TypeError, ValueError):
                conf = None
        step = PathStep(
            source=u,
            target=v,
            type=str(data.get("type") or ""),
            provenance=str(data.get("provenance") or "inferred"),
            confidence=conf,
            cost=cost,
        )
        steps.append(step)
        total += cost
    return node_list, steps, total


def format_deterministic_explanation(
    start_query: str,
    end_query: str,
    nodes: Sequence[str],
    steps: Sequence[PathStep],
) -> str:
    if not steps:
        if len(nodes) == 1:
            return (
                f"{start_query!r} and {end_query!r} resolve to the same entity "
                f"({nodes[0]})."
            )
        return f"{start_query!r} connects to {end_query!r} with no edges."

    parts: list[str] = []
    for step in steps:
        conf = ""
        if step.confidence is not None:
            conf = f", confidence={step.confidence:.2f}"
        parts.append(f"{step.source} —[{step.type}/{step.provenance}{conf}]→ {step.target}")
    chain = " ".join(parts)
    return f"{start_query!r} connects to {end_query!r} via: {chain}."


def path_answer_to_dict(answer: PathAnswer) -> dict[str, Any]:
    return {
        "kind": PATH_ANSWER_KIND,
        "version": PATH_ANSWER_VERSION,
        "input_schema_version": INPUT_SCHEMA_VERSION,
        "start": {
            "query": answer.start.query,
            "node_id": answer.start.node_id,
            "score": answer.start.score,
            "node_type": answer.start.node_type,
        },
        "end": {
            "query": answer.end.query,
            "node_id": answer.end.node_id,
            "score": answer.end.score,
            "node_type": answer.end.node_type,
        },
        "nodes": list(answer.nodes),
        "steps": [
            {
                "source": s.source,
                "target": s.target,
                "type": s.type,
                "provenance": s.provenance,
                "confidence": s.confidence,
                "cost": s.cost,
            }
            for s in answer.steps
        ],
        "hop_count": answer.hop_count,
        "total_cost": answer.total_cost,
        "explanation": answer.explanation,
        "explanation_mode": answer.explanation_mode,
        "generated_at": answer.generated_at,
    }


def build_path_answer(
    *,
    start: EndpointInfo,
    end: EndpointInfo,
    nodes: Sequence[str],
    steps: Sequence[PathStep],
    total_cost: float,
    explanation: str,
    explanation_mode: ExplanationMode = "deterministic",
    generated_at: str | None = None,
) -> PathAnswer:
    ts = generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    node_tuple = tuple(nodes)
    step_tuple = tuple(steps)
    return PathAnswer(
        start=start,
        end=end,
        nodes=node_tuple,
        steps=step_tuple,
        hop_count=len(step_tuple),
        total_cost=float(total_cost),
        explanation=explanation,
        explanation_mode=explanation_mode,
        generated_at=ts,
    )


def write_path_answer(answer: PathAnswer, path: Path) -> Path:
    """Atomically write path-answer JSON to ``path``."""
    dest = path.expanduser().resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(path_answer_to_dict(answer), indent=2, ensure_ascii=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=".path_", suffix=".json", dir=str(dest.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, dest)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return dest


def _polish_explanation(
    deterministic: str,
    steps: Sequence[PathStep],
    *,
    llm_model: str,
    llm_base_url: str,
    chat_fn: Callable[..., str] | None,
) -> tuple[str, ExplanationMode, ExplanationStatus, str | None]:
    active = chat_fn
    if active is None:
        ready, ready_msg = check_ready(model=llm_model, base_url=llm_base_url)
        if not ready:
            return (
                deterministic,
                "deterministic",
                "skipped",
                ready_msg.replace("LLM enrichment skipped", "LLM polish skipped"),
            )

        def _chat(system: str, user: str, **_kwargs: Any) -> str:
            return chat_text(
                system,
                user,
                model=llm_model,
                base_url=llm_base_url,
            )

        active = _chat

    facts = "; ".join(
        f"{s.source} -[{s.type}/{s.provenance}]-> {s.target}" for s in steps
    ) or "(no edges)"
    user = f"Deterministic text:\n{deterministic}\n\nSteps:\n{facts}"
    try:
        polished = active(PATH_SYSTEM_PROMPT, user).strip()
    except Exception as exc:  # noqa: BLE001
        return deterministic, "deterministic", "failed", f"LLM polish failed: {exc}"
    if not polished:
        return deterministic, "deterministic", "failed", "LLM polish returned empty text"
    return polished, "llm", "ok", None


def find_path(
    start: str,
    end: str,
    input_path: Path | str,
    *,
    output_path: Path | str | None = None,
    match_threshold: float = DEFAULT_MATCH_THRESHOLD,
    max_hops: int = DEFAULT_MAX_HOPS,
    confidence_default: float = DEFAULT_CONFIDENCE,
    confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR,
    inferred_factor: float = DEFAULT_INFERRED_FACTOR,
    want_llm_explain: bool = True,
    use_embeddings: bool = True,
    llm_model: str = DEFAULT_MODEL,
    llm_base_url: str = DEFAULT_BASE_URL,
    embedding_model: str | None = None,
    embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
    chat_fn: Callable[..., str] | None = None,
    cache=None,
) -> PathResult:
    """
    Load graph, resolve endpoints, find weighted path, build path answer.
    """
    start_q = start.strip()
    end_q = end.strip()
    if not start_q:
        raise PathError("start must be a non-empty string")
    if not end_q:
        raise PathError("end must be a non-empty string")
    if not (0.0 <= match_threshold <= 1.0):
        raise PathError("match_threshold must be in [0.0, 1.0]")
    if max_hops < 0:
        raise PathError("max_hops must be >= 0")

    artifact = load_artifact(Path(input_path))
    nodes_raw = artifact.get("nodes")
    if not isinstance(nodes_raw, list):
        raise GraphError("Artifact nodes must be a list")
    try:
        graph = artifact_to_digraph(artifact)
    except Exception as exc:  # noqa: BLE001
        raise GraphError(f"Cannot build digraph from artifact: {exc}") from exc

    active_embed: Callable[[list[str]], list[list[float]]] | None = None
    embed_note: str | None = None
    embed_model = embedding_model or llm_model
    if use_embeddings:
        if embed_fn is not None:
            active_embed = embed_fn
        else:
            ready, ready_msg = check_ready(model=embed_model, base_url=llm_base_url)
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

    start_match, note_a = resolve_endpoint(
        nodes_raw, start_q, threshold=match_threshold, embed_fn=active_embed
    )
    end_match, note_b = resolve_endpoint(
        nodes_raw, end_q, threshold=match_threshold, embed_fn=active_embed
    )
    if note_a or note_b:
        embed_note = note_a or note_b
    failed: list[str] = []
    if start_match is None:
        failed.append("start")
    if end_match is None:
        failed.append("end")
    if failed:
        sides = " and ".join(failed)
        raise EndpointUnresolvedError(
            f"Could not resolve {sides} above threshold {match_threshold}",
            failed=failed,
        )

    assert start_match is not None and end_match is not None
    nodes, steps, total_cost = find_weighted_path(
        graph,
        start_match.node_id,
        end_match.node_id,
        max_hops=max_hops,
        confidence_default=confidence_default,
        confidence_floor=confidence_floor,
        inferred_factor=inferred_factor,
    )

    start_info = EndpointInfo(
        query=start_q,
        node_id=start_match.node_id,
        score=start_match.final_score,
        node_type=start_match.node_type,
    )
    end_info = EndpointInfo(
        query=end_q,
        node_id=end_match.node_id,
        score=end_match.final_score,
        node_type=end_match.node_type,
    )

    deterministic = format_deterministic_explanation(start_q, end_q, nodes, steps)
    explanation = deterministic
    mode: ExplanationMode = "deterministic"
    expl_status: ExplanationStatus = "ok"
    expl_detail: str | None = None

    if want_llm_explain and steps:
        explanation, mode, expl_status, expl_detail = _polish_explanation(
            deterministic,
            steps,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            chat_fn=chat_fn,
        )
        if expl_status != "ok":
            explanation = deterministic
            mode = "deterministic"
    elif want_llm_explain and not steps:
        expl_status = "skipped"
        expl_detail = "LLM polish skipped for trivial path"

    answer = build_path_answer(
        start=start_info,
        end=end_info,
        nodes=nodes,
        steps=steps,
        total_cost=total_cost,
        explanation=explanation,
        explanation_mode=mode,
    )

    written: Path | None = None
    if output_path is not None:
        written = write_path_answer(answer, Path(output_path))

    return PathResult(
        answer=answer,
        embed_note=embed_note,
        explanation_status=expl_status,
        explanation_detail=expl_detail,
        output_path=written,
    )


__all__ = [
    "DEFAULT_CONFIDENCE",
    "DEFAULT_CONFIDENCE_FLOOR",
    "DEFAULT_INFERRED_FACTOR",
    "DEFAULT_MATCH_THRESHOLD",
    "DEFAULT_MAX_HOPS",
    "TYPE_BASE",
    "EndpointInfo",
    "EndpointUnresolvedError",
    "NoPathError",
    "PATH_ANSWER_KIND",
    "PATH_ANSWER_VERSION",
    "PathAnswer",
    "PathError",
    "PathResult",
    "PathStep",
    "PathTooLongError",
    "build_path_answer",
    "edge_cost",
    "find_path",
    "find_weighted_path",
    "format_deterministic_explanation",
    "path_answer_to_dict",
    "resolve_endpoint",
    "write_path_answer",
]
