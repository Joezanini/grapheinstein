# Feature Specification: Config, Cache & Init Polish

**Feature Branch**: `011-config-cache-init`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Add comprehensive config.yaml (ignored_patterns, embedding_model, llm_model, max_file_size, cache_dir). Implement caching for parsed chunks/ASTs/embeddings. Add grapheinstein init to create config. Full help text, progress bars, error handling."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Initialize Local Configuration (Priority: P1)

A developer new to Grapheinstein runs an init command and receives a ready-to-edit configuration file at the standard user location, with documented defaults for ignore patterns, models, file-size limits, and cache location. They can adjust those values once and have every subsequent command pick them up without repeating flags.

**Why this priority**: Without a guided way to create a complete config, users struggle to discover and set the settings that make indexing reliable and repeatable.

**Independent Test**: With no user config present, run init, confirm a valid config file is created with the documented keys and defaults, then run a command that loads that config and applies at least one non-default setting.

**Acceptance Scenarios**:

1. **Given** no config file exists at the standard user location, **When** the user runs `grapheinstein init`, **Then** a config file is created there containing at least `ignored_patterns`, `embedding_model`, `llm_model`, `max_file_size`, and `cache_dir` with sensible documented defaults.
2. **Given** a config file already exists at the standard user location, **When** the user runs init without an overwrite confirmation, **Then** the tool refuses to overwrite and reports a clear message telling the user how to proceed.
3. **Given** the user explicitly requests overwrite (or confirms when prompted), **When** init runs against an existing file, **Then** the file is replaced with a fresh template (or merged only if the product documents merge behavior) and the user is told where it was written.
4. **Given** the user passes an explicit output path for init, **When** init completes, **Then** the config is written to that path instead of (or in addition to, if documented) the standard location.

---

### User Story 2 - Configure Indexing Behavior via YAML (Priority: P1)

A developer customizes which paths to skip beyond `.gitignore`, which local embedding and language models to use, the maximum file size to process, and where on-disk caches live—by editing `config.yaml` or pointing `--config` at a project-specific file—so indexing matches their project’s constraints without cloud services.

**Why this priority**: These settings directly control correctness (what gets indexed), performance (what is skipped), and offline model choice; they are the core of the local-first configuration surface.

**Independent Test**: Provide a config with custom `ignored_patterns`, `max_file_size`, model names, and `cache_dir`; index a fixture project that exercises each setting; verify ignored/oversize files are omitted, models and cache location from config are used, and CLI flags still override config when supplied.

**Acceptance Scenarios**:

1. **Given** a config listing additional `ignored_patterns`, **When** the user indexes a project containing matching paths, **Then** those paths are excluded in addition to `.gitignore` exclusions.
2. **Given** a config with `max_file_size` set below the size of a large fixture file, **When** indexing runs, **Then** that file is skipped (with a visible warning or status note) and indexing otherwise succeeds.
3. **Given** a config with `embedding_model` and `llm_model` set, **When** a command that uses embeddings or LLM enrichment runs, **Then** those configured model identifiers are used unless overridden by CLI flags.
4. **Given** a config with `cache_dir` set to a writable path, **When** indexing or embedding work runs, **Then** cache artifacts are stored under that directory.
5. **Given** an invalid value for a known config key (wrong type, empty model name, non-positive size), **When** any command loads that config, **Then** the command fails with a clear validation error naming the key and problem.

---

### User Story 3 - Re-index Faster with Local Artifact Cache (Priority: P2)

After an initial index, a developer changes a small subset of files and re-indexes. Unchanged content reuses previously stored parse results (chunks / syntax structure) and embeddings from the local cache, so the second run finishes materially faster and does not redo expensive work for unchanged files.

**Why this priority**: Caching is the main user-visible payoff of durable intermediate artifacts and makes iterative local workflows practical on real projects.

**Independent Test**: Index a fixture project twice without changing files and confirm the second run reports cache hits (or equivalent progress/summary) and completes faster; change one file and confirm only that file’s dependent work is recomputed while others remain cache hits.

**Acceptance Scenarios**:

1. **Given** a successful first index with caching enabled (default), **When** the user re-indexes the same project with unchanged files, **Then** previously stored parse and embedding artifacts are reused for unchanged content.
2. **Given** a file whose content changed since the last index, **When** the user re-indexes, **Then** that file’s parse and embedding work is recomputed and the cache is updated for the new content.
3. **Given** the user changes `embedding_model` (or another setting that invalidates embedding compatibility), **When** they re-index, **Then** embeddings are regenerated under the new model rather than silently reusing incompatible cached vectors.
4. **Given** the cache directory is missing or empty, **When** indexing runs, **Then** the tool creates the cache as needed and proceeds without requiring manual setup.
5. **Given** a corrupted or unreadable cache entry for a file, **When** indexing encounters it, **Then** the tool recomputes that entry, continues the run, and does not fail the whole index solely because of one bad cache record.

