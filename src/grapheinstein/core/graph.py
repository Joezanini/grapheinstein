"""NetworkX graph construction and graph.json persistence (schema 3.0.0)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
from networkx.readwrite import json_graph

SCHEMA_VERSION = "3.0.0"
FILE_DIR_TYPES = frozenset({"file", "dir"})
CODE_NODE_TYPES = frozenset({"function", "class", "method"})
NODE_TYPES = FILE_DIR_TYPES | CODE_NODE_TYPES
INVENTORY_EDGE_TYPES = frozenset({"contains", "references"})
CODE_EDGE_TYPES = frozenset({"defines", "imports", "calls"})
EDGE_TYPES = INVENTORY_EDGE_TYPES | CODE_EDGE_TYPES
PROVENANCE_VALUES = frozenset({"extracted", "inferred"})
CODE_METADATA_REQUIRED = frozenset({"name", "language", "file", "start_line"})


@dataclass(frozen=True)
class GraphStats:
    file_count: int
    directory_count: int
    function_count: int
    class_count: int
    method_count: int
    total_nodes: int
    contains_count: int
    references_count: int
    defines_count: int
    imports_count: int
    calls_count: int
    project_root: str | None
    graph_path: str
    parse_skips: int = 0


class GraphError(Exception):
    """Raised when a graph artifact cannot be loaded or validated."""


def new_inventory_graph(project_root: Path) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.graph["project_root"] = str(project_root.resolve())
    graph.graph["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    add_node(graph, ".", "dir")
    return graph


def add_node(
    graph: nx.DiGraph,
    node_id: str,
    node_type: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    if node_type not in NODE_TYPES:
        raise ValueError(f"Invalid node type: {node_type}")
    graph.add_node(node_id, type=node_type, metadata=dict(metadata or {}))


def code_entity_id(file_id: str, kind: str, name: str, start_line: int) -> str:
    return f"{file_id}::{kind}::{name}::{start_line}"


def add_code_entity(
    graph: nx.DiGraph,
    *,
    file_id: str,
    kind: str,
    name: str,
    start_line: int,
    language: str,
    end_line: int | None = None,
    qualified_name: str | None = None,
) -> str:
    """Add a function/class/method node. Returns node id."""
    if kind not in CODE_NODE_TYPES:
        raise ValueError(f"Invalid code entity kind: {kind}")
    node_id = code_entity_id(file_id, kind, name, start_line)
    metadata: dict[str, Any] = {
        "name": name,
        "language": language,
        "file": file_id,
        "start_line": int(start_line),
    }
    if end_line is not None:
        metadata["end_line"] = int(end_line)
    if qualified_name:
        metadata["qualified_name"] = qualified_name
    if node_id not in graph:
        add_node(graph, node_id, kind, metadata=metadata)
    return node_id


def add_contains_edge(graph: nx.DiGraph, parent_id: str, child_id: str) -> None:
    graph.add_edge(parent_id, child_id, type="contains", provenance="extracted")


def add_references_edge(graph: nx.DiGraph, source_id: str, target_id: str) -> bool:
    """Add a references edge. Returns True if a new edge was created."""
    if source_id == target_id:
        return False
    if graph.has_edge(source_id, target_id):
        existing = graph.edges[source_id, target_id]
        if existing.get("type") == "references":
            return False
    graph.add_edge(source_id, target_id, type="references", provenance="extracted")
    return True


def add_defines_edge(graph: nx.DiGraph, source_id: str, target_id: str) -> bool:
    return _add_typed_edge(graph, source_id, target_id, "defines")


def add_imports_edge(graph: nx.DiGraph, source_id: str, target_id: str) -> bool:
    return _add_typed_edge(graph, source_id, target_id, "imports")


def add_calls_edge(graph: nx.DiGraph, source_id: str, target_id: str) -> bool:
    return _add_typed_edge(graph, source_id, target_id, "calls")


def _add_typed_edge(graph: nx.DiGraph, source_id: str, target_id: str, edge_type: str) -> bool:
    if source_id == target_id:
        return False
    if source_id not in graph or target_id not in graph:
        return False
    # DiGraph allows one edge per pair; skip if same type already present
    if graph.has_edge(source_id, target_id):
        if graph.edges[source_id, target_id].get("type") == edge_type:
            return False
        # Different relationship already occupies the pair — skip to keep Multigraph=false
        return False
    graph.add_edge(source_id, target_id, type=edge_type, provenance="extracted")
    return True


def ensure_directory_chain(graph: nx.DiGraph, relative_dir: str) -> None:
    """Ensure directory node and ancestors exist with contains edges."""
    if relative_dir in {"", "."}:
        return
    parts = Path(relative_dir).parts
    parent = "."
    for i in range(len(parts)):
        current = "/".join(parts[: i + 1])
        if current not in graph:
            add_node(graph, current, "dir")
            add_contains_edge(graph, parent, current)
        parent = current


def to_artifact_dict(graph: nx.DiGraph) -> dict[str, Any]:
    data = json_graph.node_link_data(graph, edges="links")
    data["schema_version"] = SCHEMA_VERSION
    data["directed"] = True
    data["multigraph"] = False
    nodes = []
    for node in data.get("nodes", []):
        node_id = node["id"]
        attrs = graph.nodes[node_id]
        nodes.append(
            {
                "id": node_id,
                "type": attrs.get("type", node.get("type")),
                "metadata": dict(attrs.get("metadata") or node.get("metadata") or {}),
            }
        )
    data["nodes"] = nodes
    links = []
    for link in data.get("links", []):
        links.append(
            {
                "source": link["source"],
                "target": link["target"],
                "type": link.get("type", "contains"),
                "provenance": link.get("provenance", "extracted"),
            }
        )
    data["links"] = links
    graph_meta: dict[str, Any] = {
        "project_root": graph.graph.get("project_root", ""),
        "generated_at": graph.graph.get("generated_at", ""),
    }
    languages = graph.graph.get("languages")
    if languages is not None:
        graph_meta["languages"] = list(languages)
    data["graph"] = graph_meta
    return data


def save_graph(graph: nx.DiGraph, output_path: Path) -> Path:
    path = output_path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    artifact = to_artifact_dict(graph)
    try:
        path.write_text(json.dumps(artifact, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    except OSError as exc:
        raise OSError(f"Cannot write graph to {path}: {exc}") from exc
    return path.resolve()


def _reject_old_node_shape(node: Any, path: Path) -> None:
    if not isinstance(node, dict):
        raise GraphError(f"Graph file {path} has invalid node entry (expected object)")
    if "kind" in node or node.get("type") == "directory":
        raise GraphError(
            f"Graph file {path} uses unsupported pre-2.0.0 node shape "
            f"(kind/directory). Re-index the project to produce schema {SCHEMA_VERSION}."
        )


def _validate_code_metadata(node: dict[str, Any], path: Path) -> None:
    meta = node["metadata"]
    missing = CODE_METADATA_REQUIRED - set(meta)
    if missing:
        raise GraphError(
            f"Graph file {path} code entity {node.get('id')!r} missing metadata keys "
            f"{sorted(missing)}"
        )
    if not isinstance(meta.get("name"), str):
        raise GraphError(f"Graph file {path} code entity name must be a string")
    if not isinstance(meta.get("language"), str):
        raise GraphError(f"Graph file {path} code entity language must be a string")
    if not isinstance(meta.get("file"), str):
        raise GraphError(f"Graph file {path} code entity file must be a string")
    start_line = meta.get("start_line")
    if not isinstance(start_line, int) or isinstance(start_line, bool) or start_line < 1:
        raise GraphError(
            f"Graph file {path} code entity start_line must be a positive integer"
        )


def validate_artifact(data: dict[str, Any], path: Path) -> None:
    for key in ("schema_version", "nodes", "links", "graph"):
        if key not in data:
            raise GraphError(f"Graph file {path} missing required field {key!r}")
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise GraphError(
            f"Graph file {path} has unsupported schema_version {version!r}; "
            f"expected {SCHEMA_VERSION!r}. Re-index the project."
        )
    if not isinstance(data["nodes"], list):
        raise GraphError(f"Graph file {path} field 'nodes' must be an array")
    if not isinstance(data["links"], list):
        raise GraphError(f"Graph file {path} field 'links' must be an array")
    if not isinstance(data["graph"], dict):
        raise GraphError(f"Graph file {path} field 'graph' must be an object")

    for node in data["nodes"]:
        _reject_old_node_shape(node, path)
        if "id" not in node or "type" not in node or "metadata" not in node:
            raise GraphError(
                f"Graph file {path} nodes must include id, type, and metadata"
            )
        if node["type"] not in NODE_TYPES:
            raise GraphError(
                f"Graph file {path} has invalid node type {node['type']!r}; "
                f"expected one of {sorted(NODE_TYPES)}"
            )
        if not isinstance(node["metadata"], dict):
            raise GraphError(f"Graph file {path} node metadata must be an object")
        if node["type"] in CODE_NODE_TYPES:
            _validate_code_metadata(node, path)

    for link in data["links"]:
        if not isinstance(link, dict):
            raise GraphError(f"Graph file {path} has invalid link entry")
        for key in ("source", "target", "type", "provenance"):
            if key not in link:
                raise GraphError(f"Graph file {path} links must include {key!r}")
        if link["type"] not in EDGE_TYPES:
            raise GraphError(f"Graph file {path} has invalid edge type {link['type']!r}")
        if link["provenance"] not in PROVENANCE_VALUES:
            raise GraphError(
                f"Graph file {path} has invalid provenance {link['provenance']!r}"
            )


def load_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GraphError(f"Invalid graph JSON in {path}: {exc}") from exc
    except OSError as exc:
        raise GraphError(f"Cannot read graph file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise GraphError(f"Graph file {path} must contain a JSON object")
    nodes = data.get("nodes")
    if isinstance(nodes, list):
        for node in nodes:
            if isinstance(node, dict) and ("kind" in node or node.get("type") == "directory"):
                raise GraphError(
                    f"Graph file {path} uses unsupported pre-2.0.0 node shape "
                    f"(kind/directory). Re-index the project to produce schema {SCHEMA_VERSION}."
                )
    validate_artifact(data, path)
    return data


def stats_from_artifact(
    data: dict[str, Any],
    graph_path: Path,
    *,
    parse_skips: int = 0,
) -> GraphStats:
    nodes = data.get("nodes") or []
    links = data.get("links") or []
    file_count = sum(1 for n in nodes if n.get("type") == "file")
    directory_count = sum(1 for n in nodes if n.get("type") == "dir")
    function_count = sum(1 for n in nodes if n.get("type") == "function")
    class_count = sum(1 for n in nodes if n.get("type") == "class")
    method_count = sum(1 for n in nodes if n.get("type") == "method")
    contains_count = sum(1 for link in links if link.get("type") == "contains")
    references_count = sum(1 for link in links if link.get("type") == "references")
    defines_count = sum(1 for link in links if link.get("type") == "defines")
    imports_count = sum(1 for link in links if link.get("type") == "imports")
    calls_count = sum(1 for link in links if link.get("type") == "calls")
    project_root = None
    graph_meta = data.get("graph") or {}
    if isinstance(graph_meta, dict):
        project_root = graph_meta.get("project_root")
    return GraphStats(
        file_count=file_count,
        directory_count=directory_count,
        function_count=function_count,
        class_count=class_count,
        method_count=method_count,
        total_nodes=len(nodes),
        contains_count=contains_count,
        references_count=references_count,
        defines_count=defines_count,
        imports_count=imports_count,
        calls_count=calls_count,
        project_root=project_root,
        graph_path=str(graph_path.resolve()),
        parse_skips=parse_skips,
    )
