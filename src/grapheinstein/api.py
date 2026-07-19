"""Public Python API for agent / slash-command integration.

Importing this module MUST NOT require FastAPI or Uvicorn.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

from grapheinstein.core.cache import CacheStore
from grapheinstein.core.graph import GraphError, GraphStats, load_artifact
from grapheinstein.core.index import MediaExtrasError, index_project
from grapheinstein.core.parsers import LanguageError, parse_languages_csv
from grapheinstein.core.query import (
    EmptyCorpusError,
    NoEvidenceError,
    QueryError,
    run_query,
)
from grapheinstein.utils import (
    ConfigError,
    IndexTimeoutError,
    LargeRepoError,
    load_config,
    setup_logging,
)

__all__ = [
    "IndexResult",
    "index",
    "query",
    "stats_to_dict",
    "ConfigError",
    "GraphError",
    "MediaExtrasError",
    "QueryError",
    "EmptyCorpusError",
    "NoEvidenceError",
    "LargeRepoError",
    "IndexTimeoutError",
]


@dataclass(frozen=True)
class IndexResult:
    """Result of a successful API index call."""

    output_path: Path
    stats: GraphStats | dict[str, Any]
    artifact: dict[str, Any] | None = None


def _stats_as_dict(stats: GraphStats | dict[str, Any]) -> dict[str, Any]:
    if isinstance(stats, dict):
        return dict(stats)
    if is_dataclass(stats):
        return asdict(stats)
    return {
        "total_nodes": getattr(stats, "total_nodes", 0),
        "graph_path": str(getattr(stats, "graph_path", "")),
    }


def _normalize_languages(
    languages: str | Sequence[str] | None,
) -> list[str] | None:
    if languages is None:
        return None
    if isinstance(languages, str):
        try:
            return list(parse_languages_csv(languages))
        except LanguageError as exc:
            raise ConfigError(str(exc)) from exc
    try:
        return list(languages)
    except TypeError as exc:
        raise ConfigError("languages must be a string or sequence of strings") from exc


def index(
    project_path: str | Path,
    *,
    output: str | Path | None = None,
    config: str | Path | None = None,
    languages: str | Sequence[str] | None = None,
    include_docs: bool = False,
    include_pdfs: bool = False,
    transcribe_media: bool = False,
    enrich_llm: bool = False,
    llm_model: str | None = None,
    llm_base_url: str | None = None,
    embedding_model: str | None = None,
    compress: bool = False,
    versioned: bool = False,
    include_artifact: bool = False,
    show_progress: bool = False,
    code_only: bool = False,
    include_generated_docs: bool = False,
    allow_large_repo: bool = False,
    max_reference_scan_bytes: int | None = None,
    max_reference_scan_ops: int | None = None,
    max_non_code_share: float | None = None,
    max_total_bytes: int | None = None,
    max_file_count: int | None = None,
    timeout_seconds: int | None = None,
) -> IndexResult:
    """
    Index a project folder into a portable graph (CLI `index` semantics).

    Raises FileNotFoundError, NotADirectoryError, OSError, ConfigError,
    GraphError, MediaExtrasError, LargeRepoError, IndexTimeoutError on hard
    failures — never returns an empty success.
    """
    languages_override = _normalize_languages(languages)
    cfg = load_config(
        config_path=Path(config).expanduser() if config is not None else None,
        output_override=Path(output).expanduser() if output is not None else None,
        languages_override=languages_override,
        llm_model_override=llm_model,
        llm_base_url_override=llm_base_url,
        embedding_model_override=embedding_model,
        compress_override=True if compress else None,
        versioned_override=True if versioned else None,
        code_only_override=True if code_only else None,
        include_generated_docs_override=True if include_generated_docs else None,
        allow_large_repo_override=True if allow_large_repo else None,
        max_reference_scan_bytes_override=max_reference_scan_bytes,
        max_reference_scan_ops_override=max_reference_scan_ops,
        max_non_code_share_override=max_non_code_share,
        max_total_bytes_override=max_total_bytes,
        max_file_count_override=max_file_count,
        timeout_seconds_override=timeout_seconds,
    )
    setup_logging(cfg.log_level)
    output_path = Path(cfg.output)

    written, stats = index_project(
        Path(project_path),
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
        ignored_patterns=list(cfg.ignored_patterns),
        max_file_size=cfg.max_file_size,
        cache_dir=cfg.cache_dir,
        embedding_model=cfg.embedding_model,
        show_progress=show_progress,
        code_only=cfg.code_only,
        include_generated_docs=cfg.include_generated_docs,
        max_reference_scan_bytes=cfg.max_reference_scan_bytes,
        max_reference_scan_ops=cfg.max_reference_scan_ops,
        max_non_code_share=cfg.max_non_code_share,
        max_total_bytes=cfg.max_total_bytes,
        max_file_count=cfg.max_file_count,
        timeout_seconds=cfg.timeout_seconds,
        large_repo_policy=cfg.large_repo_policy,
    )

    artifact: dict[str, Any] | None = None
    if include_artifact:
        artifact = load_artifact(written)

    return IndexResult(output_path=written, stats=stats, artifact=artifact)


def query(
    question: str,
    *,
    input: str | Path,
    output: str | Path | None = None,
    config: str | Path | None = None,
    k: int | None = None,
    hops: int | None = None,
    match_threshold: float | None = None,
    no_answer: bool = False,
    llm_model: str | None = None,
    llm_base_url: str | None = None,
    embedding_model: str | None = None,
) -> dict[str, Any]:
    """
    Answer a natural-language question over a graph (CLI `query` semantics).

    Returns the query-answer JSON envelope (schema_version 1.0.0).
    """
    input_path = Path(input).expanduser()
    if output is not None:
        output_path = Path(output).expanduser()
    else:
        output_path = input_path.parent / "subgraph.json"

    cfg = load_config(
        config_path=Path(config).expanduser() if config is not None else None,
        llm_model_override=llm_model,
        llm_base_url_override=llm_base_url,
        embedding_model_override=embedding_model,
        query_k_override=k,
        query_hops_override=hops,
        query_match_threshold_override=match_threshold,
    )
    setup_logging(cfg.log_level)

    result = run_query(
        question,
        input_path,
        output_path,
        k=cfg.query_k,
        hops=cfg.query_hops,
        match_threshold=cfg.query_match_threshold,
        node_cap=cfg.query_node_cap,
        want_answer=not no_answer,
        llm_model=cfg.llm_model,
        llm_base_url=cfg.llm_base_url,
        embedding_model=cfg.embedding_model,
        cache=CacheStore(cfg.cache_dir),
    )
    return dict(result.answer_envelope)


def stats_to_dict(stats: GraphStats | dict[str, Any]) -> dict[str, Any]:
    """Serialize index stats for HTTP / agents."""
    return _stats_as_dict(stats)
