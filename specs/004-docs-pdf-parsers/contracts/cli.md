# CLI Contract: grapheinstein (docs & PDF index)

**Feature**: `004-docs-pdf-parsers`  
**CLI contract version**: 4.0.0 (paired with graph schema_version `4.0.0`)

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

Supported keys (retained + this feature):

| Key | Type | Description |
|-----|------|-------------|
| `output` | string | Default graph output path |
| `log_level` | string | Logging level |
| `languages` | list of strings | Enabled code structure-extraction languages |

Canonical language ids unchanged: `python`, `javascript`, `typescript`, `java`, `go`, `rust`, `cpp`, `sql`.

## Commands

### Default (no subcommand)

```text
grapheinstein PROJECT_PATH [--output PATH] [--languages LIST] [--include-docs] [--include-pdfs] [--config PATH]
```

**Behavior**: Same as `grapheinstein index PROJECT_PATH ...`  
**Success exit**: `0`

### `index`

```text
grapheinstein index PROJECT_PATH [--output PATH] [--languages LIST] [--include-docs] [--include-pdfs] [--config PATH]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `PROJECT_PATH` | path | required | Project folder to index |
| `--output` / `-o` | path | config or `graph.json` | Destination graph artifact |
| `--languages` | string | unset | Comma-separated language ids; when set, replaces config/default for this run |
| `--include-docs` | flag | off | Enable Markdown / TXT / RST heading + link structure enrichment |
| `--include-pdfs` | flag | off | Enable PDF text extraction and section chunk enrichment |

**Behavior**:
1. Validate `PROJECT_PATH` and resolve config (including languages)
2. If any language id is unknown → exit non-zero; do not write a success graph
3. Discover files/dirs respecting `.gitignore`; do not follow symlinks
4. Build inventory: `contains` + basename `references` (`extracted`)
5. Code structure extract for enabled languages (`defines` / `imports` / `calls`); per-file failures warn and continue
6. If `--include-docs`: for non-ignored `.md`/`.markdown`/`.txt`/`.rst`/`.rest` files, extract headings and links; add `heading` nodes, `section_of`, and resolvable `mentions` (`extracted`); per-file failures warn and continue
7. If `--include-pdfs`: for non-ignored `.pdf` files, extract text via PyMuPDF and chunk by sections; add `heading` nodes and `section_of` (`extracted`); per-file failures warn and continue
8. Without each flag, skip that modality’s structure enrichment (file nodes may still exist from inventory)
9. Write graph artifact per [graph-json.md](./graph-json.md) schema `4.0.0` (overwrite if exists)
10. Print success summary including file/dir/code/heading counts and edge counts by type (including `section_of` / `mentions`)

**Exit codes**:

| Code | Meaning |
|------|---------|
| 0 | Success (including when some files skipped for structure) |
| 1 | Usage / validation / I/O / config / unknown language error |

### `visualize` (retained, extended summary)

```text
grapheinstein visualize --input PATH [--dot PATH] [--config PATH]
```

**Behavior**: Load schema `4.0.0` only. Console summary MUST include counts for `file`, `dir`, `function`, `class`, `method`, `heading` nodes and for `contains`, `references`, `defines`, `imports`, `calls`, `section_of`, `mentions` edges (zero when absent), plus a brief sample. Optional `--dot` still writes DOT and keeps the summary.

**Exit codes**: `0` success; `1` missing/unreadable input, unsupported/malformed graph (including schema `3.0.0`), unwritable DOT, config error.

### `status` (retained)

```text
grapheinstein status [--output PATH] [--config PATH]
```

**Behavior**: Stats from schema `4.0.0` graphs only (include heading totals when present). Old schemas → unsupported-format error. Missing graph → clear “no index” failure (existing exit convention).

## Output streams

| Stream | Content |
|--------|---------|
| Human console (stderr via Rich/console) | Progress, summaries, warnings (skipped parses), errors |
| `--output` file | Graph JSON only |

## Overwrite policy

Writable existing `--output` and `--dot` paths are overwritten without prompting.

## Known subcommands / options (default-path rewrite)

- Subcommands: `index`, `status`, `visualize`
- Options with values: `--output`, `-o`, `--config`, `--input`, `-i`, `--dot`, `--languages`
- Boolean flags (no value): `--include-docs`, `--include-pdfs` (must **not** consume the following token as a value)
