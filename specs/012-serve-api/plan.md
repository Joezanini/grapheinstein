# Implementation Plan: Serve & Agent API

**Branch**: `012-serve-api` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-serve-api/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Expose a stable public Python API (`grapheinstein.api`) for index + query that wraps existing `core/index.py` and `core/query.py` so Cursor slash-commands and other agents can call Grapheinstein in-process with CLI parity. Add optional `grapheinstein serve --port 8000` (FastAPI + Uvicorn behind `[serve]` extras) with loopback-only default binding and `POST /index` + `POST /query` thin HTTP wrappers over the same API. Ship agent-integration docs with copy-paste examples. No graph schema bump; no cloud auth.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing — Typer, NetworkX, Rich, Loguru, PyYAML, pathspec. **Optional** `[serve]` extras: FastAPI + Uvicorn (programmatic `uvicorn.run(app, host=..., port=...)`). Core install unchanged. See [research.md](./research.md).

**Storage**: Local filesystem — read/write portable `graph.json` / `.json.gz` (schema `6.0.0`); config/cache unchanged; no server-side DB

**Testing**: pytest; Typer `CliRunner`; unit tests for API wrappers/error mapping; contract tests for `serve` help/flags + HTTP JSON shapes (TestClient when extras present; skip/xfail clearly when absent); integration: Python API index→query parity with CLI; optional live serve round-trip on free port

**Target Platform**: macOS / Linux developer workstations (Windows best-effort); local loopback HTTP only by default

**Project Type**: Installable CLI + library package (extend `cli.py` + add `api.py` + optional `serve/`)

**Performance Goals**: Fixture Python API index+query completes within existing CLI budgets for the same fixture; HTTP overhead negligible vs indexing; serve startup fails fast on port-in-use

**Constraints**: Offline-capable; CLI/Python/HTTP semantic parity; HTTP deps optional; default bind `127.0.0.1`; no auth/TLS in v1; structured JSON separate from stderr logs; stay on graph schema `6.0.0` and query-answer `1.0.0`

**Scale/Scope**: Public API + optional HTTP for **index** and **query** only; explain/path/MCP host out of scope; agent docs in-repo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Loopback serve; no cloud; uses local graphs/models |
| CLI-first parity | PASS | `serve` is optional CLI; Python/HTTP call shared `api` over existing core |
| Provenance graph | PASS | No edge/provenance mutation; reuses existing index/query artifacts |
| Multi-modal scope | PASS | Index/query inherit existing modalities; no new parsers |
| Incremental simplicity | JUSTIFIED | Optional HTTP server — see Complexity Tracking; Python API is the simpler primary surface |
| Schema/contract | PASS | Graph `6.0.0` retained; additive CLI/HTTP/Python contracts + tests |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R1–R6; quickstart offline |
| CLI-first parity | PASS | [contracts/cli.md](./contracts/cli.md), [python-api.md](./contracts/python-api.md), [http-api.md](./contracts/http-api.md) |
| Provenance graph | PASS | [data-model.md](./data-model.md) reuses graph + query-answer entities |
| Multi-modal scope | PASS | No parser changes |
| Incremental simplicity | PASS | Optional `[serve]`; core path has zero FastAPI import at runtime |
| Schema/contract | PASS | Graph `6.0.0` / query-answer `1.0.0` retained; CLI contract additive `12.0.0` |

## Project Structure

### Documentation (this feature)

```text
specs/012-serve-api/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── python-api.md
│   └── http-api.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/grapheinstein/
├── __init__.py              # optionally re-export api helpers (keep thin)
├── api.py                   # NEW: public index() / query() for agents
├── cli.py                   # serve command; _KNOWN_COMMANDS; help/epilog
└── serve/                   # NEW: optional FastAPI app (lazy imports)
    ├── __init__.py          # ensure_serve_deps(); create_app(); run_server()
    └── app.py               # POST /index, POST /query

docs/
└── agent-integration.md     # NEW: agent playbook (linked from README)

tests/
├── contract/
│   ├── test_cli_help.py     # extend: serve listed
│   ├── test_cli_serve.py    # help, missing extras, flags
│   ├── test_python_api.py   # public signatures / error shapes
│   └── test_http_api.py     # FastAPI TestClient when [serve] present
├── integration/
│   ├── test_api_parity.py   # Python vs CLI same evidence for fixture query
│   └── test_serve_roundtrip.py  # optional live port or TestClient E2E
└── unit/
    └── test_api_wrappers.py
```

**Structure Decision**: Keep the single-package layout. Add top-level `api.py` as the stable import path for agents; put FastAPI behind `grapheinstein.serve` with lazy imports so core installs never load FastAPI. CLI `serve` and HTTP routes both call `api.py` only—never duplicate index/query logic.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Optional local HTTP server (FastAPI/Uvicorn) | Spec requires `grapheinstein serve` + `/index`/`/query` for non-Python clients; constitution already anticipates optional HTTP after CLI solidifies | Python-only API covers Cursor slash-commands but not heterogeneous local HTTP callers; shelling to CLI loses structured HTTP error semantics |
