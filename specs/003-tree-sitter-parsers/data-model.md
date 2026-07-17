# Data Model: Tree-sitter Code Parsers

**Feature**: `003-tree-sitter-parsers`  
**Schema version**: `3.0.0` (breaking vs `2.0.0`)

## Entities

### Project Root

- **Identity**: Absolute filesystem path supplied to `index`
- **Role**: Boundary for discovery; file/dir node `id` values are POSIX-relative to this root (`"."` for the root itself)
- **Validation**: Must exist, be a directory, and be readable

### Language Configuration

| Field | Type | Rules |
|-------|------|-------|
| Enabled set | list of strings | Subset of `python`, `javascript`, `typescript`, `java`, `go`, `rust`, `cpp`, `sql` |
| Default | all eight | When config/CLI omit languages |
| Invalid name | — | Fail index before writing a success graph |

### Graph Node (file / dir)

Unchanged from schema 2.x:

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `id` | string | yes | POSIX relative path; root `"."`; unique |
| `type` | string | yes | Exactly `file` or `dir` |
| `metadata` | object | yes | May be `{}`; may include `symlink`, `suffix` |

### Graph Node (code entity)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `id` | string | yes | `{file}::{kind}::{name}::{start_line}` (see research R3) |
| `type` | string | yes | Exactly `function`, `class`, or `method` |
| `metadata` | object | yes | Must include `name` (string), `language` (canonical id), `file` (file node id), `start_line` (positive int, 1-based). Optional: `end_line`, `qualified_name` |

**Rules**:
- `metadata.file` MUST equal an existing `type: file` node `id`
- `start_line` MUST match the line encoded in `id`
- Anonymous / unnamed definitions are not represented as nodes

### Contains Edge

Unchanged: directory → immediate child file/dir; `provenance: extracted`.

### References Edge

Unchanged: file → file basename mention; `provenance: extracted`.

### Defines Edge

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `source` | string | yes | File node id, or class entity id |
| `target` | string | yes | Code-entity node id (`function` / `class` / `method`) |
| `type` | string | yes | Exactly `defines` |
| `provenance` | string | yes | Exactly `extracted` |

**Rules**:
- File → each top-level function/class in that file
- Class → each method in that class
- File → each method in that file (also emitted for file-centric queries)
- Both endpoints must exist; no self-loops

### Imports Edge

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `source` | string | yes | Importing **file** node id |
| `target` | string | yes | Resolved file node id or code-entity id |
| `type` | string | yes | Exactly `imports` |
| `provenance` | string | yes | Exactly `extracted` |

**Rules**: Create only when resolution is unambiguous within the indexed project; otherwise omit. At most one `imports` edge per ordered pair for a given resolution (dedupe identical pairs).

### Calls Edge

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `source` | string | yes | Caller `function`/`method` id, or file id for script-level calls |
| `target` | string | yes | Callee code-entity id |
| `type` | string | yes | Exactly `calls` |
| `provenance` | string | yes | Exactly `extracted` |

**Rules**: Ambiguous or unresolved callees produce no edge. At most one `calls` edge per ordered pair.

### Graph Artifact

Portable JSON document (typically `graph.json`):

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `schema_version` | string | yes | `"3.0.0"` for this feature |
| `directed` | boolean | yes | `true` |
| `multigraph` | boolean | yes | `false` |
| `graph` | object | yes | Includes at least `project_root`, `generated_at`; MAY include `languages` (enabled list used for the run) |
| `nodes` | array | yes | File/dir + code-entity nodes |
| `links` | array | yes | contains, references, defines, imports, calls |

**Lifecycle**:
1. `index` builds inventory → references → code extract/resolve → write artifact (overwrite OK)
2. Per-file parse failures skip structure only; overall success still writes the graph
3. Invalid language config / unreadable root / unwritable output → non-zero, no success graph
4. `visualize` / `status` load → validate v3 → summarize (reject 2.x)

## Relationships (conceptual)

```text
(dir) --contains--> (dir|file)
(file) --references--> (file)
(file) --defines--> (function|class|method)
(class) --defines--> (method)
(file) --imports--> (file|function|class|method)
(function|method|file) --calls--> (function|method)
```

## Validation summary

| Condition | Outcome |
|-----------|---------|
| Missing `schema_version` / `nodes` / `links` / `graph` | Load error |
| `schema_version` ≠ `3.0.0` | Unsupported-format error (re-index) |
| Node `type` outside `file\|dir\|function\|class\|method` | Load error |
| Edge `type` outside allowed set | Load error |
| `provenance` not `extracted`\|`inferred` | Load error |
| Code entity missing required metadata keys | Load error |

## Out of scope entities

Docs/PDF/media nodes, inferred edges, table/view SQL schema modeling, external package stub modules, query-command result graphs.
