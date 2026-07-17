# Contract: graph.json (schema_version 2.0.0)

**Feature**: `002-digraph-index-visualize`  
**Format**: JSON document compatible with NetworkX node-link data, plus required envelope fields  
**Breaks**: schema `1.0.0` (`kind` / `directory`) — readers MUST reject old artifacts; users re-index

## Top-level object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Must be `"2.0.0"` for this feature |
| `directed` | boolean | yes | Must be `true` |
| `multigraph` | boolean | yes | Must be `false` |
| `graph` | object | yes | Graph-level metadata |
| `nodes` | array | yes | Node list |
| `links` | array | yes | Edge list (may be empty for a lone root) |

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
| `type` | string | yes | `"file"` or `"dir"` |
| `metadata` | object | yes | Extensible map; may be `{}` |

Optional metadata keys (non-exhaustive):

| Key | Type | Description |
|-----|------|-------------|
| `symlink` | boolean | `true` when the path is a symbolic link |

Example nodes:

```json
{ "id": ".", "type": "dir", "metadata": {} }
```

```json
{ "id": "src/app.py", "type": "file", "metadata": {} }
```

```json
{ "id": "vendor/lib", "type": "file", "metadata": { "symlink": true } }
```

## Links (edges)

Each element MUST include:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | yes | Source node `id` |
| `target` | string | yes | Target node `id` |
| `type` | string | yes | `"contains"` or `"references"` |
| `provenance` | string | yes | `"extracted"` or `"inferred"` (this feature writes `"extracted"` only) |

### `contains`

Parent directory → immediate child file or directory.

```json
{
  "source": "src",
  "target": "src/app.py",
  "type": "contains",
  "provenance": "extracted"
}
```

### `references`

File → file based on whole-token basename mention in source text.

```json
{
  "source": "README.md",
  "target": "src/app.py",
  "type": "references",
  "provenance": "extracted"
}
```

## Minimal valid example

```json
{
  "schema_version": "2.0.0",
  "directed": true,
  "multigraph": false,
  "graph": {
    "project_root": "/tmp/sample",
    "generated_at": "2026-07-16T12:00:00Z"
  },
  "nodes": [
    { "id": ".", "type": "dir", "metadata": {} },
    { "id": "README.md", "type": "file", "metadata": {} },
    { "id": "app.py", "type": "file", "metadata": {} }
  ],
  "links": [
    {
      "source": ".",
      "target": "README.md",
      "type": "contains",
      "provenance": "extracted"
    },
    {
      "source": ".",
      "target": "app.py",
      "type": "contains",
      "provenance": "extracted"
    },
    {
      "source": "README.md",
      "target": "app.py",
      "type": "references",
      "provenance": "extracted"
    }
  ]
}
```

## Rejection rules (loaders)

Reject with a clear unsupported-format / validation error when:

- `schema_version` is missing or not `"2.0.0"`
- Any node uses `kind` instead of `type`, or `type` value `directory` instead of `dir`
- Required node/link fields are missing or wrong types
- JSON is not an object or is unreadable

Do **not** coerce `kind`→`type` or `directory`→`dir`.

## Migration note

| From | To | Action |
|------|-----|--------|
| `1.0.0` inventory graphs | `2.0.0` | Re-run `grapheinstein index` — no automated converter in this feature |
