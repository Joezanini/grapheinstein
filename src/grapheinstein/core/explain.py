"""Explain concept: match nodes, extract neighborhood subgraph, optional LLM summary."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Sequence

import networkx as nx

from grapheinstein.core.graph import (
    GraphError,
    artifact_to_digraph,
    load_artifact,
    to_artifact_dict,
    write_artifact_dict,
)
from grapheinstein.core.match import score_nodes, select_matches
from grapheinstein.core.parsers.llm_ollama import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    OllamaError,
    check_ready,
    chat_text,
    embed_texts,
)

SummaryStatus = Literal["ok", "skipped", "failed"]

EXPLAIN_SYSTEM_PROMPT = (
    "You explain a concept in a software project using only the provided "
    "knowledge-graph neighborhood. Do not invent entities, files, or relations "
    "that are not listed. Be concise (a short paragraph)."
)


class ExplainError(Exception):
    """Base error for explain failures."""


class NoMatchError(ExplainError):
    """Raised when no node scores above the match threshold."""


@dataclass(frozen=True)
class ExplainResult:
    output_path: Path
    match_ids: tuple[str, ...]
    match_scores: dict[str, float]
    hops: int
    truncated: bool
    summary_status: SummaryStatus
    summary_text: str | None
    summary_detail: str | None
    embed_note: str | None


def undirected_neighborhood(
    graph: nx.DiGraph,
    seeds: Sequence[str] | list[str],
    *,
    hops: int,
    node_cap: int = 500,
) -> tuple[set[str], bool]:
    """
    Collect nodes within undirected distance ``hops`` of any seed.
    Returns (node_ids, truncated).
    """
    if hops not in (1, 2):
        raise ExplainError(f"hops must be 1 or 2, got {hops}")
    seed_set = {s for s in seeds if s in graph}
    if not seed_set:
        return set(), False

    undirected = graph.to_undirected(as_view=True)
    included: set[str] = set(seed_set)
    frontier = set(seed_set)
    for _ in range(hops):
        nxt: set[str] = set()
        for node in frontier:
            for neighbor in undirected.neighbors(node):
                if neighbor not in included:
                    nxt.add(neighbor)
        for neighbor in sorted(nxt):  # stable growth for truncation
            if len(included) >= node_cap:
                return included, True
            included.add(neighbor)
        frontier = nxt
        if not frontier:
            break

    if len(included) > node_cap:
        # Defensive: BFS truncate keeping seeds first
        ordered: list[str] = []
        seen: set[str] = set()
        q: deque[str] = deque(sorted(seed_set))
        while q and len(ordered) < node_cap:
            cur = q.popleft()
            if cur in seen:
                continue
            seen.add(cur)
            ordered.append(cur)
            for neighbor in sorted(undirected.neighbors(cur)):
                if neighbor not in seen:
                    q.append(neighbor)
        return set(ordered), True

    return included, False


def build_explanation_artifact(
    source: dict[str, Any],
    *,
    node_ids: set[str],
    concept: str,
    match_ids: list[str],
    match_scores: dict[str, float],
    hops: int,
    truncated: bool,
) -> dict[str, Any]:
    """Build a validated-ready schema 6.0.0 explanation subgraph dict."""
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
    sub.graph["explained_concept"] = concept
    sub.graph["explain_match_ids"] = list(match_ids)
    sub.graph["explain_hops"] = int(hops)
    sub.graph["explain_match_scores"] = {k: float(v) for k, v in match_scores.items()}
    if truncated:
        sub.graph["explain_truncated"] = True

    artifact = to_artifact_dict(sub)
    # Ensure explain metadata survives even if to_artifact_dict is selective
    gmeta = artifact.setdefault("graph", {})
    gmeta["explained_concept"] = concept
    gmeta["explain_match_ids"] = list(match_ids)
    gmeta["explain_hops"] = int(hops)
    gmeta["generated_at"] = now
    gmeta["explain_match_scores"] = {k: float(v) for k, v in match_scores.items()}
    if truncated:
        gmeta["explain_truncated"] = True
    if project_root:
        gmeta["project_root"] = project_root
    return artifact


def _compact_neighborhood_facts(artifact: dict[str, Any]) -> str:
    lines: list[str] = ["Nodes:"]
    for node in artifact.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        meta = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
        name = meta.get("name") or ""
        lines.append(f"- {node.get('id')} (type={node.get('type')}, name={name})")
    lines.append("Edges:")
    for link in artifact.get("links") or []:
        if not isinstance(link, dict):
            continue
        lines.append(
            f"- {link.get('source')} -[{link.get('type')}/{link.get('provenance')}]-> "
            f"{link.get('target')}"
        )
    return "\n".join(lines)


def summarize_neighborhood(
    *,
    concept: str,
    artifact: dict[str, Any],
    model: str,
    base_url: str,
    chat_fn: Callable[..., str] | None = None,
    list_models_fn: Callable[[str], list[str]] | None = None,
) -> tuple[SummaryStatus, str | None, str | None]:
    """Return (status, text, detail)."""
    ready, msg = check_ready(model=model, base_url=base_url, list_models_fn=list_models_fn)
    if not ready:
        return "skipped", None, msg.replace("LLM enrichment skipped", "Summary skipped")

    facts = _compact_neighborhood_facts(artifact)
    user_content = (
        f"Concept query: {concept}\n"
        f"Matched ids: {artifact.get('graph', {}).get('explain_match_ids')}\n"
        f"Neighborhood facts:\n{facts}\n"
        "Write a short natural-language explanation."
    )
    fn = chat_fn or chat_text
    try:
        text = fn(
            model=model,
            user_content=user_content,
            base_url=base_url,
            system=EXPLAIN_SYSTEM_PROMPT,
        )
    except OllamaError as exc:
        return "failed", None, f"Summary failed: {exc}"
    except Exception as exc:  # noqa: BLE001
        return "failed", None, f"Summary failed: {exc}"
    if not isinstance(text, str) or not text.strip():
        return "failed", None, "Summary failed: empty model response"
    return "ok", text.strip(), None


def explain_concept(
    concept: str,
    input_path: Path,
    output_path: Path,
    *,
    hops: int = 2,
    top_n: int = 3,
    match_threshold: float = 0.55,
    node_cap: int = 500,
    want_summary: bool = True,
    llm_model: str = DEFAULT_MODEL,
    llm_base_url: str = DEFAULT_BASE_URL,
    use_embeddings: bool = True,
    chat_fn: Callable[..., str] | None = None,
    embed_fn: Callable[[list[str]], list[list[float]]] | None = None,
    list_models_fn: Callable[[str], list[str]] | None = None,
) -> ExplainResult:
    """
    Match concept, write neighborhood subgraph, optionally summarize.
    Raises NoMatchError / ExplainError / GraphError / FileNotFoundError.
    """
    query = concept.strip()
    if not query:
        raise ExplainError("Concept must be a non-empty string")
    if hops not in (1, 2):
        raise ExplainError(f"hops must be 1 or 2, got {hops}")
    if not (0.0 <= match_threshold <= 1.0):
        raise ExplainError("match_threshold must be in [0.0, 1.0]")
    if top_n < 1:
        raise ExplainError("top_n must be >= 1")
    if node_cap < 1:
        raise ExplainError("node_cap must be >= 1")

    source = load_artifact(input_path.expanduser())
    nodes = source.get("nodes") or []
    if not isinstance(nodes, list) or not nodes:
        raise NoMatchError(f"No nodes matched concept {query!r}")

    active_embed: Callable[[list[str]], list[list[float]]] | None = None
    embed_note: str | None = None
    if use_embeddings:
        if embed_fn is not None:
            active_embed = embed_fn
        else:
            ready, ready_msg = check_ready(
                model=llm_model,
                base_url=llm_base_url,
                list_models_fn=list_models_fn,
            )
            if ready:

                def _default_embed(texts: list[str]) -> list[list[float]]:
                    return embed_texts(texts, model=llm_model, base_url=llm_base_url)

                active_embed = _default_embed
            else:
                embed_note = ready_msg.replace(
                    "LLM enrichment skipped", "Vector matching skipped"
                )

    candidates, scored_note = score_nodes(nodes, query, embed_fn=active_embed)
    if scored_note:
        embed_note = scored_note
    matches = select_matches(candidates, threshold=match_threshold, top_n=top_n)
    if not matches:
        raise NoMatchError(
            f"No nodes matched concept {query!r} above threshold {match_threshold}"
        )

    match_ids = [m.node_id for m in matches]
    match_scores = {m.node_id: m.final_score for m in matches}
    digraph = artifact_to_digraph(source)
    node_ids, truncated = undirected_neighborhood(
        digraph, match_ids, hops=hops, node_cap=node_cap
    )
    artifact = build_explanation_artifact(
        source,
        node_ids=node_ids,
        concept=query,
        match_ids=match_ids,
        match_scores=match_scores,
        hops=hops,
        truncated=truncated,
    )
    written = write_artifact_dict(artifact, output_path.expanduser(), compress=False)

    summary_status: SummaryStatus = "skipped"
    summary_text: str | None = None
    summary_detail: str | None = None
    if want_summary:
        summary_status, summary_text, summary_detail = summarize_neighborhood(
            concept=query,
            artifact=artifact,
            model=llm_model,
            base_url=llm_base_url,
            chat_fn=chat_fn,
            list_models_fn=list_models_fn,
        )
    else:
        summary_detail = "Summary skipped: --no-summary"

    return ExplainResult(
        output_path=written,
        match_ids=tuple(match_ids),
        match_scores=match_scores,
        hops=hops,
        truncated=truncated,
        summary_status=summary_status,
        summary_text=summary_text,
        summary_detail=summary_detail,
        embed_note=embed_note,
    )


__all__ = [
    "EXPLAIN_SYSTEM_PROMPT",
    "ExplainError",
    "ExplainResult",
    "NoMatchError",
    "build_explanation_artifact",
    "explain_concept",
    "summarize_neighborhood",
    "undirected_neighborhood",
]
