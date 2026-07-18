# Research: Config, Cache & Init Polish

**Feature**: `011-config-cache-init`  
**Date**: 2026-07-17

## R1. Cache backend (joblib vs sqlite vs plain files)

**Decision**: Use **stdlib `sqlite3` + content-addressed blob files** under `cache_dir`.

- Layout:
  - `{cache_dir}/index.sqlite` — metadata table: `key`, `kind`, `content_hash`, `settings_hash`, `blob_path`, `created_at`, `size_bytes`
  - `{cache_dir}/blobs/{aa}/{aabbcc…}` — opaque blob files (pickle or JSON bytes depending on kind)
- API surface in `core/cache.py`: `get(kind, key, content_hash, settings_hash) -> bytes | None`, `put(...)`, `stats()` for hit/miss summary.
- Atomic blob write via temp + `os.replace`; sqlite row inserted after blob is durable.
- Corrupt/unreadable blob or row → treat as miss, delete bad row when safe, recompute.

**Rationale**: Spec requires durable reuse of chunks, parse structures, and embeddings without a hosted store. SQLite is stdlib (no new dependency), queryable for stats/invalidation, and works well with separate large blobs. Matches constitution incremental simplicity.

**Alternatives considered**:
- **joblib.Memory** — excellent decorator UX and numpy-friendly, but adds a required dependency when stdlib covers the need; rejected for v1 (may revisit if Memory’s hashing becomes worth the dep).
- **Plain hash-directory only (no sqlite)** — simpler but harder to report hit rates / purge by kind / detect orphans.
- **Remote/vector DB** — violates local-first constitution; rejected.

## R2. Cache keying and invalidation

**Decision**:

1. **Content hash**: SHA-256 of raw file bytes (or of canonical chunk text for embedding keys derived from chunks).
2. **Settings hash**: SHA-256 of a stable JSON object of settings that affect the artifact, e.g.:
   - `chunk` / `ast`: parser version string + language id + relevant parser flags
   - `embedding`: `embedding_model` + embedding API shape version (constant string in code)
3. **Logical key**: relative path (posix) for file-scoped artifacts; `{rel_path}#{chunk_id}` for per-chunk embeddings when needed.
4. **Hit** only when `(kind, key, content_hash, settings_hash)` matches.
5. Changing `embedding_model` changes settings hash → automatic miss for embeddings (FR-011).
6. No global “clear cache” command required in this feature; users may delete `cache_dir`.

**Rationale**: Spec FR-010–012; content + settings fingerprints avoid silent stale reuse.

**Alternatives considered**:
- mtime-only invalidation — fragile across copy/checkout; rejected.
- Single global cache version bump for all kinds — coarse; settings hash per kind is enough.

## R3. What gets cached in v1

**Decision**: Cache three kinds during index (and embedding paths used by explain/path/query when they compute vectors for graph text):

| Kind | Payload | Produced by |
|------|---------|-------------|
| `ast` | Serialized parse result needed to rebuild structure nodes/edges without re-running Tree-sitter (language-specific stable dict or bytes) | Code parsers |
| `chunk` | List of text chunks / section payloads for docs/PDF/media text extraction paths that are expensive to recompute | Docs/PDF/media parsers |
| `embedding` | Vector `list[float]` (or packed float32 bytes) for a chunk/node text | Ollama `embed_texts` wrappers |

Inventory-only file discovery (stat + path walk) is cheap enough that caching the path list is optional and **out of scope**.

**Rationale**: Spec FR-009 names chunks, ASTs, embeddings. Focus cache on expensive steps to hit SC-002.

**Alternatives considered**:
- Cache entire `graph.json` — different concern (versioned outputs already exist); rejected.
- Cache LLM chat completions — nondeterministic / prompt-sensitive; out of scope for this feature.

## R4. New config keys and defaults

**Decision**:

| Key | Type | Default | Notes |
|-----|------|---------|-------|
| `ignored_patterns` | list[str] | `[".venv/", "venv/", "node_modules/", "__pycache__/", ".git/", "*.pyc", ".DS_Store"]` | gitignore-style via pathspec; applied **in addition to** `.gitignore` |
| `embedding_model` | str | same built-in default as today’s `llm_model` | Used for embedding calls |
| `llm_model` | str | existing default | Unchanged semantics for enrichment |
| `max_file_size` | int (bytes) | `10485760` (10 MiB) | Positive int only; skip oversized files |
| `cache_dir` | str/path | `~/.grapheinstein/cache` (expanded at load) | Created on first use |

**Compatibility**:
- Older configs omitting new keys keep working (FR-018).
- If `embedding_model` omitted but `llm_model` set → embeddings use `llm_model` (spec assumption).
- Unknown keys: continue existing behavior — **warn and ignore** (already implemented).

