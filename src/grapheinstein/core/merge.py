"""Merge multiple portable graph.json artifacts into one."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from grapheinstein.core.graph import SCHEMA_VERSION, GraphError, load_artifact, validate_artifact


class MergeConflictError(GraphError):
    """Raised when merge inputs conflict on node or edge identity."""


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _node_payload(node: dict[str, Any]) -> tuple[Any, Any]:
    return (node.get("type"), node.get("metadata"))


def _edge_identity(link: dict[str, Any]) -> tuple[Any, ...]:
    return (
        link.get("source"),
        link.get("target"),
        link.get("type"),
        link.get("provenance"),
    )


def _edge_optional_attrs(link: dict[str, Any]) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    if "confidence" in link and link["confidence"] is not None:
        attrs["confidence"] = float(link["confidence"])
    if link.get("evidence"):
        attrs["evidence"] = link["evidence"]
    if link.get("reason"):
        attrs["reason"] = link["reason"]
    return attrs


def _identical_optional(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return a == b


def _shared_or_drop(values: list[Any]) -> Any | None:
    if not values:
        return None
    first = values[0]
    if all(v == first for v in values[1:]):
        return first
    return None


def merge_artifacts(
    artifacts: list[dict[str, Any]],
    *,
    source_paths: list[Path | str],
) -> dict[str, Any]:
    """
    Union nodes/links from validated artifacts.

    Raises MergeConflictError on incompatible same-id nodes or conflicting edges.
    Raises GraphError on schema mismatches or fewer than two inputs.
    """
    if len(artifacts) < 2:
        raise GraphError("merge requires at least two input graphs")
    if len(source_paths) != len(artifacts):
        raise GraphError("source_paths length must match artifacts")

    for i, data in enumerate(artifacts):
        version = data.get("schema_version")
        if version != SCHEMA_VERSION:
            raise GraphError(
                f"Graph file {source_paths[i]} has unsupported schema_version "
                f"{version!r}; expected {SCHEMA_VERSION!r}"
            )

    nodes_by_id: dict[str, dict[str, Any]] = {}
    node_sources: dict[str, str] = {}
    edges_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    edge_sources: dict[tuple[Any, ...], str] = {}

    for data, src in zip(artifacts, source_paths, strict=True):
        src_label = str(Path(src).expanduser().resolve()) if not isinstance(src, str) else src
        # Prefer resolved path strings when Path given
        if isinstance(src, Path):
            try:
                src_label = str(src.expanduser().resolve())
            except OSError:
                src_label = str(src)

        for node in data.get("nodes") or []:
            if not isinstance(node, dict) or "id" not in node:
                raise GraphError(f"Invalid node in {src_label}")
            nid = node["id"]
            payload = {
                "id": nid,
                "type": node["type"],
                "metadata": dict(node.get("metadata") or {}),
            }
            if nid in nodes_by_id:
                if _node_payload(nodes_by_id[nid]) != _node_payload(payload):
                    raise MergeConflictError(
                        f"Conflicting node id {nid!r} between "
                        f"{node_sources[nid]} and {src_label}"
                    )
            else:
                nodes_by_id[nid] = payload
                node_sources[nid] = src_label

        for link in data.get("links") or []:
            if not isinstance(link, dict):
                raise GraphError(f"Invalid link in {src_label}")
            key = _edge_identity(link)
            entry = {
                "source": link["source"],
                "target": link["target"],
                "type": link["type"],
                "provenance": link["provenance"],
                **_edge_optional_attrs(link),
            }
            if key in edges_by_key:
                existing_opts = _edge_optional_attrs(edges_by_key[key])
                if not _identical_optional(existing_opts, _edge_optional_attrs(entry)):
                    raise MergeConflictError(
                        f"Conflicting edge {key!r} between "
                        f"{edge_sources[key]} and {src_label}"
                    )
            else:
                edges_by_key[key] = entry
                edge_sources[key] = src_label

    resolved_from: list[str] = []
    for src in source_paths:
        if isinstance(src, Path):
            try:
                resolved_from.append(str(src.expanduser().resolve()))
            except OSError:
                resolved_from.append(str(src))
        else:
            resolved_from.append(str(src))

    graph_metas = [dict(a.get("graph") or {}) for a in artifacts]
    roots = [m.get("project_root") for m in graph_metas if m.get("project_root")]
    unique_roots: list[str] = []
    for r in roots:
        if r not in unique_roots:
            unique_roots.append(str(r))

    result_graph: dict[str, Any] = {
        "generated_at": _utc_now(),
        "merged": True,
        "merged_from": resolved_from,
    }
    if len(unique_roots) == 1:
        result_graph["project_root"] = unique_roots[0]
    elif len(unique_roots) > 1:
        result_graph["project_roots"] = unique_roots

    for key in (
        "languages",
        "include_docs",
        "include_pdfs",
        "transcribe_media",
        "enrich_llm",
        "llm_model",
        "parse_skips",
    ):
        values = [m[key] for m in graph_metas if key in m]
        shared = _shared_or_drop(values)
        if shared is not None and len(values) == len(graph_metas):
            result_graph[key] = shared

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "directed": True,
        "multigraph": False,
        "graph": result_graph,
        "nodes": list(nodes_by_id.values()),
        "links": list(edges_by_key.values()),
    }
    validate_artifact(result, Path("<merged>"))
    return result


def merge_paths(paths: list[Path], *, output_path: Path, compress: bool = False) -> Path:
    """Load paths, merge, and write the result. Returns written path."""
    from grapheinstein.core.graph import write_artifact_dict

    if len(paths) < 2:
        raise GraphError("merge requires at least two input graphs")
    artifacts = [load_artifact(p) for p in paths]
    merged = merge_artifacts(artifacts, source_paths=list(paths))
    return write_artifact_dict(merged, output_path, compress=compress)


__all__ = [
    "MergeConflictError",
    "merge_artifacts",
    "merge_paths",
]
