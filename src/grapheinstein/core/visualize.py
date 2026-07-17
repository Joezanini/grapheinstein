"""Graph console summary and DOT export."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.table import Table

from grapheinstein.core.graph import GraphError, GraphStats, load_artifact, stats_from_artifact
from grapheinstein.utils import console


def load_graph_for_visualize(input_path: Path) -> tuple[dict[str, Any], GraphStats]:
    path = input_path.expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Graph file not found: {path}")
    artifact = load_artifact(path)
    stats = stats_from_artifact(artifact, path)
    return artifact, stats


def print_summary(artifact: dict[str, Any], stats: GraphStats, *, sample_limit: int = 5) -> None:
    table = Table(title="Graph summary", show_header=True, header_style="bold")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Files", str(stats.file_count))
    table.add_row("Directories", str(stats.directory_count))
    table.add_row("Functions", str(stats.function_count))
    table.add_row("Classes", str(stats.class_count))
    table.add_row("Methods", str(stats.method_count))
    table.add_row("Headings", str(stats.heading_count))
    table.add_row("Total nodes", str(stats.total_nodes))
    table.add_row("Contains edges", str(stats.contains_count))
    table.add_row("References edges", str(stats.references_count))
    table.add_row("Defines edges", str(stats.defines_count))
    table.add_row("Imports edges", str(stats.imports_count))
    table.add_row("Calls edges", str(stats.calls_count))
    table.add_row("Section-of edges", str(stats.section_of_count))
    table.add_row("Mentions edges", str(stats.mentions_count))
    table.add_row("Graph path", stats.graph_path)
    if stats.project_root:
        table.add_row("Project root", stats.project_root)
    console.print(table)

    nodes = artifact.get("nodes") or []
    links = artifact.get("links") or []
    if nodes:
        sample_nodes = [n.get("id", "?") for n in nodes[:sample_limit]]
        console.print(f"Sample nodes: {', '.join(sample_nodes)}")
    if links:
        sample_links = [
            f"{link.get('source')} -({link.get('type')})-> {link.get('target')}"
            for link in links[:sample_limit]
        ]
        console.print("Sample edges:")
        for line in sample_links:
            console.print(f"  {line}", markup=False)


def _dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def artifact_to_dot(artifact: dict[str, Any]) -> str:
    lines = ["digraph G {", '  rankdir="LR";']
    for node in artifact.get("nodes") or []:
        node_id = str(node.get("id", ""))
        node_type = str(node.get("type", ""))
        label = f"{node_id}\\n({node_type})"
        lines.append(f'  "{_dot_escape(node_id)}" [label="{_dot_escape(label)}"];')
    for link in artifact.get("links") or []:
        source = str(link.get("source", ""))
        target = str(link.get("target", ""))
        edge_type = str(link.get("type", ""))
        lines.append(
            f'  "{_dot_escape(source)}" -> "{_dot_escape(target)}" '
            f'[label="{_dot_escape(edge_type)}"];'
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_dot(artifact: dict[str, Any], output_path: Path) -> Path:
    path = output_path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    text = artifact_to_dot(artifact)
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise OSError(f"Cannot write DOT to {path}: {exc}") from exc
    return path.resolve()


__all__ = [
    "GraphError",
    "artifact_to_dot",
    "load_graph_for_visualize",
    "print_summary",
    "write_dot",
]
