---
description: "Task list for Config, Cache & Init Polish"
---

# Tasks: Config, Cache & Init Polish

**Input**: Design documents from `/specs/011-config-cache-init/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — constitution and plan require tests when CLI contracts change (`init` subcommand, expanded config keys, index ignore/size/cache behavior).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: `src/grapheinstein/`, `tests/` at repository root

## Grapheinstein Task Categories *(when applicable)*

- **Config/cache**: YAML keys, `init` template, sqlite+blob cache (`utils.py`, `core/cache.py`)
- **Ingest/parsers**: `ignored_patterns` + `max_file_size` in discovery/index; cache get/put around AST/chunk/embed
- **CLI**: `init` command, help/progress/errors (`cli.py`)
- **Contracts/tests**: CLI init + config/cache integration tests; graph schema stays `6.0.0`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Cache module stub and fixture project for ignore / oversize / cache scenarios

- [x] T001 [P] Create `src/grapheinstein/core/cache.py` stub with module docstring and placeholder public API (`CacheStore`, `get`, `put`, `stats`, `CacheError` / kind constants `ast`/`chunk`/`embedding`) per `plan.md` and `data-model.md`
- [x] T002 [P] Create `tests/fixtures/config_cache/` fixture project: (1) path matching a config ignore pattern (e.g. `secret_dir/`), (2) a clearly oversized file (>100 bytes for low `max_file_size` tests), (3) normal indexable source/docs, (4) optional `.gitignore` entry distinct from config patterns, plus `tests/fixtures/config_cache/README.md` documenting expected skips per `quickstart.md`

**Checkpoint**: Package still installable; cache stub and fixtures in place

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Expanded `AppConfig` keys, defaults, and coercion that all stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Extend `AppConfig` and YAML coercion in `src/grapheinstein/utils.py` with `ignored_patterns` (tuple[str, ...]), `embedding_model` (str), `max_file_size` (int, default `10485760`), `cache_dir` (Path, default `~/.grapheinstein/cache` expanded), plus defaults for `ignored_patterns` per `contracts/cli.md` / `research.md` R4; unknown keys remain warn-and-ignore
- [x] T004 Implement embedding-model fallback in `src/grapheinstein/utils.py`: if `embedding_model` omitted in file but `llm_model` is set, resolved config uses `llm_model` for embeddings; validate non-empty strings and `max_file_size >= 1`
- [x] T005 [P] Add `DEFAULT_CONFIG_TEMPLATE` (commented YAML string) and `write_config_template(path: Path, *, force: bool)` helper in `src/grapheinstein/utils.py` (or `src/grapheinstein/core/config_init.py` if split) covering at least `ignored_patterns`, `embedding_model`, `llm_model`, `max_file_size`, `cache_dir`, `output`, `log_level`, `llm_base_url` per `contracts/cli.md`
- [x] T006 [P] Extend unit tests in `tests/unit/test_config.py` for new keys, defaults, invalid `max_file_size`, empty model strings, and `embedding_model` fallback from `llm_model`

**Checkpoint**: Foundation ready — new config keys load with defaults; template helper available; existing commands still accept old configs

---

## Phase 3: User Story 1 - Initialize Local Configuration (Priority: P1) 🎯 MVP

**Goal**: `grapheinstein init` writes a commented starter config at the standard path or `--output`, refusing overwrite unless `--force` / interactive confirm

**Independent Test**: Run init to a temp path; assert keys present; second init without `--force` fails; `--force` overwrites (quickstart Scenario A)

### Tests for User Story 1

- [x] T007 [P] [US1] Add contract tests for `init` CLI shape (`--output`, `--force`, help lists `init`) in `tests/contract/test_cli_init.py`
- [x] T008 [P] [US1] Add integration tests for init create / refuse-overwrite / `--force` in `tests/integration/test_cli_init_cmd.py`

### Implementation for User Story 1

- [x] T009 [US1] Add `grapheinstein init` command in `src/grapheinstein/cli.py`: register `init` in `_KNOWN_COMMANDS`; options `--output`/`-o` (default `~/.grapheinstein/config.yaml`) and `--force`; call template writer; create parent dirs; interactive `typer.confirm` only on TTY when file exists and not `--force`; non-TTY refuse with message suggesting `--force`
- [x] T010 [US1] Ensure init success prints absolute path on stderr and exits 0; failures use `_fail` with actionable messages (permissions, refuse overwrite) in `src/grapheinstein/cli.py` per `contracts/cli.md`

**Checkpoint**: US1 MVP — users can create a documented starter config without hand-writing YAML

---

## Phase 4: User Story 2 - Configure Indexing Behavior via YAML (Priority: P1)

**Goal**: Resolved config drives extra ignores, max file size skips, embedding/llm model choice, and `cache_dir` location during index (and embedding consumers)

**Independent Test**: Index `tests/fixtures/config_cache/` with custom config; assert ignored paths absent, oversize files marked `metadata.skipped: "oversize"`, `cache_dir` created, models/flags override per precedence (quickstart Scenario B)

### Tests for User Story 2

- [x] T011 [P] [US2] Add unit tests for combining `.gitignore` + `ignored_patterns` and oversize skip decisions in `tests/unit/test_ignore_patterns.py`
- [x] T012 [P] [US2] Extend integration coverage in `tests/integration/test_cli_config_cache.py` for config-driven ignore, oversize metadata, and `cache_dir` creation on index

### Implementation for User Story 2

- [x] T013 [US2] Extend discovery in `src/grapheinstein/core/index.py` to accept/build a config `pathspec` from `ignored_patterns` and ignore paths matching either `.gitignore` or config patterns (root `"."` never ignored; keep `.git` skip)
- [x] T014 [US2] Apply `max_file_size` during index in `src/grapheinstein/core/index.py`: for oversized regular files, emit `file` node with `metadata.skipped: "oversize"` and `metadata.size_bytes`, skip parse/chunk/embed; count skips for summary
- [x] T015 [US2] Thread `embedding_model`, `cache_dir`, `ignored_patterns`, and `max_file_size` from `load_config` through `src/grapheinstein/cli.py` into `index_project` / `build_inventory_graph` (and embedding call sites in `explain`/`path`/`query` for `embedding_model`)
- [x] T016 [US2] Add CLI override flags only where needed for models (reuse existing `--llm-model`; add `--embedding-model` if required by contract/precedence testing) and ensure CLI > config > defaults in `src/grapheinstein/cli.py` / `src/grapheinstein/utils.py`

**Checkpoint**: US1 + US2 — config file fully controls ignore/size/models/cache location for indexing

---

## Phase 5: User Story 3 - Re-index Faster with Local Artifact Cache (Priority: P2)

**Goal**: Durable cache under `cache_dir` reuses AST/chunk/embedding artifacts for unchanged content; model/settings changes invalidate embeddings; corrupt entries recompute

**Independent Test**: Index fixture twice unchanged → cache hits and faster warm run; change one file → miss for that file only; change `embedding_model` → embedding misses (quickstart Scenario C)

### Tests for User Story 3

- [x] T017 [P] [US3] Add unit tests for cache hit/miss, settings-hash invalidation, and corrupt-blob recovery in `tests/unit/test_cache.py`
- [x] T018 [P] [US3] Extend integration tests in `tests/integration/test_cli_config_cache.py` for warm re-index cache hits and embedding-model change invalidation

### Implementation for User Story 3

- [x] T019 [US3] Implement `CacheStore` in `src/grapheinstein/core/cache.py`: sqlite `index.sqlite` + `blobs/` layout, SHA-256 content/settings hashes, atomic blob write + row insert, WAL mode, `get`/`put`/`stats` per `research.md` R1–R2
- [x] T020 [US3] Wire AST/chunk cache get/put around expensive parse paths in `src/grapheinstein/core/index.py` and relevant parsers under `src/grapheinstein/core/parsers/` (kinds `ast` / `chunk`); create `cache_dir` on first use
- [x] T021 [US3] Wire embedding cache (kind `embedding`) around `embed_texts` usage in `src/grapheinstein/core/parsers/llm_ollama.py` and/or call sites in `explain`/`path`/`query`/`index`, keyed by text hash + `embedding_model` settings hash per `research.md` R3
- [x] T022 [US3] On corrupt/unreadable cache entry, log warning, delete/ignore bad row, recompute, continue index; surface hit/miss/corrupt/oversize counts in index stderr summary in `src/grapheinstein/cli.py` / `src/grapheinstein/core/index.py`

**Checkpoint**: US1–US3 — re-index reuses local artifacts; SC-002 target approachable on ≥200-file trees

---

## Phase 6: User Story 4 - Discoverable CLI with Progress and Clear Errors (Priority: P3)

**Goal**: Complete help on every command; Rich progress on long interactive runs; actionable non-zero errors without corrupting machine outputs

**Independent Test**: `--help` on root and all subcommands including `init` documents options/defaults; long index shows progress on TTY; bad config names the key (quickstart Scenario D)

### Tests for User Story 4

- [x] T023 [P] [US4] Extend `tests/contract/test_cli_help.py` so root help lists `init` and every subcommand help is non-empty (options + purpose)
- [x] T024 [P] [US4] Add/extend tests asserting invalid config errors name the key and exit non-zero without stack-only output in `tests/unit/test_config.py` or `tests/integration/test_cli_config_cache.py`

### Implementation for User Story 4

- [x] T025 [US4] Expand Typer `help=` strings and root `epilog` examples (include `init` and `--config`) for all commands/options in `src/grapheinstein/cli.py` per `contracts/cli.md` / FR-013
- [x] T026 [US4] Add Rich `Progress` (stderr) for index stages when `sys.stderr.isatty()`; otherwise periodic Loguru lines; never write progress into graph/JSON outputs in `src/grapheinstein/core/index.py` / `src/grapheinstein/cli.py` per `research.md` R7
- [x] T027 [US4] Audit failure paths (missing project, bad config, cache dir unwritable, init permission errors) to use clear `_fail` / `ConfigError` messages and non-zero exits in `src/grapheinstein/cli.py` / `src/grapheinstein/utils.py` / `src/grapheinstein/core/cache.py`

**Checkpoint**: All stories — CLI is discoverable, progressive, and fails clearly

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and docs hygiene

- [x] T028 [P] Update `README.md` with `grapheinstein init`, new config keys, and cache location notes (keep concise)
- [x] T029 Run scenarios from `specs/011-config-cache-init/quickstart.md` and fix any gaps in `src/grapheinstein/` or tests
- [x] T030 [P] Confirm graph `schema_version` remains `6.0.0` with no accidental bump in `src/grapheinstein/core/graph.py` / fixtures

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **User Story 1 (Phase 3)**: After Foundational — MVP (`init`)
- **User Story 2 (Phase 4)**: After Foundational — needs config keys from Phase 2; independently testable with fixtures
- **User Story 3 (Phase 5)**: After Foundational — ideally after US2 so `cache_dir` is threaded; can stub path for unit tests earlier
- **User Story 4 (Phase 6)**: After US1 at minimum (help for `init`); best after US2–US3 so progress wraps real work
- **Polish (Phase 7)**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependency on US2–US4
- **US2 (P1)**: After Foundational — uses config keys; does not require working cache hits
- **US3 (P2)**: After Foundational; practical dependency on US2 for `cache_dir` plumbing through index
- **US4 (P3)**: Cross-cutting; depends on `init` existing for help coverage

### Within Each User Story

- Tests marked first SHOULD fail before implementation
- Core helpers before CLI wiring
- Story complete before moving to next priority when sequential

### Parallel Opportunities

- T001 ∥ T002 (Setup)
- T005 ∥ T006 (within Foundational after T003–T004)
- T007 ∥ T008 (US1 tests)
- T011 ∥ T012 (US2 tests)
- T017 ∥ T018 (US3 tests)
- T023 ∥ T024 (US4 tests)
- T028 ∥ T030 (Polish)
- After Foundational: US1 and US2 can proceed in parallel if staffed; US3 follows US2 plumbing

---

## Parallel Example: User Story 1

```bash
# Tests in parallel:
Task: "Contract tests for init in tests/contract/test_cli_init.py"
Task: "Integration tests for init in tests/integration/test_cli_init_cmd.py"

