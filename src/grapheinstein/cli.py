"""Typer CLI for Grapheinstein."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.table import Table

from grapheinstein.api import index as api_index
from grapheinstein.api import query as api_query
from grapheinstein.core.cache import CacheStore
from grapheinstein.core.explain import ExplainError, NoMatchError, explain_concept
from grapheinstein.core.graph import GraphError, load_artifact, stats_from_artifact
from grapheinstein.core.index import MediaExtrasError
from grapheinstein.core.merge import MergeConflictError, merge_paths
from grapheinstein.core.path import (
    EndpointUnresolvedError,
    NoPathError,
    PathError,
    PathTooLongError,
    find_path,
    path_answer_to_dict,
)
from grapheinstein.core.query import (
    EmptyCorpusError,
    NoEvidenceError,
    QueryError,
)
from grapheinstein.core.visualize import load_graph_for_visualize, print_summary, write_dot
from grapheinstein.utils import (
    USER_CONFIG_PATH,
    ConfigError,
    console,
    load_config,
    setup_logging,
    write_config_template,
)

cli = typer.Typer(
    name="grapheinstein",
    help=(
        "Local-first project knowledge graph CLI. "
        "Index projects into portable graph.json, then explain/path/query locally."
    ),
    epilog=(
        "Examples:\n"
        "  grapheinstein init\n"
        "  grapheinstein init --output ./gs.yaml\n"
        "  grapheinstein index . --config ~/.grapheinstein/config.yaml\n"
        "  grapheinstein query \"How does auth work?\" -i graph.json -o sub.json --no-answer\n"
        "  grapheinstein serve --port 8000"
    ),
    no_args_is_help=True,
    add_completion=False,
)

_KNOWN_COMMANDS = frozenset(
    {
        "init",
        "index",
        "status",
        "visualize",
        "merge",
        "explain",
        "path",
        "query",
        "serve",
    }
)
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
        "--embedding-model",
        "--llm-base-url",
        "--hops",
        "--top-n",
        "--match-threshold",
        "--max-hops",
        "--k",
        "--max-file-size",
        "--cache-dir",
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
    if getattr(stats, "skipped_oversize", 0):
        table.add_row("Skipped oversize", str(stats.skipped_oversize))
    if getattr(stats, "cache_hits", 0) or getattr(stats, "cache_misses", 0):
        table.add_row("Cache hits", str(stats.cache_hits))
        table.add_row("Cache misses", str(stats.cache_misses))
    if getattr(stats, "cache_corrupt_recovered", 0):
        table.add_row("Cache recovered", str(stats.cache_corrupt_recovered))
    table.add_row("Output", str(output_path))
    console.print(table)


def _run_index(
    project_path: Path,
    *,
    output: Path | None,
    config: Path | None,
    languages: str | None,
    include_docs: bool,
    include_pdfs: bool,
    transcribe_media: bool,
    enrich_llm: bool,
    llm_model: str | None,
    llm_base_url: str | None,
    embedding_model: str | None,
    compress: bool,
    versioned: bool,
) -> None:
    try:
        result = api_index(
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
            embedding_model=embedding_model,
            compress=compress,
            versioned=versioned,
            show_progress=sys.stderr.isatty(),
        )
    except ConfigError as exc:
        _fail(str(exc), 1)
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

    _print_index_summary(result.stats, result.output_path)


@cli.command("init")
def init_cmd(
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Destination config path (default: ~/.grapheinstein/config.yaml)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing config file without prompting",
    ),
) -> None:
    """Create a commented starter config.yaml with documented defaults."""
    destination = (output if output is not None else USER_CONFIG_PATH).expanduser()
    if destination.exists() and not force:
        if sys.stdin.isatty() and sys.stderr.isatty():
            if not typer.confirm(
                f"Config already exists at {destination}. Overwrite?",
                default=False,
            ):
                _fail(
                    f"Config file already exists at {destination}; "
                    "re-run with --force to overwrite",
                    1,
                )
        else:
            _fail(
                f"Config file already exists at {destination}; "
                "use --force to overwrite (non-interactive)",
                1,
            )
    try:
        # Overwrite policy already enforced above; force write of the template.
        written = write_config_template(destination, force=True)
    except ConfigError as exc:
        _fail(str(exc), 1)
    console.print(f"Wrote config template to {written.resolve()}")


@cli.command("index")
def index_cmd(
    project_path: Path = typer.Argument(
        ...,
        help="Project folder to index (respects .gitignore and config ignored_patterns)",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Path for graph.json artifact (default: graph.json or config)",
    ),
    languages: str | None = typer.Option(
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
    llm_model: str | None = typer.Option(
        None,
        "--llm-model",
        help="Ollama model tag for LLM enrichment (default from config)",
    ),
    embedding_model: str | None = typer.Option(
        None,
        "--embedding-model",
        help="Ollama model tag for embeddings (default from config or llm_model)",
    ),
    llm_base_url: str | None = typer.Option(
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
    config: Path | None = typer.Option(
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
        embedding_model=embedding_model,
        compress=compress,
        versioned=versioned,
    )


@cli.command("merge")
def merge_cmd(
    inputs: list[Path] = typer.Argument(
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
    config: Path | None = typer.Option(
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
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Path to existing graph.json artifact",
    ),
    config: Path | None = typer.Option(
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
    hops: int | None = typer.Option(
        None,
        "--hops",
        help="Undirected neighborhood radius (1 or 2)",
    ),
    top_n: int | None = typer.Option(
        None,
        "--top-n",
        help="Maximum primary matches to include",
    ),
    match_threshold: float | None = typer.Option(
        None,
        "--match-threshold",
        help="Minimum match score in [0.0, 1.0]",
    ),
    llm_model: str | None = typer.Option(
        None,
        "--llm-model",
        help="Local Ollama model for summary text (default from config)",
    ),
    embedding_model: str | None = typer.Option(
        None,
        "--embedding-model",
        help="Local Ollama model for embeddings (default from config or llm_model)",
    ),
    llm_base_url: str | None = typer.Option(
        None,
        "--llm-base-url",
        help="Local Ollama base URL",
    ),
    no_summary: bool = typer.Option(
        False,
        "--no-summary",
        help="Skip local LLM summary; still write subgraph",
    ),
    config: Path | None = typer.Option(
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
            embedding_model_override=embedding_model,
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
            embedding_model=cfg.embedding_model,
            cache=CacheStore(cfg.cache_dir),
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


@cli.command("path")
def path_cmd(
    start: str = typer.Argument(..., help="Start concept phrase"),
    end: str = typer.Argument(..., help="End concept phrase"),
    input_path: Path = typer.Option(
        ...,
        "--input",
        "-i",
        help="Path to existing graph.json artifact",
    ),
    output_path: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional path to write path-answer JSON (same document as stdout)",
    ),
    match_threshold: float | None = typer.Option(
        None,
        "--match-threshold",
        help="Minimum match score in [0.0, 1.0] per endpoint",
    ),
    max_hops: int | None = typer.Option(
        None,
        "--max-hops",
        help="Maximum accepted path edge count",
    ),
    llm_model: str | None = typer.Option(
        None,
        "--llm-model",
        help="Local Ollama model for explanation polish (default from config)",
    ),
    embedding_model: str | None = typer.Option(
        None,
        "--embedding-model",
        help="Local Ollama model for embeddings (default from config or llm_model)",
    ),
    llm_base_url: str | None = typer.Option(
        None,
        "--llm-base-url",
        help="Local Ollama base URL",
    ),
    no_llm_explain: bool = typer.Option(
        False,
        "--no-llm-explain",
        help="Skip LLM polish; keep deterministic explanation",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="YAML config file (overrides ~/.grapheinstein/config.yaml)",
    ),
) -> None:
    """Find a preferred weighted path between two concepts and print a path answer."""
    import json

    try:
        cfg = load_config(
            config_path=config,
            llm_model_override=llm_model,
            llm_base_url_override=llm_base_url,
            embedding_model_override=embedding_model,
            path_match_threshold_override=match_threshold,
            path_max_hops_override=max_hops,
        )
    except ConfigError as exc:
        _fail(str(exc), 1)

    setup_logging(cfg.log_level)

    try:
        result = find_path(
            start,
            end,
            input_path,
            output_path=output_path,
            match_threshold=cfg.path_match_threshold,
            max_hops=cfg.path_max_hops,
            confidence_default=cfg.path_confidence_default,
            confidence_floor=cfg.path_confidence_floor,
            inferred_factor=cfg.path_provenance_inferred_factor,
            want_llm_explain=not no_llm_explain,
            llm_model=cfg.llm_model,
            llm_base_url=cfg.llm_base_url,
            embedding_model=cfg.embedding_model,
            cache=CacheStore(cfg.cache_dir),
        )
    except EndpointUnresolvedError as exc:
        _fail(str(exc), 1)
    except (NoPathError, PathTooLongError, PathError) as exc:
        _fail(str(exc), 1)
    except FileNotFoundError as exc:
        _fail(str(exc), 1)
    except GraphError as exc:
        _fail(str(exc), 1)
    except OSError as exc:
        _fail(str(exc), 1)

    payload = path_answer_to_dict(result.answer)
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))

    table = Table(title="Path complete", show_header=True, header_style="bold")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Start", f"{result.answer.start.node_id} ({result.answer.start.score:.2f})")
    table.add_row("End", f"{result.answer.end.node_id} ({result.answer.end.score:.2f})")
    table.add_row("Hops", str(result.answer.hop_count))
    table.add_row("Total cost", f"{result.answer.total_cost:.3f}")
    if result.output_path is not None:
        table.add_row("Output", str(result.output_path))
    table.add_row("Explanation", result.explanation_status)
    console.print(table)

    if result.embed_note:
        console.print(f"[yellow]{result.embed_note}[/yellow]")
    if result.explanation_detail and result.explanation_status != "ok":
        console.print(f"[yellow]{result.explanation_detail}[/yellow]")
    console.print("\n[bold]Explanation[/bold]")
    console.print(result.answer.explanation)


@cli.command("query")
def query_cmd(
    question: str = typer.Argument(..., help="Plain-language question to answer"),
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
        help="Destination path for supporting subgraph",
    ),
    k: int | None = typer.Option(
        None,
        "--k",
        help="Maximum primary retrieval hits (1-200)",
    ),
    hops: int | None = typer.Option(
        None,
        "--hops",
        help="Undirected expansion radius (1 or 2)",
    ),
    match_threshold: float | None = typer.Option(
        None,
        "--match-threshold",
        help="Minimum hit score in [0.0, 1.0]",
    ),
    llm_model: str | None = typer.Option(
        None,
        "--llm-model",
        help="Local Ollama model for answer text (default from config)",
    ),
    embedding_model: str | None = typer.Option(
        None,
        "--embedding-model",
        help="Local Ollama model for embeddings (default from config or llm_model)",
    ),
    llm_base_url: str | None = typer.Option(
        None,
        "--llm-base-url",
        help="Local Ollama base URL",
    ),
    no_answer: bool = typer.Option(
        False,
        "--no-answer",
        help="Skip local LLM answer; still write subgraph and visualization summary",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="YAML config file (overrides ~/.grapheinstein/config.yaml)",
    ),
) -> None:
    """Answer a plain-language question with hybrid retrieval and a cited subgraph."""
    import json

    try:
        envelope = api_query(
            question,
            input=input_path,
            output=output_path,
            config=config,
            k=k,
            hops=hops,
            match_threshold=match_threshold,
            no_answer=no_answer,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            embedding_model=embedding_model,
        )
    except ConfigError as exc:
        _fail(str(exc), 1)
    except (NoEvidenceError, EmptyCorpusError) as exc:
        _fail(str(exc), 1)
    except QueryError as exc:
        _fail(str(exc), 1)
    except FileNotFoundError as exc:
        _fail(str(exc), 1)
    except GraphError as exc:
        _fail(str(exc), 1)
    except OSError as exc:
        _fail(str(exc), 1)

    typer.echo(json.dumps(envelope, indent=2, ensure_ascii=False))

    hit_ids = list(envelope.get("hit_ids") or [])
    answer = envelope.get("answer") or {}
    viz = envelope.get("visualization") or {}
    table = Table(title="Query complete", show_header=True, header_style="bold")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Question", str(envelope.get("question") or question))
    table.add_row(
        "Hits",
        ", ".join(hit_ids[:5]) + ("…" if len(hit_ids) > 5 else ""),
    )
    table.add_row("k", str(envelope.get("k")))
    table.add_row("Hops", str(envelope.get("hops")))
    table.add_row("Truncated", "yes" if envelope.get("truncated") else "no")
    table.add_row("Output", str(envelope.get("output") or output_path))
    table.add_row("Answer", str(answer.get("status") or ""))
    console.print(table)

    console.print("\n[bold]Visualization summary[/bold]")
    types = viz.get("node_type_counts") or {}
    type_s = ", ".join(f"{t}={n}" for t, n in list(types.items())[:8])
    sample = ", ".join(viz.get("sample_hit_ids") or []) or "(none)"
    console.print(
        f"Supporting subgraph: {viz.get('node_count', 0)} nodes, "
        f"{viz.get('edge_count', 0)} edges\n"
        f"Node types: {type_s or '(none)'}\n"
        f"Primary hits (sample): {sample}\n"
        f"Truncated: {'yes' if viz.get('truncated') else 'no'}\n"
        f"Output: {viz.get('output_path') or envelope.get('output')}"
    )

    if envelope.get("embed_note"):
        console.print(f"[yellow]{envelope['embed_note']}[/yellow]")
    if envelope.get("truncated"):
        console.print(
            "[yellow]Neighborhood truncated to query_node_cap; "
            "graph.query_truncated=true[/yellow]"
        )
    if answer.get("status") == "ok" and answer.get("text"):
        console.print("\n[bold]Answer[/bold]")
        console.print(answer["text"])
    elif answer.get("detail"):
        console.print(f"[yellow]{answer['detail']}[/yellow]")


@cli.command("serve")
def serve_cmd(
    port: int = typer.Option(
        8000,
        "--port",
        help="TCP port to listen on (default: 8000)",
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help=(
            "Bind address (default: 127.0.0.1 loopback only). "
            "Binding beyond loopback exposes the API on the network without auth — "
            "use only on trusted networks."
        ),
    ),
) -> None:
    """Start optional local HTTP API (POST /index, POST /query). See docs/agent-integration.md."""
    from grapheinstein.serve import ServeExtrasError, run_server

    if port < 1 or port > 65535:
        _fail(f"Invalid port {port}; must be between 1 and 65535", 1)

    try:
        console.print(
            f"Starting Grapheinstein serve on http://{host}:{port} "
            "(see docs/agent-integration.md)"
        )
        run_server(host=host, port=port)
    except ServeExtrasError as exc:
        _fail(str(exc), 1)
    except OSError as exc:
        _fail(f"Failed to bind {host}:{port}: {exc}", 1)
    except Exception as exc:  # noqa: BLE001
        _fail(f"Serve failed: {exc}", 1)


@cli.command("visualize")
def visualize_cmd(
    input_path: Path = typer.Option(
        ...,
        "--input",
        "-i",
        help="Path to existing graph.json artifact",
    ),
    dot: Path | None = typer.Option(
        None,
        "--dot",
        help="Optional path to write DOT export (summary still prints)",
    ),
    config: Path | None = typer.Option(
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
    args: list[str] | None = None,
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
