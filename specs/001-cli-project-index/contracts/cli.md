# CLI Contract: grapheinstein

**Feature**: `001-cli-project-index`  
**CLI contract version**: 1.0.0 (paired with graph schema_version `1.0.0`)

## Entrypoint

- Console script: `grapheinstein`
- Module: `python -m grapheinstein`

## Global options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config` | path | unset | YAML config path; overrides user config for this run |
| `--output` / `-o` | path | from config or `graph.json` | Graph artifact path |
| `--help` | flag | — | Show help |

Config precedence: CLI flags > `--config` file > `~/.grapheinstein/config.yaml` > built-ins.

User config path: `~/.grapheinstein/config.yaml`  
Supported keys: `output` (string), `log_level` (string).

## Commands

### Default (no subcommand)

```text
grapheinstein PROJECT_PATH [--output PATH] [--config PATH]
```

**Behavior**: Same as `grapheinstein index PROJECT_PATH ...`  
**Success exit**: `0`  
**Graph output**: written only to the resolved output file path  
**Human output / logs**: stderr

### `index`

```text
grapheinstein index PROJECT_PATH [--output PATH] [--config PATH]
```

**Behavior**:
1. Validate `PROJECT_PATH` is an existing readable directory
2. Discover files/dirs respecting `.gitignore`
3. Write graph artifact per [graph-json.md](./graph-json.md)
4. Print a short success summary (node counts, output path) to stderr

**Exit codes**:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Usage / validation / I/O / config error |

### `status`

```text
grapheinstein status [--output PATH] [--config PATH]
```

**Behavior**:
1. Resolve graph path from `--output` / config / default `graph.json`
2. If file missing: print that no index is available; exit `2`
3. If present: load artifact; print file count, directory count, total nodes, graph path, and `project_root` when available

**Exit codes**:

| Code | Meaning |
|------|---------|
| 0 | Graph found; stats printed |
| 1 | Invalid config / unreadable or invalid graph JSON |
| 2 | Graph file not found |

## Error message requirements

- Missing/non-directory project path: name the path and the problem
- Unwritable output: name the path
- Invalid config: name the file and the parse/validation issue
- Messages on stderr; exit non-zero

## Non-goals (this contract version)

- `explain`, `path`, `ask` subcommands
- Writing graph JSON to stdout by default
- Network calls
