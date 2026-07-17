# CLI Contract: grapheinstein (graph output, compression, versioning, merge)

**Feature**: `007-graph-output-merge`  
**CLI contract version**: 7.0.0 (pairs with graph schema_version `6.0.0`; additive I/O flags + `merge`)

## Entrypoint

- Console script: `grapheinstein`
- Module: `python -m grapheinstein`

## Global / shared options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config` | path | unset | YAML config path; overrides user config for this run |
| `--help` | flag | — | Show help |

Config precedence: CLI flags > `--config` file > `~/.grapheinstein/config.yaml` > built-ins.

User config path: `~/.grapheinstein/config.yaml`

Supported keys (additions for this feature):

| Key | Type | Description |
|-----|------|-------------|
| `output` | string | Default graph output path (existing) |
| `compress` | bool | Default for `--compress` when flag omitted (default `false`) |
| `versioned` | bool | Default for `--versioned` when flag omitted (default `false`) |

Prior keys (`log_level`, `languages`, LLM settings, etc.) unchanged.

## Path / compression rule

When compression is enabled for a write:

1. If the resolved destination path already ends with `.gz`, write gzip bytes to that path.
2. Otherwise append `.gz` to the path (e.g. `graph.json` → `graph.json.gz`).

Readers accept plain JSON and gzip (by `.gz` suffix and/or gzip magic).

## Commands

### Default (no subcommand) / `index`

```text
grapheinstein index PROJECT_PATH [existing index options...] [--compress] [--versioned] [--output PATH] [--config PATH]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--compress` | flag | config or off | Write gzip-compressed graph artifact |
| `--versioned` | flag | config or off | Also write next `graph_vN.json[.gz]` beside primary output |
| `--output` / `-o` | path | config or `graph.json` | Primary (“latest”) destination (subject to `.gz` rule) |

**Behavior** (additions; prior index stages unchanged):

1. Build in-memory digraph as today (inventory → parsers → optional enrichments).
2. Convert to artifact dict; **validate** before any write.
3. Resolve primary path with compression rule; **atomic write** primary.
4. If `--versioned`: compute next `N` from existing `graph_v*.json[.gz]` in the primary’s parent directory; atomic-write that snapshot with the same payload; never overwrite an existing `graph_vN`.
5. On failure before successful replace: exit non-zero; do not leave a corrupt file at the final primary path; do not create a new `graph_vN`.
6. Progress/errors on stderr; summary on the human-readable stream as today.

**Success exit**: `0`  
**Typical failures**: invalid project path, validation failure, I/O error → non-zero; no success artifact published for that failed write.

### `merge` (new)

```text
grapheinstein merge INPUT_GRAPH [INPUT_GRAPH ...] --output PATH [--compress] [--config PATH]
```

| Option / arg | Type | Default | Description |
|--------------|------|---------|-------------|
| `INPUT_GRAPH` | path | required (≥2) | Graph artifacts to combine (`.json` or `.json.gz`) |
| `--output` / `-o` | path | required | Destination for merged graph |
| `--compress` | flag | config or off | Write gzip-compressed merged artifact |

**Behavior**:

1. If fewer than two inputs → usage error, non-zero exit, no write.
2. Load each input (gzip-aware); validate; require `schema_version == 6.0.0` matching the tool.
3. Union nodes/edges per [data-model.md](../data-model.md); on conflict → error naming conflicting `id` (and inputs), non-zero exit, **no** success output.
4. Set merge graph metadata (`merged`, `merged_from`, fresh `generated_at`, shared or divergent roots).
5. Validate result; atomic write to output (compression rule applies).
6. Print a short merge summary (input count, node/edge totals, output path) on the human-readable stream.

**Success exit**: `0`

### `visualize` / `status` (compatibility)

Prefer the shared gzip-aware loader so `.json.gz` inputs work the same as `.json`. Behavior otherwise unchanged from prior contracts.

## Non-goals (this contract)

- Soft merge / last-write-wins
- Re-indexing the filesystem as part of `merge`
- Changing default index flags (`--compress` / `--versioned` remain opt-in)
- Bumping graph `schema_version` beyond `6.0.0`
