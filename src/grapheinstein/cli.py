"""Typer CLI for Grapheinstein."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.table import Table

from grapheinstein.core.explain import ExplainError, NoMatchError, explain_concept
from grapheinstein.core.graph import GraphError, load_artifact, stats_from_artifact
from grapheinstein.core.index import MediaExtrasError, index_project
from grapheinstein.core.merge import MergeConflictError, merge_paths
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

_KNOWN_COMMANDS = frozenset({"index", "status", "visualize", "merge", "explain"})
_OPTS_WITH_VALUE = frozenset(
    {
        "--output",
        "-o",
        "--config",
        "--input",
        "-i",
        "--dot",
        "--languages",
        "--llm-model",
        "--llm-base-url",
        "--hops",
        "--top-n",
        "--match-threshold",
    }
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
    from rich.markup import escape

    console.print(f"[red]Error:[/red] {escape(message)}")
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
    table.add_row("Media texts", str(stats.media_text_count))
    table.add_row("Transcript chunks", str(stats.transcript_chunk_count))
    table.add_row("Concepts", str(stats.concept_count))
    table.add_row("Total nodes", str(stats.total_nodes))
    table.add_row("Contains edges", str(stats.contains_count))
    table.add_row("References edges", str(stats.references_count))
    table.add_row("Defines edges", str(stats.defines_count))
    table.add_row("Imports edges", str(stats.imports_count))
    table.add_row("Calls edges", str(stats.calls_count))
    table.add_row("Section-of edges", str(stats.section_of_count))
    table.add_row("Mentions edges", str(stats.mentions_count))
    table.add_row("Related-to edges", str(stats.related_to_count))
    table.add_row("Implements edges", str(stats.implements_count))
    table.add_row("Depends-on edges", str(stats.depends_on_count))
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
    transcribe_media: bool,
    enrich_llm: bool,
    llm_model: Optional[str],
    llm_base_url: Optional[str],
    compress: bool,
    versioned: bool,
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
            llm_model_override=llm_model,
            llm_base_url_override=llm_base_url,
            compress_override=True if compress else None,
            versioned_override=True if versioned else None,
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
            transcribe_media=transcribe_media,
            enrich_llm=enrich_llm,
            llm_model=cfg.llm_model,
            llm_base_url=cfg.llm_base_url,
            llm_confidence_threshold=cfg.llm_confidence_threshold,
            compress=cfg.compress,
            versioned=cfg.versioned,
        )
    except MediaExtrasError as exc:
        _fail(str(exc), 1)
    except GraphError as exc:
        _fail(str(exc), 1)
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
    transcribe_media: bool = typer.Option(
        False,
        "--transcribe-media",
        help="Enable image OCR, A/V transcription, and media linking",
    ),
    enrich_llm: bool = typer.Option(
        False,
        "--enrich-llm",
        help="Enable local LLM concept/relation enrichment via Ollama",
    ),
    llm_model: Optional[str] = typer.Option(
        None,
        "--llm-model",
        help="Ollama model tag (default: qwen3.5-2b-mlx:fp16-8gbGPU or config)",
    ),
    llm_base_url: Optional[str] = typer.Option(
        None,
        "--llm-base-url",
        help="Ollama base URL (default: http://localhost:11434 or config)",
    ),
    compress: bool = typer.Option(
        False,
        "--compress",
        help="Write gzip-compressed graph artifact (.json.gz)",
    ),
    versioned: bool = typer.Option(
        False,
        "--versioned",
        help="Also write next graph_vN.json[.gz] snapshot beside primary output",
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
        transcribe_media=transcribe_media,
        enrich_llm=enrich_llm,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        compress=compress,
        versioned=versioned,
    )


@cli.command("merge")
def merge_cmd(
    inputs: List[Path] = typer.Argument(
        ...,
        help="Two or more graph.json / graph.json.gz artifacts to combine",
    ),
    output: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Destination path for the merged graph",
    ),
    compress: bool = typer.Option(
        False,
        "--compress",
        help="Write gzip-compressed merged artifact (.json.gz)",
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        help="YAML config file (overrides ~/.grapheinstein/config.yaml)",
    ),
) -> None:
    """Combine two or more portable graphs into one."""
    try:
        cfg = load_config(
            config_path=config,
            compress_override=True if compress else None,
        )
    except ConfigError as exc:
        _fail(str(exc), 1)

    setup_logging(cfg.log_level)

    if len(inputs) < 2:
        _fail("merge requires at least two input graph files", 1)

    try:
        written = merge_paths(list(inputs), output_path=output, compress=cfg.compress)
        artifact = load_artifact(written)
        stats = stats_from_artifact(artifact, written)
    except MergeConflictError as exc:
        _fail(str(exc), 1)
    except GraphError as exc:
        _fail(str(exc), 1)
    except FileNotFoundError as exc:
        _fail(str(exc), 1)
    except OSError as exc:
        _fail(str(exc), 1)

    table = Table(title="Merge complete", show_header=True, header_style="bold")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Inputs", str(len(inputs)))
    table.add_row("Total nodes", str(stats.total_nodes))
    table.add_row("Total links", str(len(artifact.get("links") or [])))
    table.add_row("Output", str(written))
    console.print(table)


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
    table.add_row("Media texts", str(stats.media_text_count))
    table.add_row("Transcript chunks", str(stats.transcript_chunk_count))
    table.add_row("Concepts", str(stats.concept_count))
    table.add_row("Total nodes", str(stats.total_nodes))
    table.add_row("Contains edges", str(stats.contains_count))
    table.add_row("References edges", str(stats.references_count))
    table.add_row("Defines edges", str(stats.defines_count))
    table.add_row("Imports edges", str(stats.imports_count))
    table.add_row("Calls edges", str(stats.calls_count))
    table.add_row("Section-of edges", str(stats.section_of_count))
    table.add_row("Mentions edges", str(stats.mentions_count))
    table.add_row("Related-to edges", str(stats.related_to_count))
    table.add_row("Implements edges", str(stats.implements_count))
    table.add_row("Depends-on edges", str(stats.depends_on_count))
    table.add_row("Graph path", stats.graph_path)
    if stats.project_root:
        table.add_row("Project root", stats.project_root)
    console.print(table)


@cli.command("explain")
def explain_cmd(
    concept: str = typer.Argument(..., help="Concept phrase to match in the graph"),
    input_path: Path = typer.Option(
        ...,
        "--input",
        "-i",
        help="Path to existing graph.json artifact",
    ),
    output_path: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Destination path for explanation subgraph",
    ),
    hops: Optional[int] = typer.Option(
        None,
        "--hops",
        help="Undirected neighborhood radius (1 or 2)",
    ),
    top_n: Optional[int] = typer.Option(
        None,
        "--top-n",
        help="Maximum primary matches to include",
    ),
    match_threshold: Optional[float] = typer.Option(
        None,
        "--match-threshold",
        help="Minimum match score in [0.0, 1.0]",
    ),
    llm_model: Optional[str] = typer.Option(
        None,
        "--llm-model",
        help="Local Ollama model for summary (and embeddings when used)",
    ),
    llm_base_url: Optional[str] = typer.Option(
        None,
        "--llm-base-url",
        help="Local Ollama base URL",
    ),
    no_summary: bool = typer.Option(
        False,
        "--no-summary",
        help="Skip local LLM summary; still write subgraph",
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        help="YAML config file (overrides ~/.grapheinstein/config.yaml)",
    ),
) -> None:
    """Find concept nodes, write a neighborhood subgraph, and summarize with a local LLM."""
    try:
        cfg = load_config(
            config_path=config,
            llm_model_override=llm_model,
            llm_base_url_override=llm_base_url,
            explain_hops_override=hops,
            explain_top_n_override=top_n,
            explain_match_threshold_override=match_threshold,
        )
    except ConfigError as exc:
        _fail(str(exc), 1)

    setup_logging(cfg.log_level)

    try:
        result = explain_concept(
            concept,
            input_path,
            output_path,
            hops=cfg.explain_hops,
            top_n=cfg.explain_top_n,
            match_threshold=cfg.explain_match_threshold,
            node_cap=cfg.explain_node_cap,
            want_summary=not no_summary,
            llm_model=cfg.llm_model,
            llm_base_url=cfg.llm_base_url,
        )
    except NoMatchError as exc:
        _fail(str(exc), 1)
    except ExplainError as exc:
        _fail(str(exc), 1)
    except FileNotFoundError as exc:
        _fail(str(exc), 1)
    except GraphError as exc:
        _fail(str(exc), 1)
    except OSError as exc:
        _fail(str(exc), 1)

    table = Table(title="Explain complete", show_header=True, header_style="bold")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Concept", concept.strip())
    table.add_row("Matches", ", ".join(result.match_ids))
    table.add_row("Hops", str(result.hops))
    table.add_row("Truncated", "yes" if result.truncated else "no")
    table.add_row("Output", str(result.output_path))
    table.add_row("Summary", result.summary_status)
    console.print(table)

    if result.embed_note:
        console.print(f"[yellow]{result.embed_note}[/yellow]")
    if result.truncated:
        console.print(
            "[yellow]Neighborhood truncated to explain_node_cap; "
            "graph.explain_truncated=true[/yellow]"
        )
    if result.summary_status == "ok" and result.summary_text:
        console.print("\n[bold]Summary[/bold]")
        console.print(result.summary_text)
    elif result.summary_detail:
        console.print(f"[yellow]{result.summary_detail}[/yellow]")


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