---

### User Story 4 - Discoverable CLI with Progress and Clear Errors (Priority: P3)

A developer exploring the tool relies on complete help text for every command, sees progress during long indexing or enrichment runs, and receives actionable error messages (wrong paths, bad config, missing local models) instead of opaque failures or silent exits.

**Why this priority**: Polish that makes the existing CLI trustworthy for daily use and for agents that parse help and stderr; it does not add new graph capabilities but is required for a production-quality local tool.

**Independent Test**: Invoke `--help` on the root command and each subcommand (including `init`) and confirm descriptions, options, and examples are present; run a long index and observe progress updates; trigger common failure modes and confirm non-zero exit plus clear stderr messages.

**Acceptance Scenarios**:

1. **Given** Grapheinstein is installed, **When** the user runs help on the root command and on each subcommand including `init`, **Then** each help screen documents purpose, required arguments, options, and defaults in plain language.
2. **Given** a long-running index or enrichment operation, **When** the command runs in an interactive terminal, **Then** the user sees ongoing progress (e.g., files processed / stage) on the diagnostic stream without corrupting machine-oriented output files.
3. **Given** a failure such as missing project path, unreadable config, or unavailable local model when one is required, **When** the command exits, **Then** the exit status is non-zero and the error message states what failed and what the user can try next.
4. **Given** progress or logging is active, **When** structured results are written to a file or stdout as specified by the command, **Then** progress and human messages do not mix into that structured payload.

---

### Edge Cases

- Init cannot create the parent directory for the config path (permissions): fail with a clear error; do not claim success.
- Config file exists but is empty or contains only comments: treat as empty mapping and apply built-in defaults (same as missing optional keys).
- Unknown config keys: ignore with a warning, or reject—product MUST document one consistent behavior; default is warn and ignore unknown keys so forward-compatible templates do not break older installs.
- `max_file_size` of zero or negative: validation error.
- `ignored_patterns` empty list: valid; only `.gitignore` (and built-in safety ignores if any) apply.
- `cache_dir` on a full disk or read-only filesystem: fail the write with a clear error; prefer failing that cache write over silently disabling cache without notice.
- Concurrent indexes sharing the same cache directory: MUST NOT corrupt the cache into an unrecoverable state; at worst one run recomputes overlapping entries.
- Non-interactive environments (CI, piped stderr): progress MAY degrade to periodic log lines; commands MUST still succeed and MUST NOT hang waiting for overwrite prompts (init overwrite in non-interactive mode requires an explicit force flag).

## Requirements *(mandatory)*

<!--
  Grapheinstein constitution constraints in scope for this feature:
  - Local-first / offline-capable defaults; no required cloud APIs
  - CLI subcommands; human progress/errors on stderr; structured results separate
  - Config via YAML for ignore overrides, model paths, and cache locations
  - Intermediate artifacts MUST be cacheable on disk for incremental re-index
  - Incremental simplicity: polish config/cache without adding hosted backends
-->

### Functional Requirements

