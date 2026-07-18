"""Ignore-aware project discovery and inventory indexing."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pathspec
from loguru import logger

from grapheinstein.core.cache import CacheStore
from grapheinstein.core.graph import (
    add_contains_edge,
    add_node,
    ensure_directory_chain,
    new_inventory_graph,
    save_graph,
    stats_from_artifact,
    to_artifact_dict,
)
from grapheinstein.core.parsers import DEFAULT_LANGUAGES, merge_code_structure
from grapheinstein.core.parsers.docs import merge_docs_structure
from grapheinstein.core.parsers.media_av import merge_media_av
from grapheinstein.core.parsers.media_link import merge_media_links
from grapheinstein.core.parsers.media_ocr import (
    MediaExtrasError,
    ensure_media_deps,
    merge_media_ocr,
)
from grapheinstein.core.parsers.pdf import merge_pdf_structure
from grapheinstein.core.references import add_reference_edges
from grapheinstein.utils import DEFAULT_MAX_FILE_SIZE, resolve_project_path


def load_gitignore_spec(project_root: Path) -> pathspec.PathSpec | None:
    gitignore = project_root / ".gitignore"
    if not gitignore.exists():
        return None
    try:
        lines = gitignore.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning(
            "Could not read .gitignore at {}: {} — continuing without ignores",
            gitignore,
            exc,
        )
        return None
    try:
        return pathspec.PathSpec.from_lines("gitignore", lines)
    except Exception as exc:  # noqa: BLE001 - best-effort ignore handling
        logger.warning(
            "Broken .gitignore at {}: {} — continuing without ignores",
            gitignore,
            exc,
        )
        return None


def build_config_ignore_spec(patterns: Sequence[str] | None) -> pathspec.PathSpec | None:
    """Build a pathspec from `ignored_patterns` config, applied in addition to .gitignore."""
    if not patterns:
        return None
    try:
        return pathspec.PathSpec.from_lines("gitignore", list(patterns))
    except Exception as exc:  # noqa: BLE001 - best-effort ignore handling
        logger.warning(
            "Invalid ignored_patterns {!r}: {} — continuing without them", patterns, exc
        )
        return None


def _to_posix_relative(project_root: Path, path: Path) -> str:
    rel = path.relative_to(project_root).as_posix()
    return "." if rel == "." else rel


def _is_ignored(spec: pathspec.PathSpec | None, relative: str, *, is_dir: bool) -> bool:
    if spec is None or relative in {"", "."}:
        return False
    candidates = [relative]
    if is_dir and not relative.endswith("/"):
        candidates.append(relative + "/")
    return any(spec.match_file(candidate) for candidate in candidates)


def discover_paths(
    project_root: Path,
    *,
    ignored_patterns: Sequence[str] | None = None,
) -> list[tuple[str, str, dict[str, Any]]]:
    """
    Return list of (relative_id, type, metadata) for non-ignored files and directories.
    Always includes root "." as dir. Symlinks are type file with metadata.symlink=True
    and are not followed.

    A path is ignored if it matches the project `.gitignore` OR the supplied
    `ignored_patterns` (config-driven, gitignore-style syntax).
    """
    root = resolve_project_path(project_root)
    gitignore_spec = load_gitignore_spec(root)
    config_spec = build_config_ignore_spec(ignored_patterns)
    found: dict[str, tuple[str, dict[str, Any]]] = {".": ("dir", {})}

    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir(), key=lambda p: p.name)
        except OSError as exc:
            logger.warning("Skipping unreadable directory {}: {}", current, exc)
            continue

        for entry in entries:
            if entry.name == ".git":
                continue
            rel = _to_posix_relative(root, entry)

            if entry.is_symlink():
                if _is_ignored(gitignore_spec, rel, is_dir=False) or _is_ignored(
                    config_spec, rel, is_dir=False
                ):
                    logger.debug("Ignoring {}", rel)
                    continue
                found[rel] = ("file", {"symlink": True})
                continue

            is_dir = entry.is_dir()
            if _is_ignored(gitignore_spec, rel, is_dir=is_dir) or _is_ignored(
                config_spec, rel, is_dir=is_dir
            ):
                logger.debug("Ignoring {}", rel)
                continue
            if is_dir:
                found[rel] = ("dir", {})
                stack.append(entry)
            elif entry.is_file():
                found[rel] = ("file", {})
            else:
                logger.debug("Skipping non-file/non-dir {}", rel)

    items = [(rel, typ, meta) for rel, (typ, meta) in found.items()]
    return sorted(items, key=lambda item: (0 if item[1] == "dir" else 1, item[0]))


class _NullProgress:
    """No-op stand-in used when progress display is disabled."""

    def advance(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def set_stage(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def __enter__(self) -> _NullProgress:
        return self

    def __exit__(self, *_exc: Any) -> None:
        return None


class _RichIndexProgress:
    """Thin wrapper around rich.progress.Progress for index stages (stderr only)."""

    def __init__(self, total: int, description: str = "Indexing"):
        from rich.progress import (
            BarColumn,
            MofNCompleteColumn,
            Progress,
            TextColumn,
            TimeElapsedColumn,
        )

        from grapheinstein.utils import console

        self._progress = Progress(
            TextColumn("[bold blue]{task.fields[stage]}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        )
        self._task = None
        self._total = total
        self._description = description

    def __enter__(self) -> _RichIndexProgress:
        self._progress.__enter__()
        self._task = self._progress.add_task(
            self._description, total=self._total, stage=self._description
        )
        return self

    def __exit__(self, *exc: Any) -> None:
        self._progress.__exit__(*exc)

    def advance(self, amount: int = 1) -> None:
        if self._task is not None:
            self._progress.update(self._task, advance=amount)

    def set_stage(self, stage: str, *, total: int | None = None) -> None:
        if self._task is not None:
            kwargs: dict[str, Any] = {"stage": stage}
            if total is not None:
                kwargs["total"] = total
                kwargs["completed"] = 0
            self._progress.update(self._task, **kwargs)


def _make_progress(show_progress: bool, total: int, description: str = "Indexing"):
    if not show_progress:
        return _NullProgress()
    try:
        import sys

        if not sys.stderr.isatty():
            return _NullProgress()
        return _RichIndexProgress(total, description)
    except Exception as exc:  # noqa: BLE001 - progress is best-effort
        logger.debug("Progress display unavailable: {}", exc)
        return _NullProgress()


def build_inventory_graph(
    project_root: Path,
    *,
    languages: Sequence[str] | None = None,
    include_docs: bool = False,
    include_pdfs: bool = False,
    transcribe_media: bool = False,
    enrich_llm: bool = False,
    llm_model: str | None = None,
    llm_base_url: str | None = None,
    llm_confidence_threshold: float | None = None,
    ocr_extract=None,
    av_transcribe=None,
    llm_chat=None,
    list_models_fn=None,
    skip_media_deps_check: bool = False,
    skip_llm_preflight: bool = False,
    ignored_patterns: Sequence[str] | None = None,
    max_file_size: int | None = None,
    cache_dir: Path | str | None = None,
    embedding_model: str | None = None,
    show_progress: bool = False,
):
    from grapheinstein.core.parsers.llm_enrich import (
        DEFAULT_CONFIDENCE_THRESHOLD,
        merge_llm_enrichment,
    )
    from grapheinstein.core.parsers.llm_ollama import (
        DEFAULT_BASE_URL,
        DEFAULT_MODEL,
        check_ready,
    )

    root = resolve_project_path(project_root)
    if transcribe_media and not skip_media_deps_check:
        ensure_media_deps()

    max_size = int(max_file_size) if max_file_size is not None else DEFAULT_MAX_FILE_SIZE

    cache: CacheStore | None = None
    if cache_dir is not None:
        cache = CacheStore(Path(cache_dir))

    graph = new_inventory_graph(root)
    discovered = discover_paths(root, ignored_patterns=ignored_patterns)

    skipped_oversize = 0
    with _make_progress(show_progress, len(discovered), "Discovering files") as progress:
        for rel, node_type, metadata in discovered:
            if rel == ".":
                progress.advance()
                continue
            if node_type == "dir":
                ensure_directory_chain(graph, rel)
            else:
                parent = Path(rel).parent.as_posix()
                if parent == ".":
                    parent_id = "."
                else:
                    ensure_directory_chain(graph, parent)
                    parent_id = parent
                if rel not in graph:
                    file_metadata = dict(metadata)
                    if not file_metadata.get("symlink"):
                        try:
                            size_bytes = (root / rel).stat().st_size
                        except OSError:
                            size_bytes = None
                        if size_bytes is not None and size_bytes > max_size:
                            file_metadata["skipped"] = "oversize"
                            file_metadata["size_bytes"] = size_bytes
                            skipped_oversize += 1
                            logger.warning(
                                "Skipping oversize file {} ({} bytes > max_file_size {})",
                                rel,
                                size_bytes,
                                max_size,
                            )
                    add_node(graph, rel, "file", metadata=file_metadata)
                    add_contains_edge(graph, parent_id, rel)
            progress.advance()

    add_reference_edges(graph, root)
    enabled = list(languages) if languages is not None else list(DEFAULT_LANGUAGES)
    progress2 = _make_progress(show_progress, 1, "Parsing structure")
    with progress2:
        skips = merge_code_structure(graph, root, enabled, cache=cache)
        progress2.advance()
    graph.graph["languages"] = list(enabled)
    graph.graph["include_docs"] = bool(include_docs)
    graph.graph["include_pdfs"] = bool(include_pdfs)
    graph.graph["transcribe_media"] = bool(transcribe_media)
    graph.graph["enrich_llm"] = bool(enrich_llm)
    graph.graph["skipped_oversize"] = skipped_oversize
    model = llm_model or DEFAULT_MODEL
    embed_model = embedding_model or model
    base_url = (llm_base_url or DEFAULT_BASE_URL).rstrip("/")
    threshold = (
        DEFAULT_CONFIDENCE_THRESHOLD
        if llm_confidence_threshold is None
        else float(llm_confidence_threshold)
    )
    if enrich_llm:
        graph.graph["llm_model"] = model
    graph.graph["embedding_model"] = embed_model
    if include_docs:
        skips += merge_docs_structure(graph, root)
    if include_pdfs:
        skips += merge_pdf_structure(graph, root)
    if transcribe_media:
        skips += merge_media_ocr(graph, root, extract_text=ocr_extract)
        skips += merge_media_av(graph, root, transcribe=av_transcribe)
        merge_media_links(graph)
    if enrich_llm:
        ready = True
        if llm_chat is not None:
            ready = True
        elif not skip_llm_preflight:
            ready, _msg = check_ready(
                model=model, base_url=base_url, list_models_fn=list_models_fn
            )
        else:
            ready = True
        if ready:
            skips += merge_llm_enrichment(
                graph,
                root,
                model=model,
                base_url=base_url,
                confidence_threshold=threshold,
                llm_chat=llm_chat,
            )
    graph.graph["parse_skips"] = skips
    if cache is not None:
        cache_stats = cache.stats()
        graph.graph["cache_hits"] = cache_stats.hits
        graph.graph["cache_misses"] = cache_stats.misses
        graph.graph["cache_corrupt_recovered"] = cache_stats.corrupt_recovered
        cache.close()
    return graph


def index_project(
    project_root: Path,
    output_path: Path,
    *,
    languages: Sequence[str] | None = None,
    include_docs: bool = False,
    include_pdfs: bool = False,
    transcribe_media: bool = False,
    enrich_llm: bool = False,
    llm_model: str | None = None,
    llm_base_url: str | None = None,
    llm_confidence_threshold: float | None = None,
    compress: bool = False,
    versioned: bool = False,
    ocr_extract=None,
    av_transcribe=None,
    llm_chat=None,
    list_models_fn=None,
    skip_media_deps_check: bool = False,
    skip_llm_preflight: bool = False,
    ignored_patterns: Sequence[str] | None = None,
    max_file_size: int | None = None,
    cache_dir: Path | str | None = None,
    embedding_model: str | None = None,
    show_progress: bool = False,
):
    """Index project and write graph.json artifact. Returns (path, stats)."""
    root = resolve_project_path(project_root)
    graph = build_inventory_graph(
        root,
        languages=languages,
        include_docs=include_docs,
        include_pdfs=include_pdfs,
        transcribe_media=transcribe_media,
        enrich_llm=enrich_llm,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        llm_confidence_threshold=llm_confidence_threshold,
        ocr_extract=ocr_extract,
        av_transcribe=av_transcribe,
        llm_chat=llm_chat,
        list_models_fn=list_models_fn,
        skip_media_deps_check=skip_media_deps_check,
        skip_llm_preflight=skip_llm_preflight,
        ignored_patterns=ignored_patterns,
        max_file_size=max_file_size,
        cache_dir=cache_dir,
        embedding_model=embedding_model,
        show_progress=show_progress,
    )
    written = save_graph(graph, output_path, compress=compress, versioned=versioned)
    artifact = to_artifact_dict(graph)
    parse_skips = int(graph.graph.get("parse_skips") or 0)
    stats = stats_from_artifact(
        artifact,
        written,
        parse_skips=parse_skips,
        cache_hits=int(graph.graph.get("cache_hits") or 0),
        cache_misses=int(graph.graph.get("cache_misses") or 0),
        cache_corrupt_recovered=int(graph.graph.get("cache_corrupt_recovered") or 0),
        skipped_oversize=int(graph.graph.get("skipped_oversize") or 0),
    )
    return written, stats


# Re-export for callers that catch missing extras
__all__ = [
    "MediaExtrasError",
    "build_config_ignore_spec",
    "build_inventory_graph",
    "discover_paths",
    "index_project",
    "load_gitignore_spec",
]
