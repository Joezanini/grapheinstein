# CLI Contract: Config, Cache & Init

**Feature**: `011-config-cache-init`  
**CLI contract version**: `11.0.0` (additive; graph schema remains `6.0.0`)

## Entrypoint

- Console script: `grapheinstein`
- Module: `python -m grapheinstein`

## Global / shared options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config` | path | unset | YAML config path; overrides user config for this run |
| `--help` / `-h` | flag | — | Show help (complete text required on root and every subcommand) |

Config precedence: CLI flags > `--config` file > `~/.grapheinstein/config.yaml` > built-ins.

User config path: `~/.grapheinstein/config.yaml`

### Supported config keys (additive)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ignored_patterns` | list of strings | See below | Extra gitignore-style patterns beyond project `.gitignore` |
| `embedding_model` | string | same as built-in `llm_model` default | Model id for embedding calls |
| `llm_model` | string | existing default | Model id for LLM enrichment |
| `max_file_size` | positive int | `10485760` | Max file size in **bytes**; larger files skip content parsing |
| `cache_dir` | string | `~/.grapheinstein/cache` | Directory for parse/embedding cache |

Default `ignored_patterns`:

```yaml
ignored_patterns:
  - ".venv/"
  - "venv/"
  - "node_modules/"
  - "__pycache__/"
  - ".git/"
  - "*.pyc"
  - ".DS_Store"
```

**Compatibility**:
- Omitting any new key uses the default above.
- If `embedding_model` is omitted but `llm_model` is set, embeddings use `llm_model`.
- Unknown keys: warn on stderr and ignore (unchanged).
- Existing keys (`output`, `log_level`, `languages`, `llm_base_url`, explain/path/query keys, etc.) remain valid.

Human messages / progress / logs: **stderr** only.  
Machine graph / JSON answers: file path or stdout as each command already defines — never mixed with progress.

## Commands

### `init` (new)

```text
grapheinstein init [--output PATH] [--force]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output` / `-o` | path | `~/.grapheinstein/config.yaml` | Destination config file |
| `--force` | flag | off | Overwrite existing file without prompting |

**Behavior**:

1. Resolve destination path (expanduser).
2. If parent directory missing, create it (fail clearly on permission errors).
3. If file exists and `--force` is false:
   - Interactive TTY: prompt to confirm overwrite; decline → exit 1, no write.
   - Non-interactive: print error suggesting `--force`; exit 1, no write.
4. Write starter YAML template with commented keys including at least: `ignored_patterns`, `embedding_model`, `llm_model`, `max_file_size`, `cache_dir`, plus `output`, `log_level`, `llm_base_url`.
5. Print absolute path written to stderr; exit 0.

**Exit codes**:

| Code | Meaning |
|------|---------|
| 0 | Config written |
| 1 | Refused overwrite, I/O error, or invalid usage |

`init` MUST be a first-class subcommand (not rewritten to `index`).

### `index` (behavior extensions)

```text
grapheinstein index PROJECT_PATH [existing options...] [--config PATH]
```

**Additional behavior** (existing flags unchanged):

1. Apply `ignored_patterns` from resolved config in addition to `.gitignore`.
2. For each regular file whose size exceeds `max_file_size`: do not parse/chunk/embed; keep a `file` node with `metadata.skipped: "oversize"` and `metadata.size_bytes` when practical; log/summary counts skipped oversize files.
3. Use `cache_dir` for AST/chunk/embedding reuse; create directory if needed.
4. Use `embedding_model` for embedding work when embeddings run; use `llm_model` for enrichment.
5. Show Rich progress on stderr when interactive; periodic logs otherwise.
6. On success, summary MAY include `cache hits` / `misses` / `skipped oversize`.

**Exit codes**: unchanged (`0` success, `1` usage/config/I/O, existing special cases).

### Other commands (`status`, `visualize`, `merge`, `explain`, `path`, `query`)

- MUST load the expanded config schema without requiring new keys.
- MUST use `embedding_model` (with fallback rules) wherever they call embeddings.
- MUST keep complete `--help` text.
- Long embedding batches SHOULD show progress when interactive.

## Help text requirements

- Root help lists all subcommands including `init`.
- Every option documents its default when not obvious.
- Root or `init` help includes at least one example of `grapheinstein init` and using `--config`.

## Error message requirements

- Invalid config: name file and key/problem; exit non-zero; no stack-only output at default log level.
- Init overwrite refused: name path and mention `--force`.
- Cache write failure (disk full / permission): name `cache_dir` (or file); exit non-zero rather than silent disable.
- Single corrupt cache entry: warn, recompute, continue.

## Non-goals

- No graph `schema_version` change.
- No remote cache or config sync.
- No `tqdm` dependency requirement (Rich progress is the contract).
- No interactive multi-step setup wizard beyond overwrite confirm.
