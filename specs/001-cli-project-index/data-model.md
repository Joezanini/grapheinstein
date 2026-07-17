# Data Model: CLI Project Index Skeleton

**Feature**: `001-cli-project-index`  
**Date**: 2026-07-16

## Entities

### ProjectRoot

Represents the folder the user indexes.

| Field | Type | Description |
|-------|------|-------------|
| path | absolute path string | Resolved, existing directory |
| relative_id | string | Always `"."` as the root node id |

**Validation**:
- MUST exist and be a directory
- MUST be readable

### InventoryNode

A file or directory discovered under the project root (non-ignored).

| Field | Type | Description |
|-------|------|-------------|
| id | string | Stable identity: POSIX relative path from project root (`"."` for root) |
| path | string | Same as `id` (relative, POSIX separators) |
| kind | enum | `file` \| `directory` |

**Validation**:
- `id` / `path` MUST NOT be empty
- `kind` MUST be exactly `file` or `directory`
- Ignored paths MUST NOT produce nodes
- Every non-root node’s parent directory SHOULD also exist as a directory node (walk creates parents as needed)

### GraphEdge (Containment)

Directed relationship from parent directory to child node.

| Field | Type | Description |
|-------|------|-------------|
| source | string | Parent node `id` |
| target | string | Child node `id` |
| type | string | Always `contains` in this increment |
| provenance | enum | Always `extracted` for containment |

**Validation**:
- Every edge MUST include `type` and `provenance`
- `provenance` MUST be `extracted` or `inferred` (only `extracted` used here)
- `source` and `target` MUST reference existing nodes

### GraphArtifact

Portable on-disk representation written to the output path (default `graph.json`).

| Field | Type | Description |
|-------|------|-------------|
| schema_version | string | Semver string; this feature uses `1.0.0` |
| directed | bool | `true` |
| multigraph | bool | `false` |
| graph.project_root | string | Absolute path indexed |
| graph.generated_at | string | ISO-8601 UTC timestamp |
| nodes | list | NetworkX node-link nodes (`id` + attributes) |
| links | list | NetworkX node-link links (`source`, `target`, + edge attrs) |

**Validation**:
- MUST be valid JSON
- MUST include `schema_version`
- Node counts in status MUST match `nodes` filtered by `kind`

### UserConfig

Optional local defaults.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| output | string | `graph.json` | Default graph output path |
| log_level | string | `INFO` | Loguru level name |

**Validation**:
- Missing file at default location → use defaults (not an error)
- Explicit `--config` path missing or invalid YAML → error
- Unknown keys MAY be ignored with a warning (forward-compatible) or rejected; **decision**: ignore unknown keys with warning

### IgnoreRules

Patterns loaded from `{project}/.gitignore`.

| Field | Type | Description |
|-------|------|-------------|
| patterns | list[string] | Raw gitignore lines (comments/blanks skipped) |
| matcher | pathspec matcher | Used to test relative paths |

**Validation**:
- Unreadable/broken file → empty rules + warning
- Matching uses paths relative to project root

## Relationships

```text
ProjectRoot --contains--> InventoryNode (directory | file)
InventoryNode(directory) --contains--> InventoryNode (child)
UserConfig --> influences --> GraphArtifact.output location / logging
IgnoreRules --> filters --> which InventoryNodes are created
```

## State Transitions

### Index run

1. **Unresolved** → validate project path  
2. **Configured** → merge CLI > explicit config > user config > defaults  
3. **Discovering** → walk + apply ignore rules  
4. **Building** → create nodes + `contains` edges  
5. **Persisted** → write GraphArtifact  
6. **Failed** → any step may transition here with non-zero exit (no silent success)

### Status run

1. **Lookup** graph path from flags/config/default  
2. **Missing** → clear message, exit 2  
3. **Loaded** → compute counts from nodes  
4. **Reported** → Rich summary to human console  

## Out of Scope (later features)

- Code/symbol nodes, document chunks, media assets
- Edge types beyond `contains` (`imports`, `calls`, `mentions`, …)
- `inferred` provenance edges
- Embedding / vector indexes
- Query entities (explain/path/ask results)
