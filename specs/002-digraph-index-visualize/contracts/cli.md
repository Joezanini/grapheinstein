# CLI Contract: grapheinstein (index + visualize)

**Feature**: `002-digraph-index-visualize`  
**CLI contract version**: 2.0.0 (paired with graph schema_version `2.0.0`)

## Entrypoint

- Console script: `grapheinstein`
- Module: `python -m grapheinstein`

## Global / shared options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config` | path | unset | YAML config path; overrides user config for this run |
| `--help` | flag | — | Show help |

Config precedence (unchanged): CLI flags > `--config` file > `~/.grapheinstein/config.yaml` > built-ins.

User config path: `~/.grapheinstein/config.yaml`  
Supported keys: `output` (string), `log_level` (string).

## Commands

### Default (no subcommand)

```text
grapheinstein PROJECT_PATH [--output PATH] [--config PATH]
```

**Behavior**: Same as `grapheinstein index PROJECT_PATH ...`  
**Success exit**: `0`

### `index`

```text
grapheinstein index PROJECT_PATH [--output PATH] [--config PATH]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `PROJECT_PATH` | path | required | Project folder to index |
| `--output` / `-o` | path | config or `graph.json` | Destination graph artifact |

**Behavior**:
1. Validate `PROJECT_PATH` is an existing readable directory
2. Discover files/dirs respecting `.gitignore`; do not follow symlinks (symlink → `file` node)
3. Build directed graph: `contains` + whole-token basename `references` (provenance `extracted`)
4. Write graph artifact per [graph-json.md](./graph-json.md) (overwrite if exists)
5. Print a short success summary to the human console stream

**Exit codes**:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Usage / validation / I/O / config error |

### `visualize`

```text
grapheinstein visualize --input PATH [--dot PATH] [--config PATH]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--input` / `-i` | path | required | Existing graph.json to load |
| `--dot` | path | unset | If set, write DOT export to this path (overwrite if exists) |
| `--config` | path | unset | Optional config (logging, etc.) |

**Behavior**:
1. Load and validate graph as schema `2.0.0` new-shape only
2. Always print console summary: file count, dir count, total nodes, `contains` count, `references` count, brief sample
3. If `--dot` provided, write DOT document to that path; still print summary

**Exit codes**:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Missing/unreadable input, unsupported/malformed graph, unwritable DOT path, config error |

### `status` (retained)

```text
grapheinstein status [--output PATH] [--config PATH]
```

**Behavior**: Unchanged command name; stats computed from v2 `type` fields. Old v1 graphs → error (same validation as visualize). Missing graph file → non-zero with clear “no index” message (existing behavior may use exit `2`).

## Output streams

| Stream | Content |
|--------|---------|
| Human console (stderr via Rich/console) | Progress, summaries, errors |
| `--output` file | Graph JSON only |
| `--dot` file | DOT text only |

## Overwrite policy

Writable existing `--output` and `--dot` paths are overwritten without prompting.

## Known subcommands (for default-path rewrite)

`index`, `status`, `visualize` — bare project paths must not be mistaken for these names.
