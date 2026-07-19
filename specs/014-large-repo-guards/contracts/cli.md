# CLI Contract: Large Repo Guards

**Feature**: `014-large-repo-guards`  
**CLI contract version**: `14.0.0` (additive; graph schema remains `6.0.0`)

## Entrypoint

- Console script: `grapheinstein`
- Module: `python -m grapheinstein`

## Global / shared options

Unchanged: `--config`, `--help`.  
Config precedence: CLI flags > `--config` file > `~/.grapheinstein/config.yaml` > built-ins.

Human messages / progress / logs: **stderr** only.

## Additive config keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `code_only` | bool | `false` | Apply code-only default ignores; restrict reference *sources* to code extensions |
| `include_generated_docs` | bool | `false` | When true, do not apply `CODE_ONLY_DEFAULT_IGNORES` even if `code_only` |
| `max_reference_scan_bytes` | positive int | `262144` | Max bytes read per file for reference linking |
| `max_reference_scan_ops` | positive int | `5000000` | Reject when `eligible_scan_files * unique_basenames` exceeds (unless allow) |
| `max_non_code_share` | float (0–1] | `0.85` | Reject when `code_only` and non-code byte share exceeds (unless allow) |
| `max_total_bytes` | positive int | `838860800` | Reject when inventoried regular-file bytes exceed |
| `max_file_count` | positive int | `20000` | Reject when inventoried regular-file count exceeds |
| `timeout_seconds` | int ≥ 0 | `0` | Cooperative index timeout; `0` disables |
| `large_repo_policy` | `reject` \| `allow` | `reject` | `allow` bypasses scan-ops and non-code-share gates only |

### Code-only default ignores

Applied when `code_only` is true and `include_generated_docs` is false (gitignore-style, via pathspec):

```yaml
# Built-in (not necessarily written to user config; documented here)
- "docs/"
- "docs/dyn/"
- "**/docs/dyn/"
- "discovery_cache/"
- "**/discovery_cache/"
```

Merged with project `.gitignore` and user `ignored_patterns`.

**Compatibility**: Omitting new keys uses defaults above. Unknown keys: warn and ignore (unchanged). Graph `schema_version` stays `6.0.0`.

## Commands

### `index` (extended)

```text
grapheinstein index PROJECT_PATH
  [--output PATH]
  [--config PATH]
  [--code-only]
  [--include-generated-docs]
  [--allow-large-repo]
  [--languages ...]
  [--include-docs] [--include-pdfs] [--transcribe-media]
  [--enrich-llm ...]
  [--compress] [--versioned]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--code-only` | flag | off | Set `code_only` for this run |
| `--include-generated-docs` | flag | off | Set `include_generated_docs` for this run |
| `--allow-large-repo` | flag | off | Set `large_repo_policy=allow` for this run |

Numeric thresholds (`max_reference_scan_*`, `max_total_bytes`, `max_file_count`, `timeout_seconds`) are configured via YAML in this increment; CLI flags for them are optional polish if already patterned in the codebase—config MUST suffice for SC validation.

**Behavior additions**:

1. Resolve effective ignores (including code-only defaults when applicable).
2. Discover inventory; apply `max_file_size` oversize metadata as today.
3. Enforce `max_total_bytes` / `max_file_count`; on exceed → exit non-zero, no success graph.
4. Compute scan-cost estimate; if ops/share gates fail and policy is `reject` → exit non-zero with remediation on stderr (mention `--code-only`, ignores, `--allow-large-repo`, narrowing project path).
5. Run bounded reference linking (skip oversize / non-eligible; cap bytes).
6. Continue structure / optional modalities / persist as today.
7. If `timeout_seconds` &gt; 0 and exceeded → exit non-zero; message includes phase; no success graph.

**Exit codes**:

| Code | Meaning |
|------|---------|
| `0` | Successful complete index; graph written |
| `1` | Usage / config / path / generic failure (existing) |
| `2` | Large-repo / preflight reject (size, count, scan-ops, or non-code share) |
| `3` | Index timeout |

(If implementing on a platform that already reserved `2`/`3`, document mapping in help; tests assert distinct non-zero for reject vs timeout.)

### Default (no subcommand)

Same as `index`, including new flags.

### `init` (template)

Starter YAML comments MUST document the new keys and code-only default-ignore behavior.

## Non-goals (this contract)

- Path sharding, resume, or multi-graph merge for one logical index
- Changing whole-token reference matching rules for eligible files
- Bumping graph `schema_version`
