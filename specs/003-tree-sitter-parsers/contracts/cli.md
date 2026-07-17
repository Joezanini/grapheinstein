# CLI Contract: grapheinstein (code structure index)

**Feature**: `003-tree-sitter-parsers`  
**CLI contract version**: 3.0.0 (paired with graph schema_version `3.0.0`)

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

Supported keys:

| Key | Type | Description |
|-----|------|-------------|
| `output` | string | Default graph output path |
| `log_level` | string | Logging level |
| `languages` | list of strings | Enabled structure-extraction languages (see below) |

### Canonical language ids

`python`, `javascript`, `typescript`, `java`, `go`, `rust`, `cpp`, `sql`

Default when `languages` unset: all eight.

## Commands

### Default (no subcommand)

```text
grapheinstein PROJECT_PATH [--output PATH] [--languages LIST] [--config PATH]
```

**Behavior**: Same as `grapheinstein index PROJECT_PATH ...`  
**Success exit**: `0`

### `index`

```text
grapheinstein index PROJECT_PATH [--output PATH] [--languages LIST] [--config PATH]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `PROJECT_PATH` | path | required | Project folder to index |
| `--output` / `-o` | path | config or `graph.json` | Destination graph artifact |
| `--languages` | string | unset | Comma-separated language ids; when set, replaces config/default for this run |

**Behavior**:
1. Validate `PROJECT_PATH` and resolve config (including languages)
2. If any language id is unknown → exit non-zero with names of invalid ids and the valid set; do not write a success graph
3. Discover files/dirs respecting `.gitignore`; do not follow symlinks
4. Build inventory: `contains` + basename `references` (`extracted`)
5. For each non-ignored regular file mapped to an enabled language: parse structure; add code-entity nodes and `defines` / `imports` / `calls` (`extracted`); on per-file failure, warn and continue
6. Write graph artifact per [graph-json.md](./graph-json.md) schema `3.0.0` (overwrite if exists)
7. Print success summary including file/dir counts, code-entity counts (functions/classes/methods), and edge counts by type

**Exit codes**:

| Code | Meaning |
|------|---------|
| 0 | Success (including when some files skipped for structure) |
| 1 | Usage / validation / I/O / config / unknown language error |

### `visualize` (retained, extended summary)

```text
grapheinstein visualize --input PATH [--dot PATH] [--config PATH]
```

**Behavior**: Load schema `3.0.0` only. Console summary MUST include counts for `file`, `dir`, `function`, `class`, `method` nodes and for `contains`, `references`, `defines`, `imports`, `calls` edges (zero when absent), plus a brief sample. Optional `--dot` still writes DOT and keeps the summary.

**Exit codes**: `0` success; `1` missing/unreadable input, unsupported/malformed graph (including schema `2.0.0`), unwritable DOT, config error.

### `status` (retained)

```text
grapheinstein status [--output PATH] [--config PATH]
```

**Behavior**: Stats from schema `3.0.0` graphs only (include code-entity totals when present). Old schemas → unsupported-format error. Missing graph → clear “no index” failure (existing exit convention).

## Output streams

| Stream | Content |
|--------|---------|
| Human console (stderr via Rich/console) | Progress, summaries, warnings (skipped parses), errors |
| `--output` file | Graph JSON only |

## Overwrite policy

Writable existing `--output` and `--dot` paths are overwritten without prompting.

## Known subcommands (for default-path rewrite)

`index`, `status`, `visualize` — and any new option tokens such as `--languages` must be treated as options with values in the default-path rewriter (`_OPTS_WITH_VALUE`).
