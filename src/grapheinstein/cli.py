"""Typer CLI for Grapheinstein."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from grapheinstein.core.graph import GraphError, load_artifact, stats_from_artifact
from grapheinstein.core.index import index_project
from grapheinstein.core.parsers import LanguageError, parse_languages_csv
from grapheinstein.core.visualize import load_graph_for_visualize, print_summary, write_dot
from grapheinstein.utils import (
    ConfigError,
    console,
    load_config,
    setup_logging,
)

cli = typer.Typer(
    name="grapheinstein",
    help="Local-first project knowledge graph CLI",
    no_args_is_help=True,
    add_completion=False,
)

_KNOWN_COMMANDS = frozenset({"index", "status", "visualize"})
_OPTS_WITH_VALUE = frozenset(
    {"--output", "-o", "--config", "--input", "-i", "--dot", "--languages"}
)


def prepend_index_if_needed(args: list[str]) -> list[str]:
    """
    Support `grapheinstein PROJECT_PATH` as an alias for `grapheinstein index PROJECT_PATH`.
    """
    if not args:
        return args
    i = 0
    while i < len(args):
        token = args[i]
        if token in {"--help", "-h"}:
            return args
        if token.startswith("-"):
            if token in _OPTS_WITH_VALUE:
                i += 2
            else:
                i += 1
            continue
        if token in _KNOWN_COMMANDS:
            return args
        return [*args[:i], "index", *args[i:]]
    return args


def _fail(message: str, code: int = 1) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(code)


def _print_index_summary(stats, output_path: Path) -> None:
    table = Table(title="Index complete", show_header=True, header_style="bold")
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
    if stats.parse_skips:
        table.add_row("Parse skips", str(stats.parse_skips))
    table.add_row("Output", str(output_path))
    console.print(table)


def _run_index(
    project_path: Path,
    *,
    output: Optional[Path],
    config: Optional[Path],
    languages: Optional[str],
    include_docs: bool,
    include_pdfs: bool,
) -> None:
    languages_override = None
    if languages is not None:
        try:
            languages_override = parse_languages_csv(languages)
        except LanguageError as exc:
            _fail(str(exc), 1)

    try:
        cfg = load_config(
            config_path=config,
            output_override=output,
            languages_override=languages_override,
        )
    except ConfigError as exc:
        _fail(str(exc), 1)

    setup_logging(cfg.log_level)
    output_path = Path(cfg.output)

    try:
        written, stats = index_project(
            project_path,
            output_path,
            languages=list(cfg.languages),
            include_docs=include_docs,
            include_pdfs=include_pdfs,
        )
    except FileNotFoundError as exc:
        _fail(str(exc), 1)
    except NotADirectoryError as exc:
        _fail(str(exc), 1)
    except OSError as exc:
        _fail(str(exc), 1)
    except Exception as exc:  # noqa: BLE001
        _fail(f"Indexing failed: {exc}", 1)

    _print_index_summary(stats, written)


@cli.command("index")
def index_cmd(
    project_path: Path = typer.Argument(..., help="Project folder to index"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Path for graph.json artifact",
    ),
    languages: Optional[str] = typer.Option(
        None,
        "--languages",
        help="Comma-separated languages for structure extraction (default: all)",
    ),
    include_docs: bool = typer.Option(
        False,
        "--include-docs",
        help="Enable Markdown/TXT/RST heading and link structure enrichment",
    ),
    include_pdfs: bool = typer.Option(
        False,
        "--include-pdfs",
        help="Enable PDF text extraction and section chunk enrichment",
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        help="YAML config file (overrides ~/.grapheinstein/config.yaml)",
    ),
) -> None:
    """Scan a project and write a portable graph.json digraph."""
    _run_index(
        project_path,
        output=output,
        config=config,
        languages=languages,
        include_docs=include_docs,
        include_pdfs=include_pdfs,
    )


@cli.command("status")
def status_cmd(
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Path to existing graph.json artifact",
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        help="YAML config file (overrides ~/.grapheinstein/config.yaml)",
    ),
) -> None:
    """Show stats for an existing graph artifact."""
    try:
        cfg = load_config(config_path=config, output_override=output)
    except ConfigError as exc:
        _fail(str(exc), 1)

    setup_logging(cfg.log_level)
    graph_path = Path(cfg.output).expanduser()

    if not graph_path.exists():
        console.print(f"[yellow]No index available:[/yellow] graph file not found at {graph_path}")
        raise typer.Exit(2)

    try:
        artifact = load_artifact(graph_path)
        stats = stats_from_artifact(artifact, graph_path)
    except GraphError as exc:
        _fail(str(exc), 1)

    table = Table(title="Graph status", show_header=True, header_style="bold")
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


@cli.command("visualize")
def visualize_cmd(
    input_path: Path = typer.Option(
        ...,
        "--input",
        "-i",
        help="Path to existing graph.json artifact",
    ),
    dot: Optional[Path] = typer.Option(
        None,
        "--dot",
        help="Optional path to write DOT export (summary still prints)",
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        help="YAML config file (overrides ~/.grapheinstein/config.yaml)",
    ),
) -> None:
    """Summarize a graph.json artifact; optionally export DOT."""
    try:
        cfg = load_config(config_path=config)
    except ConfigError as exc:
        _fail(str(exc), 1)

    setup_logging(cfg.log_level)

    try:
        artifact, stats = load_graph_for_visualize(input_path)
    except FileNotFoundError as exc:
        _fail(str(exc), 1)
    except GraphError as exc:
        _fail(str(exc), 1)

    print_summary(artifact, stats)

    if dot is not None:
        try:
            written = write_dot(artifact, dot)
        except OSError as exc:
            _fail(str(exc), 1)
        console.print(f"DOT written to {written}")


def app(
    args: Optional[list[str]] = None,
    *,
    prog_name: str = "grapheinstein",
    standalone_mode: bool = True,
) -> None:
    """Console entrypoint; rewrites bare project paths to `index`."""
    if args is None:
        normalized = prepend_index_if_needed(sys.argv[1:])
        sys.argv = [sys.argv[0], *normalized]
        cli(prog_name=prog_name, standalone_mode=standalone_mode)
    else:
        cli(args=prepend_index_if_needed(list(args)), prog_name=prog_name, standalone_mode=standalone_mode)


# Back-compat for tests that invoke the Typer app directly with full argv
app_typer = cli

if __name__ == "__main__":
    app()
