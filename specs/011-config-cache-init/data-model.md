# Data Model: Config, Cache & Init Polish

**Feature**: `011-config-cache-init`  
**Graph schema version**: `6.0.0` (unchanged)

## Entities

### App Config (resolved runtime)

Resolved after precedence: CLI flags > `--config` > `~/.grapheinstein/config.yaml` > built-ins.

| Field | Type | Rules |
|-------|------|-------|
| `output` | string | Non-empty; default `graph.json` |
| `log_level` | string | Non-empty; default `INFO` |
| `languages` | tuple[str, ...] | Existing validation |
| `llm_model` | string | Non-empty |
| `llm_base_url` | string | Non-empty URL |
| `llm_confidence_threshold` | float | ∈ [0.0, 1.0] |
| `embedding_model` | string | Non-empty; default = built-in embedding default; if omitted in file but `llm_model` present, resolve to `llm_model` |
| `ignored_patterns` | tuple[str, ...] | List of gitignore-style patterns; default bulky-path set; empty list allowed |
| `max_file_size` | int | Bytes; must be ≥ 1; default `10485760` |
| `cache_dir` | Path | Absolute after expanduser/resolve; default `~/.grapheinstein/cache` |
| *(existing keys)* | … | `compress`, `versioned`, explain/path/query keys unchanged |

**Validation**:
- Wrong types / empty model strings / non-positive `max_file_size` → `ConfigError` naming the key.
- Unknown keys → warn and ignore (existing behavior).
- Missing file at user path → not an error.

### Init Template (on disk)

| Field | Type | Rules |
|-------|------|-------|
| `path` | Path | Default `~/.grapheinstein/config.yaml` or `--output` |
| `body` | UTF-8 YAML text | Includes comments + default values for required keys (see [contracts/cli.md](./contracts/cli.md)) |
| `force` | bool | When false and path exists → confirm (TTY) or refuse (non-TTY) |

**State transitions**:
1. Missing → write template → success.
2. Exists + no force + non-TTY → error, no write.
3. Exists + no force + TTY + user declines → abort, no write.
4. Exists + force (or TTY confirm) → replace with fresh template.

### Ignore Pattern Set (runtime)

| Field | Type | Rules |
|-------|------|-------|
| `gitignore_spec` | PathSpec \| None | From project `.gitignore` |
| `config_spec` | PathSpec \| None | From `ignored_patterns`; None if empty list |
| `match(rel, is_dir)` | bool | True if either spec matches |

Root `"."` is never ignored. `.git` directory continues to be skipped by name.

### File Skip Decision (runtime)

| Field | Type | Rules |
|-------|------|-------|
| `relative_path` | string | Posix relative id |
| `reason` | enum | `ignored_gitignore` \| `ignored_config` \| `oversize` \| `unreadable` \| … |
| `size_bytes` | int \| null | Set when oversize check ran |

Oversize files remain in the inventory as plain `file` nodes with `metadata.skipped: "oversize"` and `metadata.size_bytes` when practical. They are **not** structure-parsed, chunked, or embedded (no child structure/chunk nodes from that file).

### Cache Store (on disk)

| Field | Type | Rules |
|-------|------|-------|
| `root` | Path | Resolved `cache_dir` |
| `db_path` | Path | `{root}/index.sqlite` |
| `blobs_dir` | Path | `{root}/blobs/` |

Created on first `put` if missing.

### Cache Entry

| Field | Type | Rules |
|-------|------|-------|
| `kind` | enum | `ast` \| `chunk` \| `embedding` |
| `key` | string | File relative path, or `{rel}#{chunk_id}` for chunk embeddings |
| `content_hash` | string | Hex SHA-256 of source bytes or canonical text |
| `settings_hash` | string | Hex SHA-256 of settings JSON affecting this kind |
| `blob_path` | string | Relative path under `blobs/` |
| `payload` | bytes | Opaque serialized artifact |
| `created_at` | string | UTC ISO-8601 |

**Hit rules**: Exact match on `(kind, key, content_hash, settings_hash)`.  
**Miss / corrupt**: Recompute; replace entry; do not fail the whole run.  
**Concurrency**: Best-effort; overlapping writers may race to replace the same key — result must remain a valid entry or a miss on next read (no unrecoverable DB corruption; use WAL mode and atomic blob replace).

### Cache Run Stats (runtime / stderr)

| Field | Type | Rules |
|-------|------|-------|
| `hits` | int | ≥ 0 |
| `misses` | int | ≥ 0 |
| `corrupt_recovered` | int | ≥ 0 |
| `skipped_oversize` | int | ≥ 0 |
| `skipped_ignored` | int | ≥ 0 (optional) |

Emitted in index summary on stderr; not required in `graph.json`.

## Relationships

```text
AppConfig.cache_dir ──owns──> CacheStore
AppConfig.ignored_patterns ──builds──> Ignore Pattern Set (with .gitignore)
Ignore Pattern Set + max_file_size ──filters──> discovery / parse pipeline
Parse pipeline ──get/put──> CacheEntry (ast, chunk)
Embedding calls ──get/put──> CacheEntry (embedding)
init ──writes──> Init Template ──loads as──> AppConfig (on later commands)
```

## Validation Summary

| Rule | Error behavior |
|------|----------------|
| Invalid YAML / non-mapping | ConfigError; exit 1 |
| `max_file_size` ≤ 0 | ConfigError naming key |
| Empty `embedding_model` / `llm_model` | ConfigError |
| `ignored_patterns` not a list of strings | ConfigError |
| `cache_dir` empty string | ConfigError |
| Init cannot create parent dir | Clear error; exit 1 |
| Cache blob unreadable | Miss + recompute; log warning |
