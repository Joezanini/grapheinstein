# Data Model: Serve & Agent API

**Feature**: `012-serve-api`  
**Date**: 2026-07-17

This feature does **not** change graph schema `6.0.0` or query-answer schema `1.0.0`. It introduces request/result entities for the agent surfaces.

## Entities

### IndexRequest

Inputs to build or refresh a portable project graph.

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `project_path` | path | yes | Existing directory; resolved via existing project-path rules |
| `output` | path | no | Default from config / built-in `graph.json` resolution |
| `config` | path | no | Optional YAML; same precedence as CLI |
| `include_docs` / `include_pdfs` / `transcribe_media` / `enrich_llm` | bool | no | Same semantics as CLI index flags |
| `languages` | string / list | no | Same as CLI `--languages` |
| `compress` / `versioned` | bool | no | Same as CLI |
| `include_artifact` | bool | no | Python/HTTP only: when true, result may embed full graph dict (default false) |

**Validation**: Missing/unreadable `project_path` → hard failure. Invalid config → hard failure.

### IndexResult

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `output_path` | path | yes | Written portable graph location |
| `stats` | object | yes | Summary fields already produced by CLI index (node/edge counts, skips, cache hits when available) |
| `artifact` | object \| null | no | Full graph dict only when requested; schema `6.0.0` |

**Relationships**: Points at a **Portable Project Graph** on disk.

### QueryRequest

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `question` | string | yes | Non-empty after strip |
| `input` | path | yes* | Path to portable graph (*required unless in-memory graph supported later; v1 = path) |
| `output` | path | no | Supporting subgraph path; default as CLI |
| `config` | path | no | Optional YAML |
| `k` / `hops` / `match_threshold` / `no_answer` | as CLI | no | Same bounds as hybrid query feature |

**Validation**: Unreadable graph → hard failure. No evidence → structured no-evidence failure (Python exception / HTTP 4xx), not a fabricated answer.

### QueryResult (wire)

Identical to existing **Structured Query Answer** envelope (`schema_version` `1.0.0`) from `010-hybrid-query`. See that feature’s [query-answer-json](../010-hybrid-query/contracts/query-answer-json.md) contract; this feature reuses it without revision.

### Portable Project Graph

Unchanged schema `6.0.0` artifact (`nodes`, `links` with `type` + `provenance`, etc.). Produced by index; consumed by query.

### LocalServeSession

Runtime-only (not persisted).

| Field | Type | Rules |
|-------|------|-------|
| `host` | string | Default `127.0.0.1` |
| `port` | int | Default `8000`; must be free at bind |
| `app` | HTTP app | Exposes `/index`, `/query` |
| `request_lock` | lock | Serializes index/query handlers |

**State transitions**:

```text
[stopped] -- serve starts --> [listening]
[listening] -- SIGINT/SIGTERM / process exit --> [stopped]
[listening] -- port bind failure --> [stopped] (error)
```

### ApiError

| Field | Type | Rules |
|-------|------|-------|
| `ok` | false | Always false for error objects |
| `error` | string | Human-readable message |
| `code` | string | Stable machine code e.g. `not_found`, `validation`, `no_evidence`, `config`, `deps_missing` |

## Invariants

1. Index/query via Python or HTTP MUST produce the same graph schema and query-answer shape as CLI for equivalent inputs.
2. Hard failures NEVER yield an empty “success” graph.
3. Serve session binds loopback by default; broadening host is explicit and documented.
4. Optional HTTP dependencies absent ⇒ serve unavailable; Python API remains available.
