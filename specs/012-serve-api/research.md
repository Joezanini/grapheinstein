# Research: Serve & Agent API

**Feature**: `012-serve-api`  
**Date**: 2026-07-17

## R1 — Public Python API surface

**Decision**: Add `grapheinstein.api` with two primary callables:

- `index(project_path, *, output=..., config=..., **index_options) -> IndexResult`
- `query(question, *, input=..., output=..., config=..., **query_options) -> dict` (query-answer envelope)

`IndexResult` is a small dataclass/TypedDict: `output_path`, `stats` (or equivalent summary fields), and optionally the loaded artifact dict when `include_artifact=True` (default `False` to avoid huge returns; agents that only need the path skip the payload).

Both functions load config via existing `load_config` precedence and call `index_project` / `run_query` — same core as CLI. CLI handlers SHOULD be refactored to call `api` (or thin shared helpers) so parity is structural, not accidental.

**Rationale**: Spec P1 requires in-process agent integration; constitution requires slash/MCP reuse of library/API. A dedicated `api` module is a stable import path without forcing agents to import Typer CLI internals.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Document `index_project` / `run_query` as the public API | Too many low-level kwargs; no config merge; CLI-only error UX |
| Only subprocess CLI from agents | Violates in-process slash-command story; harder structured errors |
| Large facade with explain/path/merge | Out of scope for this feature |

## R2 — Optional HTTP stack (FastAPI + Uvicorn)

**Decision**: Optional extras `[serve]` installing `fastapi` and `uvicorn`. CLI `grapheinstein serve` calls `ensure_serve_deps()` (pattern from `ensure_media_deps`) then `uvicorn.run(app, host=..., port=...)`.

Verified against FastAPI docs (`/fastapi/fastapi`): programmatic run is `uvicorn.run(app, host=..., port=...)`. Default **host `127.0.0.1`** (loopback); default **port `8000`**. Optional advanced `--host` for non-loopback (documented unsafe for untrusted networks). Single worker (default Uvicorn) — no multi-worker for v1 (avoids shared-state complexity during long index).

**Rationale**: Matches user intent and Spec Kit assumption; FastAPI gives request validation + JSON errors with minimal code; optional extras keep core install lean (constitution incremental simplicity).

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| stdlib `http.server` only | More hand-rolled JSON/validation; worse DX for agents |
| Always-on FastAPI dependency | Violates FR-010 / optional complexity gate |
| Starlette alone | Less ergonomic validation; FastAPI is the requested stack |

## R3 — HTTP request/response shape

**Decision**:

- `POST /index` JSON body: `{ "project_path": "...", "output": "...?", "config": "...?", ...optional flags }` → `200` `{ "ok": true, "output": "<path>", "stats": {...} }` or `4xx` `{ "ok": false, "error": "...", "code": "..." }`
- `POST /query` JSON body: `{ "question": "...", "input": "<graph path>", "output": "<subgraph path>?", ... }` → `200` query-answer envelope (schema `1.0.0`) plus optional wrapper fields documented in [http-api.md](./contracts/http-api.md); hard failures → `4xx` error object
- No auth headers; Content-Type `application/json`
- Synchronous handlers: request blocks until index/query completes (acceptable for local tool; document client timeouts)

**Rationale**: Reuse existing query-answer JSON for parity (SC-002/SC-003). Index returns path + stats rather than full graph by default (graphs can be large); optional `include_graph: true` MAY embed artifact for tiny fixtures.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Always return full `graph.json` body | Huge payloads; prefer path + file |
| Async job queue + poll | Overbuilt for local single-user serve |
| GraphQL / OpenAPI-only without POST bodies | Spec names `/index` and `/query` as POST-style operations |

## R4 — Concurrency & shutdown

**Decision**: Document **serialized request handling** via a process-wide `threading.Lock` around API calls in HTTP handlers (and note single Uvicorn worker). Concurrent requests queue; they MUST NOT interleave writes to the same output path. Different output paths still run one-at-a-time in v1 for simplicity. SIGINT/SIGTERM: Uvicorn default shutdown; in-flight work may abort mid-index (acceptable per spec edge cases).

**Rationale**: Spec requires no corruption across concurrent indexes; lock is the simplest correct local policy.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Fully parallel indexes | Risk of shared cache/config races; little benefit for local agent use |
| Per-output-path locks only | More code; still need care around cache_dir |

## R5 — Agent documentation location

**Decision**: Add `docs/agent-integration.md` with Python examples, HTTP examples, parity table (CLI ↔ Python ↔ HTTP), and `pip install 'grapheinstein[serve]'`. Link from root `README.md` under a short “Agent integration” section. `grapheinstein serve --help` epilog points to that doc path.

**Rationale**: FR-011 / User Story 4; keeps contracts under `specs/012-serve-api/contracts/` while user-facing playbook lives in `docs/`.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Only specs/quickstart | Specs are for implementers; agents need a stable docs path |
| README-only wall of text | Too long; separate doc scales better |

## R6 — Error model

**Decision**: Python API raises typed exceptions (reuse `GraphError`, `QueryError`, `ConfigError`, `FileNotFoundError`, etc.) with clear messages — never return empty success graphs. HTTP maps known errors to `400`/`404`/`422` and unexpected to `500` with generic message + log detail on stderr. Missing `[serve]` extras → CLI exit non-zero with `pip install 'grapheinstein[serve]'` hint (mirror media extras).

**Rationale**: FR-003, FR-010, SC-005.

## R7 — Agent context script

**Decision**: This Spec Kit install has **no** `update-agent-context` / agent-context bash script under `.specify/scripts/`. Skip agent-context update for this plan run; design artifacts under `specs/012-serve-api/` are the source of truth for downstream `/speckit-tasks`.

**Alternatives considered**: N/A
