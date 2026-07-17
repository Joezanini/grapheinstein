# Contract: graph.json (schema_version 1.0.0)

**Feature**: `001-cli-project-index`  
**Format**: JSON document compatible with NetworkX node-link data, plus required envelope fields

## Top-level object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Must be `"1.0.0"` for this feature |
| `directed` | boolean | yes | Must be `true` |
| `multigraph` | boolean | yes | Must be `false` |
| `graph` | object | yes | Graph-level metadata |
| `nodes` | array | yes | Node list (may be empty aside from root in degenerate cases) |
| `links` | array | yes | Edge list (may be empty only if a single isolated root is written without self-edges) |

### `graph` metadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_root` | string | yes | Absolute path that was indexed |
| `generated_at` | string | yes | ISO-8601 UTC timestamp |

## Nodes

Each element MUST include:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Relative POSIX path from project root; root is `"."` |
| `kind` | string | yes | `"file"` or `"directory"` |
| `path` | string | yes | Same value as `id` |

Example node:

```json
{ "id": "src/app.py", "kind": "file", "path": "src/app.py" }
```

## Links (edges)

Each element MUST include:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | yes | Parent node `id` |
| `target` | string | yes | Child node `id` |
| `type` | string | yes | `"contains"` for this feature |
| `provenance` | string | yes | `"extracted"` for containment edges |

Example link:

```json
{
  "source": "src",
  "target": "src/app.py",
  "type": "contains",
  "provenance": "extracted"
}
```

## Minimal valid example

```json
{
  "schema_version": "1.0.0",
  "directed": true,
  "multigraph": false,
  "graph": {
    "project_root": "/tmp/sample",
    "generated_at": "2026-07-16T12:00:00Z"
  },
  "nodes": [
    { "id": ".", "kind": "directory", "path": "." },
    { "id": "README.md", "kind": "file", "path": "README.md" }
  ],
  "links": [
    {
      "source": ".",
      "target": "README.md",
      "type": "contains",
      "provenance": "extracted"
    }
  ]
}
```

## Invariants

1. Every `links[].source` and `links[].target` MUST exist in `nodes[].id`
2. Ignored paths MUST NOT appear as nodes
3. Every edge MUST have `provenance` of exactly `extracted` or `inferred`
4. Breaking changes to this shape require a `schema_version` bump and migration notes

## Non-goals (1.0.0)

- Symbol/concept nodes
- Non-containment edge types
- Embedding payloads on nodes
