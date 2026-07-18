# HTTP API Contract: Local Serve

**Feature**: `012-serve-api`  
**Base URL**: `http://127.0.0.1:<port>` (default port `8000`)  
**Contract version**: `1.0.0`

Requires optional install: `pip install 'grapheinstein[serve]'` then `grapheinstein serve`.

## Common

- Methods: `POST` with `Content-Type: application/json`
- Success: HTTP `200` + JSON body
- Client/validation errors: HTTP `400` / `404` / `422` + error object
- Unexpected server errors: HTTP `500` + error object (details logged on server stderr)
- No authentication

### Error object

```json
{
  "ok": false,
  "error": "human readable message",
  "code": "not_found"
}
```

| `code` | Typical status | Meaning |
|--------|----------------|---------|
| `validation` | 400 / 422 | Missing/invalid fields |
| `not_found` | 404 | Path does not exist |
| `config` | 400 | Config load/validation failed |
| `no_evidence` | 400 | Query found no supporting hits |
| `empty_corpus` | 400 | Graph has no searchable chunks |
| `deps_missing` | 500 | Should not occur if serve started; media extras mid-request |
| `internal` | 500 | Unexpected failure |

## `POST /index`

### Request body

```json
{
  "project_path": "/abs/or/relative/project",
  "output": "/optional/graph.json",
  "config": "/optional/config.yaml",
  "include_docs": false,
  "include_pdfs": false,
  "transcribe_media": false,
  "enrich_llm": false,
  "compress": false,
  "versioned": false,
  "include_graph": false
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `project_path` | yes | Project folder |
| `output` | no | Graph output path |
| `config` | no | Config path |
| boolean flags | no | Same meaning as CLI |
| `include_graph` | no | If true, response may include full artifact (large) |

### Success `200`

```json
{
  "ok": true,
  "output": "/path/to/graph.json",
  "stats": {
    "node_count": 0,
    "edge_count": 0
  },
  "graph": null
}
```

`stats` MUST include at least counts the CLI summary already exposes (exact key set may mirror `GraphStats` / index summary). `graph` is null unless `include_graph` is true.

## `POST /query`

### Request body

```json
{
  "question": "How does authentication work?",
  "input": "/path/to/graph.json",
  "output": "/optional/subgraph.json",
  "config": "/optional/config.yaml",
  "k": 20,
  "hops": 1,
  "no_answer": false
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `question` | yes | Non-empty |
| `input` | yes | Existing graph path |
| `output` | no | Supporting subgraph path |
| `k` / `hops` / … | no | Same bounds as CLI query |
| `no_answer` | no | Skip LLM answer generation |

### Success `200`

Body is the **query-answer envelope** (`schema_version` `1.0.0`) as defined by hybrid-query, optionally wrapped as:

```json
{
  "ok": true,
  "answer": { "...": "full query-answer envelope fields at top level OR nested" }
}
```

**Implementation choice (lock in tasks)**: Prefer returning the query-answer envelope **at the top level** (same keys as CLI stdout) plus `"ok": true` for HTTP consistency—or nest under `answer` and document one style only. Quickstart and tests MUST match the chosen style; do not support both ambiguously.

Recommended locked style for implement:

```json
{
  "ok": true,
  "schema_version": "1.0.0",
  "question": "...",
  "output": "...",
  "k": 20,
  "hops": 1,
  "hit_ids": [],
  "truncated": false,
  "embed_note": null,
  "visualization": {},
  "answer": {}
}
```

## Concurrency

Handlers serialize index/query work (process-wide lock). Clients MAY queue; they MUST NOT assume parallel indexing.

## Out of scope

- `GET` health (optional later)
- `/explain`, `/path`
- TLS, auth, CORS for browsers (local tool default)