# Then implementation:
Task: "Add init command in src/grapheinstein/cli.py"
Task: "Wire success/error paths for init in src/grapheinstein/cli.py"
```

---

## Parallel Example: User Story 3

```bash
# Tests in parallel:
Task: "Unit tests in tests/unit/test_cache.py"
Task: "Integration cache hit/invalidation in tests/integration/test_cli_config_cache.py"

# Then implementation sequentially (same modules):
Task: "Implement CacheStore in src/grapheinstein/core/cache.py"
Task: "Wire AST/chunk cache in index/parsers"
Task: "Wire embedding cache"
Task: "Corrupt recovery + summary stats"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (config keys + template helper)
3. Complete Phase 3: User Story 1 (`init`)
4. **STOP and VALIDATE**: quickstart Scenario A
5. Demo: `grapheinstein init --output /tmp/gs.yaml`

### Incremental Delivery

1. Setup + Foundational → config schema ready
2. US1 → init works (MVP)
3. US2 → ignores / size / models / cache_dir applied
4. US3 → warm re-index cache hits
5. US4 → help + progress + errors polish
6. Polish → README + quickstart green

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Then:
   - Developer A: US1 (`init`)
   - Developer B: US2 (discovery / size / config threading)
3. US3 after US2 plumbing; US4 last or interleaved with help strings

---

## Notes

- [P] tasks = different files, no dependencies on incomplete work
- Graph schema stays `6.0.0` — no `graph-json` contract changes
- Prefer Rich Progress over adding `tqdm`; prefer stdlib sqlite over `joblib` (`research.md`)
- Commit after each task or logical group
- Stop at checkpoints to validate stories independently