- **FR-001**: The system MUST support a comprehensive YAML configuration schema that includes at least: `ignored_patterns` (list of path patterns), `embedding_model` (string), `llm_model` (string), `max_file_size` (positive size limit), and `cache_dir` (filesystem path).
- **FR-002**: Configuration loading MUST preserve existing precedence: CLI flags > explicit `--config` file > standard user config `~/.grapheinstein/config.yaml` > built-in defaults.
- **FR-003**: Missing optional config keys MUST fall back to documented built-in defaults; absence of the user config file MUST NOT be an error for commands other than those that explicitly require a config path.
- **FR-004**: Users MUST be able to run `grapheinstein init` to create a starter config file populated with documented defaults and brief inline comments explaining each key.
- **FR-005**: `init` MUST refuse to overwrite an existing config file unless the user passes an explicit force/overwrite option (non-interactive) or confirms when prompted in an interactive session.
- **FR-006**: Discovery and indexing MUST apply `ignored_patterns` from config in addition to `.gitignore` (and any existing built-in ignores), so matching paths are excluded from processing.
- **FR-007**: Indexing MUST skip files whose size exceeds `max_file_size`, record a per-file skip reason visible in logs or summary, and continue processing remaining files.
- **FR-008**: Commands that perform embedding MUST use `embedding_model` from the resolved config unless overridden by a CLI flag; commands that perform LLM enrichment MUST use `llm_model` similarly.
- **FR-009**: The system MUST persist reusable intermediate artifacts for at least: parsed text chunks, parse/syntax structures used by code parsers, and embedding vectors, under the resolved `cache_dir`.
- **FR-010**: Cache entries MUST be keyed so that unchanged file content with the same relevant settings (including embedding model for vectors) produces a cache hit on subsequent runs.
- **FR-011**: Changing embedding model (or other settings that affect artifact meaning) MUST invalidate or namespace incompatible cached embeddings so stale vectors are not reused.
- **FR-012**: Cache misses and corrupt entries MUST trigger recomputation for the affected item without aborting the entire index when other files succeed.
- **FR-013**: Every CLI command (root and subcommands, including `init`) MUST provide complete help text describing purpose, arguments, options, and defaults.
- **FR-014**: Long-running operations (indexing, enrichment, embedding) MUST show progress to the user on the diagnostic stream when running in an interactive terminal.
- **FR-015**: On user-facing failures (paths, permissions, invalid config, required local model unavailable), the CLI MUST exit non-zero with an actionable error message on the diagnostic stream.
- **FR-016**: Human-oriented progress, logs, and errors MUST NOT corrupt machine-oriented outputs (graph files, JSON answers on stdout or declared output paths).
- **FR-017**: All configuration, caching, and init behavior MUST operate fully offline with local filesystem storage; no cloud service is required for this feature.
- **FR-018**: Existing commands (`index`, `status`, `explain`, `path`, `query`, and others already shipped) MUST continue to load the expanded config schema without breaking previously valid config files that omit the new keys.

### Key Entities

- **User Config File**: YAML document at the standard user path or an explicit path; holds defaults for ignore patterns, models, size limits, cache location, and any already-supported keys.
- **Ignore Pattern Set**: User-supplied path patterns combined with project `.gitignore` rules to decide which paths are out of scope.
- **Cache Store**: On-disk directory (from `cache_dir`) holding reusable parse chunks, syntax structures, and embeddings keyed by content and relevant settings.
- **Cache Entry**: One reusable artifact tied to a source file (or chunk identity), content fingerprint, artifact kind, and settings fingerprint; may be hit, miss, or invalidated.
- **Init Template**: The default documented config content written by `grapheinstein init`, including keys, defaults, and explanatory comments.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can create a valid starter config with `grapheinstein init` in under 30 seconds without reading external documentation beyond the command’s own help text.
- **SC-002**: On a project of at least 200 indexable files, a second unchanged re-index completes in at most 50% of the wall-clock time of a cold (empty-cache) index on the same machine and settings.
- **SC-003**: 100% of CLI subcommands expose help that lists every public option and its default; spot-check by users or tests finds no subcommand with empty or placeholder-only help.
- **SC-004**: In usability checks, at least 9 of 10 first-time users correctly identify how to change ignore patterns, models, max file size, and cache location from the generated config file alone.
- **SC-005**: When config validation fails, 100% of tested invalid configs produce a non-zero exit and an error message that names the offending key (or file path) without a stack trace as the only output.
- **SC-006**: Files matching `ignored_patterns` or exceeding `max_file_size` never appear as successfully processed content nodes in the resulting graph for those runs (verified on fixture projects).

## Assumptions

- Standard user config path remains `~/.grapheinstein/config.yaml`; `init` writes there by default and may accept an explicit path for project-local configs.
- Default `cache_dir` is under the user’s Grapheinstein data directory (e.g., `~/.grapheinstein/cache`) unless overridden.
- Default `max_file_size` is large enough for typical source and docs (on the order of several megabytes) and is documented in the init template.
- Default `ignored_patterns` includes common bulky or generated paths not always covered by every project’s `.gitignore` (e.g., virtualenvs, dependency directories), and remains editable.
- `embedding_model` is distinct from `llm_model` so users can choose a lighter embedding model while keeping a separate enrichment model; when only `llm_model` is present in older configs, embeddings may continue to use that value until `embedding_model` is set.
- Cache backend and progress-library choices are implementation details for planning; the product requirement is durable local reuse of chunks, parse structures, and embeddings, plus visible progress on long runs.
- Caching is enabled by default; a future “disable cache” switch is out of scope unless needed for debugging and can be added later without changing this feature’s success criteria.
- This feature does not introduce remote vector databases, hosted config sync, or a GUI settings editor.
