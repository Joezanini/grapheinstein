# Data Model: Directed File Graph Index & Visualize

**Feature**: `002-digraph-index-visualize`  
**Schema version**: `2.0.0` (breaking vs `1.0.0`)

## Entities

### Project Root

- **Identity**: Absolute filesystem path supplied to `index`
- **Role**: Boundary for discovery; all node `id` values are POSIX-relative to this root (`"."` for the root itself)
- **Validation**: Must exist, be a directory, and be readable

### Graph Node

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `id` | string | yes | POSIX relative path from project root; root is `"."`; unique in graph |
| `type` | string | yes | Exactly `file` or `dir` |
| `metadata` | object | yes | May be empty `{}`; reserved for extensible attributes (e.g. `symlink: true`, `suffix`) |

**Notes**:
- Symlinks are `type: file` (optionally `metadata.symlink = true`)
- Directories use `type: dir` (not `directory`)
- No required duplicate `path` field in v2 (identity is `id`)

### Contains Edge

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `source` | string | yes | Parent directory node `id` |
| `target` | string | yes | Immediate child file or dir `id` |
| `type` | string | yes | Exactly `contains` |
| `provenance` | string | yes | Exactly `extracted` |

**Rules**: Both endpoints must exist as nodes. No self-loops. One `contains` edge per parent→child.

### References Edge

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `source` | string | yes | File node `id` whose text mentioned the target |
| `target` | string | yes | File node `id` whose basename was mentioned |
| `type` | string | yes | Exactly `references` |
| `provenance` | string | yes | Exactly `extracted` |

**Rules**:
- Source and target must be `type: file`
- Target basename must be unique among indexed files
- Mention must be a whole-token match (see research R3)
- No self-`references`
- At most one `references` edge per ordered pair `(source, target)`
- Ambiguous basenames create no edges

### Graph Artifact

Portable JSON document (typically `graph.json`):

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `schema_version` | string | yes | `"2.0.0"` for this feature |
| `directed` | boolean | yes | `true` |
| `multigraph` | boolean | yes | `false` |
| `graph` | object | yes | Includes at least `project_root`, `generated_at` |
| `nodes` | array | yes | Graph Node objects |
| `links` | array | yes | Contains + References edges |

**Lifecycle**:
1. `index` builds in-memory DiGraph → writes artifact (overwrite OK)
2. `visualize` / `status` load artifact → validate v2 shape → summarize or export DOT
3. Unsupported/malformed artifacts fail closed (no write of partial “success” graph on index validation failure of inputs)

## Relationships (conceptual)

```text
(dir) --contains--> (dir|file)
(file) --references--> (file)   # basename whole-token mention
```

## Validation summary

| Condition | Outcome |
|-----------|---------|
| Missing `schema_version` / `nodes` / `links` / `graph` | Load error |
| `schema_version` ≠ `2.0.0` | Unsupported-format error |
| Node has `kind` or `type: directory` instead of v2 shape | Unsupported-format error |
| Edge missing `type` or `provenance` | Load error |
| `provenance` not `extracted`\|`inferred` | Load error |

## Out of scope entities

Functions, classes, imports AST, SQL tables, media assets, inferred edges — deferred to later features.
