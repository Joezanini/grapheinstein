"""FastAPI routes for local serve (imported only after ensure_serve_deps)."""

from __future__ import annotations

import threading
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

from grapheinstein.api import (
    ConfigError,
    EmptyCorpusError,
    GraphError,
    IndexTimeoutError,
    LargeRepoError,
    MediaExtrasError,
    NoEvidenceError,
    QueryError,
    index,
    query,
    stats_to_dict,
)

_REQUEST_LOCK = threading.Lock()


class IndexBody(BaseModel):
    project_path: str
    output: str | None = None
    config: str | None = None
    include_docs: bool = False
    include_pdfs: bool = False
    transcribe_media: bool = False
    enrich_llm: bool = False
    compress: bool = False
    versioned: bool = False
    include_graph: bool = False
    languages: str | None = None
    llm_model: str | None = None
    embedding_model: str | None = None
    llm_base_url: str | None = None
    code_only: bool = False
    include_generated_docs: bool = False
    allow_large_repo: bool = False
    max_reference_scan_bytes: int | None = None
    max_reference_scan_ops: int | None = None
    max_non_code_share: float | None = None
    max_total_bytes: int | None = None
    max_file_count: int | None = None
    timeout_seconds: int | None = None


class QueryBody(BaseModel):
    question: str
    input: str
    output: str | None = None
    config: str | None = None
    k: int | None = None
    hops: int | None = None
    match_threshold: float | None = None
    no_answer: bool = False
    llm_model: str | None = None
    embedding_model: str | None = None
    llm_base_url: str | None = None


def _error(status: int, message: str, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": message, "code": code},
    )


def _map_exception(exc: BaseException) -> JSONResponse:
    if isinstance(exc, (FileNotFoundError, NotADirectoryError)):
        return _error(404, str(exc), "not_found")
    if isinstance(exc, LargeRepoError):
        return _error(400, str(exc), "large_repo")
    if isinstance(exc, IndexTimeoutError):
        return _error(408, str(exc), "timeout")
    if isinstance(exc, ConfigError):
        return _error(400, str(exc), "config")
    if isinstance(exc, NoEvidenceError):
        return _error(400, str(exc), "no_evidence")
    if isinstance(exc, EmptyCorpusError):
        return _error(400, str(exc), "empty_corpus")
    if isinstance(exc, QueryError):
        return _error(400, str(exc), "validation")
    if isinstance(exc, MediaExtrasError):
        return _error(500, str(exc), "deps_missing")
    if isinstance(exc, GraphError):
        return _error(400, str(exc), "validation")
    if isinstance(exc, OSError):
        return _error(400, str(exc), "validation")
    logger.exception("Unhandled serve error")
    return _error(500, "Internal server error", "internal")


def build_app() -> FastAPI:
    app = FastAPI(
        title="Grapheinstein Serve",
        description=(
            "Local-only index/query HTTP surface. "
            "See docs/agent-integration.md for agent usage."
        ),
        version="1.0.0",
    )

    @app.post("/index")
    def post_index(body: IndexBody) -> JSONResponse:
        with _REQUEST_LOCK:
            try:
                result = index(
                    body.project_path,
                    output=body.output,
                    config=body.config,
                    languages=body.languages,
                    include_docs=body.include_docs,
                    include_pdfs=body.include_pdfs,
                    transcribe_media=body.transcribe_media,
                    enrich_llm=body.enrich_llm,
                    compress=body.compress,
                    versioned=body.versioned,
                    include_artifact=body.include_graph,
                    llm_model=body.llm_model,
                    embedding_model=body.embedding_model,
                    llm_base_url=body.llm_base_url,
                    code_only=body.code_only,
                    include_generated_docs=body.include_generated_docs,
                    allow_large_repo=body.allow_large_repo,
                    max_reference_scan_bytes=body.max_reference_scan_bytes,
                    max_reference_scan_ops=body.max_reference_scan_ops,
                    max_non_code_share=body.max_non_code_share,
                    max_total_bytes=body.max_total_bytes,
                    max_file_count=body.max_file_count,
                    timeout_seconds=body.timeout_seconds,
                    show_progress=False,
                )
            except Exception as exc:  # noqa: BLE001
                return _map_exception(exc)

        payload: dict[str, Any] = {
            "ok": True,
            "output": str(result.output_path),
            "stats": stats_to_dict(result.stats),
            "graph": result.artifact,
        }
        return JSONResponse(status_code=200, content=payload)

    @app.post("/query")
    def post_query(body: QueryBody) -> JSONResponse:
        if not body.question or not str(body.question).strip():
            return _error(422, "question must be a non-empty string", "validation")
        if not body.input or not str(body.input).strip():
            return _error(422, "input graph path is required", "validation")

        with _REQUEST_LOCK:
            try:
                envelope = query(
                    body.question,
                    input=body.input,
                    output=body.output,
                    config=body.config,
                    k=body.k,
                    hops=body.hops,
                    match_threshold=body.match_threshold,
                    no_answer=body.no_answer,
                    llm_model=body.llm_model,
                    embedding_model=body.embedding_model,
                    llm_base_url=body.llm_base_url,
                )
            except Exception as exc:  # noqa: BLE001
                return _map_exception(exc)

        payload = {"ok": True, **envelope}
        return JSONResponse(status_code=200, content=payload)

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception) -> JSONResponse:
        return _map_exception(exc)

    return app
