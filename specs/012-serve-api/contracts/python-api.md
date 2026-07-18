# Python API Contract: Agent Integration

**Feature**: `012-serve-api`  
**API module**: `grapheinstein.api`  
**Contract version**: `1.0.0`

## Purpose

Stable in-process surface for Cursor slash-commands and other agents. Semantics match CLI `index` and `query`.

## `index`

```python
from grapheinstein.api import index

result = index(
    project_path,                 # str | Path — required
    *,
    output=None,                  # str | Path | None
    config=None,                  # str | Path | None
    languages=None,               # str | Sequence[str] | None
    include_docs=False,
    include_pdfs=False,
    transcribe_media=False,
    enrich_llm=False,
    compress=False,
    versioned=False,
    include_artifact=False,
    # plus other CLI-equivalent overrides as implemented (llm_model, etc.)
)
```

### Success return (`IndexResult`)

| Attribute | Type | Meaning |
|-----------|------|---------|
| `output_path` | `Path` | Written graph path |
| `stats` | object | Index summary (node/edge counts and related fields) |
| `artifact` | `dict \| None` | Full schema `6.0.0` artifact if `include_artifact=True`, else `None` |

### Errors

Raises (do not return empty success):

| Condition | Exception family |
|-----------|------------------|
| Missing/invalid project path | `FileNotFoundError` / `NotADirectoryError` / `OSError` |
| Bad config | `ConfigError` |
| Graph write/validation failure | `GraphError` |
| Missing media extras when required | `MediaExtrasError` |

## `query`

```python
from grapheinstein.api import query

envelope = query(
    question,                     # str — required, non-empty
    *,
    input,                        # str | Path — required graph path
    output=None,                  # str | Path | None — subgraph path
    config=None,
    k=None,
    hops=None,
    match_threshold=None,
    no_answer=False,
    # plus other CLI-equivalent overrides as implemented
)
```

### Success return

`dict` matching query-answer schema `1.0.0` (same as CLI stdout on success). See `specs/010-hybrid-query/contracts/query-answer-json.md`.

### Errors

| Condition | Exception family |
|-----------|------------------|
| Empty/invalid question | `QueryError` |
| Missing/unreadable graph | `FileNotFoundError` / `GraphError` |
| No searchable corpus | `EmptyCorpusError` |
| No evidence hits | `NoEvidenceError` |
| Bad config | `ConfigError` |

Agents SHOULD catch these and surface `.args[0]` / `str(exc)` to users.

## Parity

For the same project path, graph path, question, and resolved config/flags:

- `index(...)` writes a graph equivalent to `grapheinstein index ...`
- `query(...)` returns the same citation evidence set as `grapheinstein query ...` (SC-002)

## Non-goals

- This module is **not** required to expose explain/path/merge/serve.
- Importing `grapheinstein.api` MUST NOT require FastAPI/Uvicorn.