**Rationale**: Spec FR-001–003, Assumptions; 10 MiB covers typical source/docs while skipping huge binaries/media dumps unless raised.

**Alternatives considered**:
- Human-readable size strings (`"10MB"`) — nicer UX but more parsing edge cases; defer (init comments document bytes).
- Project-local default cache (`.grapheinstein/cache` in project) — risk of committing caches; user-home default is safer; override via config.

## R5. Combining ignore rules

**Decision**: Build two pathspecs (or one combined):

1. Project `.gitignore` (existing `load_gitignore_spec`)
2. Config `ignored_patterns` via `pathspec.PathSpec.from_lines("gitignore", patterns)`

A path is ignored if **either** matches. Keep skipping `.git` as today. Empty `ignored_patterns` is valid.

**Rationale**: Spec FR-006; pathspec already in the stack.

**Alternatives considered**:
- Only config patterns replace gitignore — would break existing behavior; rejected.
- fnmatch only — weaker than gitignore semantics users expect.

## R6. `grapheinstein init`

**Decision**:

```text
grapheinstein init [--output PATH] [--force]
```

- Default output: `~/.grapheinstein/config.yaml` (create parent dir).
- Template: YAML with **all** documented keys (new + commonly used existing: `output`, `log_level`, `languages`, `llm_*`, explain/path/query keys optional subset — at minimum the five new keys plus `output`, `log_level`, `llm_model`, `llm_base_url`) and `#` comments explaining each.
- If target exists and `--force` not set:
  - Interactive TTY: `typer.confirm` to overwrite
  - Non-interactive: refuse with message suggesting `--force` (exit 1)
- Overwrite replaces file with fresh template (no merge).
- Success: print absolute path written to stderr; exit 0.

**Rationale**: Spec Stories 1 / FR-004–005 / edge cases for CI.

**Alternatives considered**:
- Interactive questionnaire for each key — heavier; template + comments sufficient for SC-001/SC-004.
- Merge-preserving init — complex and surprising; rejected.

## R7. Progress display (tqdm vs Rich)

**Decision**: Use **Rich `Progress`** (already a dependency) on stderr when `sys.stderr.isatty()`; otherwise emit periodic Loguru info lines (e.g. every N files or stage boundaries). Do **not** add `tqdm`.

Stages with progress during `index`: discovery complete count → parse/enrich files → optional embedding batches. Explain/path/query may show a simple spinner/progress when embedding many texts.

**Rationale**: Spec FR-014/016; Rich already used for tables/console; dual progress libraries add noise. User-facing “progress bars” are satisfied by Rich.

**Alternatives considered**:
- **tqdm** — matches user mention but duplicates Rich; rejected for v1.
- No progress — fails FR-014.

## R8. Help text and error handling polish

**Decision**:

- Expand Typer `help=` on app, every command, and every option to include purpose + default where non-obvious.
- Root app `epilog` with 3–4 example invocations including `init` and `--config`.
- Keep `_fail` / `ConfigError` patterns: stderr via Rich console, non-zero exit, no stack trace unless log level DEBUG.
- Ensure `init` is registered in `_KNOWN_COMMANDS` so `grapheinstein init` is not rewritten to `index`.

**Rationale**: Spec Story 4 / FR-013–015; small CLI contract bump, no graph schema change.

**Alternatives considered**:
- Separate man pages — out of scope.
- Click migration — unnecessary churn.

## R9. Graph schema impact

**Decision**: **No `schema_version` bump.** Cache and config are sidecar concerns. Optional: include `cache_hits` / `cache_misses` / `skipped_oversize` counts in index **stderr summary** only (not required in `graph.json`).

**Rationale**: Constitution schema discipline; FR-018 focuses on config compatibility, not graph format.

**Alternatives considered**:
- Persist cache stats in `graph.graph` metadata — useful later; not required by spec success criteria.

## R10. Wiring points in existing code

**Decision**:

| Area | Change |
|------|--------|
| `utils.AppConfig` / `load_config` | New fields + coercion |
| `core/index.discover_paths` | Accept extra pathspec + `max_file_size` skip |
| `core/parsers/*` / index orchestration | Call cache get/put around AST/chunk work |
| `core/parsers/llm_ollama.embed_texts` or wrappers in explain/path/query | Cache embeddings by text hash + model |
| `cli.py` | `init` command; richer help; progress hooks; pass new config into index |

**Rationale**: Minimal structural churn; keep single-package layout.

**Alternatives considered**:
- Split `config/` package — optional cleanup, not required for this feature.
