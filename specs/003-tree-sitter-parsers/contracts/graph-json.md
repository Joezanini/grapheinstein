# Contract: graph.json (schema_version 3.0.0)

**Feature**: `003-tree-sitter-parsers`  
**Format**: JSON document compatible with NetworkX node-link data, plus required envelope fields  
**Breaks**: schema `2.0.0` (file/dir only) — readers MUST reject older artifacts; users re-index

## Top-level object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Must be `"3.0.0"` for this feature |
| `directed` | boolean | yes | Must be `true` |
| `multigraph` | boolean | yes | Must be `false` |
| `graph` | object | yes | Graph-level metadata |
| `nodes` | array | yes | Node list |
| `links` | array | yes | Edge list |

### `graph` metadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_root` | string | yes | Absolute path that was indexed |
| `generated_at` | string | yes | ISO-8601 UTC timestamp |
| `languages` | array of strings | no | Enabled language ids used for structure extraction on this run |

## Nodes

### File / directory

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Relative POSIX path; root is `"."` |
| `type` | string | yes | `"file"` or `"dir"` |
| `metadata` | object | yes | Extensible map; may be `{}` |

### Code entity

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | `{file}::{kind}::{name}::{start_line}` |
| `type` | string | yes | `"function"`, `"class"`, or `"method"` |
| `metadata` | object | yes | Must include `name`, `language`, `file`, `start_line` |

Example code entity:

```json
{
  "id": "src/app.py::function::greet::1",
  "type": "function",
  "metadata": {
    "name": "greet",
    "language": "python",
    "file": "src/app.py",
    "start_line": 1
  }
}
```

## Links (edges)

Each element MUST include:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | yes | Source node `id` |
| `target` | string | yes | Target node `id` |
| `type` | string | yes | One of: `contains`, `references`, `defines`, `imports`, `calls` |
| `provenance` | string | yes | `"extracted"` or `"inferred"` (this feature writes `"extracted"` only for new code edges) |

### `defines`

```json
{
  "source": "src/app.py",
  "target": "src/app.py::function::greet::1",
  "type": "defines",
  "provenance": "extracted"
}
```

### `imports`

```json
{
  "source": "src/main.py",
  "target": "src/app.py",
  "type": "imports",
  "provenance": "extracted"
}
```

### `calls`

```json
{
  "source": "src/main.py::function::run::3",
  "target": "src/app.py::function::greet::1",
  "type": "calls",
  "provenance": "extracted"
}
```

Inventory edges `contains` and `references` retain the schema 2.x shapes and semantics.

## Minimal valid example (excerpt)

```json
{
  "schema_version": "3.0.0",
  "directed": true,
  "multigraph": false,
  "graph": {
    "project_root": "/tmp/code_project",
    "generated_at": "2026-07-16T12:00:00Z",
    "languages": ["python"]
  },
  "nodes": [
    { "id": ".", "type": "dir", "metadata": {} },
    { "id": "src", "type": "dir", "metadata": {} },
    { "id": "src/app.py", "type": "file", "metadata": {} },
    {
      "id": "src/app.py::function::greet::1",
      "type": "function",
      "metadata": {
        "name": "greet",
        "language": "python",
        "file": "src/app.py",
        "start_line": 1
      }
    }
  ],
  "links": [
    {
      "source": ".",
      "target": "src",
      "type": "contains",
      "provenance": "extracted"
    },
    {
      "source": "src",
      "target": "src/app.py",
      "type": "contains",
      "provenance": "extracted"
    },
    {
      "source": "src/app.py",
      "target": "src/app.py::function::greet::1",
      "type": "defines",
      "provenance": "extracted"
    }
  ]
}
```

## Rejection rules (loaders)

Reject with a clear unsupported-format / validation error when:

- `schema_version` is missing or not `"3.0.0"` (including `"2.0.0"`)
- Node `type` is not one of `file`, `dir`, `function`, `class`, `method`
- Code-entity nodes lack required metadata keys / types
- Edge `type` or `provenance` invalid
- JSON is not an object or is unreadable

Do **not** coerce schema `2.0.0` artifacts to `3.0.0`.

## Migration note

| From | To | Action |
|------|-----|--------|
| `2.0.0` digraph inventory | `3.0.0` | Re-run `grapheinstein index` — no automated converter in this feature |
| `1.0.0` inventory | `3.0.0` | Re-run `grapheinstein index` |
