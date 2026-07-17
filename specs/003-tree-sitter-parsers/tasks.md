---
description: "Task list for Tree-sitter Code Parsers"
---

# Tasks: Tree-sitter Code Parsers

**Input**: Design documents from `/specs/003-tree-sitter-parsers/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — constitution and plan require tests when `graph.json` schema or CLI contracts change (bump to `3.0.0`, code-entity edges, `--languages`).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: `src/grapheinstein/`, `tests/` at repository root

## Grapheinstein Task Categories *(when applicable)*

- **Ingest/parsers**: Tree-sitter registry, queries, extract/resolve (`core/parsers/`)
- **Graph**: schema `3.0.0` node/edge model, provenance (`core/graph.py`)
- **Index**: wire code extract after inventory + references (`core/index.py`)
- **Config/CLI**: `languages` config + `--languages` (`utils.py`, `cli.py`)
- **Visualize/status**: enriched counts (`core/visualize.py`, `cli.py`)
- **Contracts/tests**: CLI + graph schema tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add Tree-sitter dependencies, parser package stubs, and multi-language fixtures

- [x] T001 Add `tree-sitter` and per-language grammar packages to `pyproject.toml` dependencies per `research.md` R1/R10 (python, javascript, typescript, java, go, rust, cpp, sql)
- [x] T002 [P] Create parser package stubs `src/grapheinstein/core/parsers/registry.py`, `extract.py`, `resolve.py`, and `queries/` (empty `__init__.py` / placeholder modules with docstrings) per plan.md structure; update `src/grapheinstein/core/parsers/__init__.py` exports
- [x] T003 [P] Create `tests/fixtures/code_project/` with Python defs/imports/calls (`src/app.py`, `src/main.py`), a second-language file (`src/util.go`), `broken/bad.py`, unsupported `notes.txt`, `.gitignore` excluding `ignored_dir/`, and documented expected line numbers in `tests/fixtures/code_project/README.md`
- [x] T004 [P] Add sample schema `2.0.0` graph fixture at `tests/fixtures/old_schema_v2_graph.json` for rejection tests

**Checkpoint**: Package still installable after dependency edit; fixtures and stubs in place

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema `3.0.0` graph primitives, language registry, and stats/load validation shared by all stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Bump NetworkX build/save/load in `src/grapheinstein/core/graph.py` to `schema_version` `3.0.0`; extend node allow-list with `function`|`class`|`method` and edge allow-list with `defines`|`imports`|`calls` per `contracts/graph-json.md` and `data-model.md`
- [x] T006 Implement helpers in `src/grapheinstein/core/graph.py` to add code-entity nodes (`{file}::{kind}::{name}::{start_line}` + required metadata) and `defines`/`imports`/`calls` edges with `provenance: extracted`
- [x] T007 Update strict load validation in `src/grapheinstein/core/graph.py` to accept only `3.0.0`, reject `2.0.0`/older with clear unsupported-format / re-index error, and validate code-entity metadata keys
- [x] T008 Extend `GraphStats` / `stats_from_artifact` in `src/grapheinstein/core/graph.py` to count function/class/method nodes and defines/imports/calls edges (retain file/dir/contains/references)
- [x] T009 Implement language registry in `src/grapheinstein/core/parsers/registry.py`: canonical ids, extension→language map, grammar `Language`/`Parser` loading, default all-eight set, validate language name lists
- [x] T010 Update `status` path in `src/grapheinstein/cli.py` (and any load helpers) to use v3 stats and fail clearly on schema `2.0.0` graphs
- [x] T011 Update existing suite expectations that hard-code `schema_version` `2.0.0` in `tests/contract/`, `tests/unit/`, and `tests/integration/` so baseline tests assert `3.0.0` inventory still works before code extract is wired

**Checkpoint**: Foundation ready — v3 graph round-trip, registry loads grammars offline, old schemas rejected

---

## Phase 3: User Story 1 - Index Code Structure into the Project Graph (Priority: P1) 🎯 MVP

**Goal**: `grapheinstein index` enriches the graph with function/class/method nodes (start lines) and `defines`/`imports`/`calls` edges (`extracted`) for supported languages

**Independent Test**: Index `tests/fixtures/code_project` → entities for `greet`/caller with correct lines; `defines` + resolvable `imports`/`calls`; Go entity present; ignored paths absent; all new edges `extracted` (quickstart Scenario A)

### Tests for User Story 1

- [x] T012 [P] [US1] Add unit tests for entity id/metadata and defines edge helpers in `tests/unit/test_graph_code_entities.py`
- [x] T013 [P] [US1] Add unit tests for Python extract (function/class/method + import/call facts) in `tests/unit/test_extract_python.py`
- [x] T014 [P] [US1] Add unit tests for import/call resolution (unique hit, ambiguous skip, external omit) in `tests/unit/test_resolve.py`
- [x] T015 [P] [US1] Add contract tests for schema `3.0.0` code nodes/links and provenance in `tests/contract/test_graph_json_v3.py`
- [x] T016 [P] [US1] Add integration test that `index` on `code_project` writes expected entities/edges in `tests/integration/test_cli_index_code.py`

### Implementation for User Story 1

- [x] T017 [P] [US1] Add Tree-sitter query definitions for Python in `src/grapheinstein/core/parsers/queries/python.scm` (or embedded equivalent) covering function/class/method/import/call captures
- [x] T018 [P] [US1] Add Tree-sitter query definitions for JavaScript and TypeScript (incl. TSX entry) in `src/grapheinstein/core/parsers/queries/javascript.scm` and `typescript.scm`
- [x] T019 [P] [US1] Add Tree-sitter query definitions for Java, Go, Rust, C++, and SQL in `src/grapheinstein/core/parsers/queries/` per research R4/R8
- [x] T020 [US1] Implement per-file parse + query extraction in `src/grapheinstein/core/parsers/extract.py` returning code entities and raw import/call facts (UTF-8 decode failure → skip with warning)
- [x] T021 [US1] Implement best-effort import/call resolution and `defines` emission in `src/grapheinstein/core/parsers/resolve.py` per research R5
- [x] T022 [US1] Expose orchestration entrypoint in `src/grapheinstein/core/parsers/__init__.py` to merge entities/edges into an existing DiGraph for a language set
- [x] T023 [US1] Wire code-structure pass into `src/grapheinstein/core/index.py` after inventory + references; record enabled languages on `graph.graph["languages"]`; keep ignore rules
- [x] T024 [US1] Update index success summary in `src/grapheinstein/cli.py` to report code-entity and defines/imports/calls counts
- [x] T025 [US1] Update visualize summary in `src/grapheinstein/core/visualize.py` (and DOT labels) to include new node/edge kinds without crashing

**Checkpoint**: US1 MVP complete — default index produces schema `3.0.0` digraph with code structure

---

## Phase 4: User Story 2 - Configure Which Languages Are Parsed (Priority: P1)

**Goal**: Users can restrict structure extraction via config `languages` and/or `--languages`; unknown names fail closed; default remains all eight

**Independent Test**: `--languages python` extracts only Python entities while Go file node remains; unknown language non-zero and no success write; config list works and CLI overrides config (quickstart Scenarios B, C, G)

### Tests for User Story 2

- [x] T026 [P] [US2] Add unit tests for language list parsing/validation in `tests/unit/test_languages_config.py`
- [x] T027 [P] [US2] Add integration tests for `--languages` subset, config `languages`, CLI override precedence, and invalid language failure in `tests/integration/test_cli_languages.py`

### Implementation for User Story 2

- [x] T028 [US2] Extend `AppConfig` / `load_config` in `src/grapheinstein/utils.py` to accept optional `languages` list (validate via registry; default all eight when unset)
- [x] T029 [US2] Add `--languages` option to `index` (and default-path alias) in `src/grapheinstein/cli.py`; add `--languages` to `_OPTS_WITH_VALUE`; precedence CLI > config > default
- [x] T030 [US2] Pass resolved language set into `index_project` in `src/grapheinstein/core/index.py` / `cli.py` so disabled languages skip structure extract but keep file nodes
- [x] T031 [US2] On invalid language ids, exit non-zero with clear error listing invalid and valid names and do not write a success graph (`src/grapheinstein/cli.py`)

**Checkpoint**: US1 + US2 — configurable language scope works with fail-closed validation

---

## Phase 5: User Story 3 - Surviving Partial Parse Failures (Priority: P2)

**Goal**: Per-file extract failures and unsupported extensions do not abort index; users see skip/failure signals in logs or summary

**Independent Test**: Index fixture with `broken/bad.py` + `notes.txt` → exit 0; good entities present; warning/summary indicates skips; no fabricated entities for bad file (quickstart Scenario D)

### Tests for User Story 3

- [x] T032 [P] [US3] Add unit tests that extract/orchestration swallows per-file errors and records skip counts in `tests/unit/test_extract_errors.py`
- [x] T033 [P] [US3] Add integration test for mixed good/broken/unsupported files succeeding with warnings in `tests/integration/test_cli_index_partial.py`

### Implementation for User Story 3

- [x] T034 [US3] Harden per-file try/except and skip accounting in `src/grapheinstein/core/parsers/extract.py` / orchestration so exceptions never abort the whole index
- [x] T035 [US3] Surface parse-skip counts via logging and/or index summary fields in `src/grapheinstein/core/index.py` and `src/grapheinstein/cli.py` (human-visible without opening the graph)
- [x] T036 [US3] Ensure unsupported extensions and disabled languages are silent no-ops for structure (file nodes only) in `src/grapheinstein/core/parsers/registry.py` / `index.py`

**Checkpoint**: All user stories independently functional; messy trees index successfully

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Alignment with quickstart, loader rejection, and suite hygiene

- [x] T037 [P] Add/extend contract or integration assertion that visualize/status reject `tests/fixtures/old_schema_v2_graph.json` in `tests/integration/test_cli_visualize.py` or `tests/contract/test_graph_json_v3.py`
- [x] T038 [P] Add lightweight extract smoke coverage for non-Python fixture languages present in `code_project` (at least Go) in `tests/unit/test_extract_go.py` or extend `tests/integration/test_cli_index_code.py`
- [x] T039 Run through `specs/003-tree-sitter-parsers/quickstart.md` scenarios A–G locally and fix any gaps in CLI messaging or counts
- [x] T040 [P] Confirm DOT export still includes new node ids/edge types after visualize updates in `tests/unit/test_visualize_dot.py` (extend existing tests)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP
- **User Story 2 (Phase 4)**: Depends on Foundational; practically follows US1 so index already emits code entities to filter
- **User Story 3 (Phase 5)**: Depends on Foundational; practically follows US1 extract path for skip accounting
- **Polish (Phase 6)**: Depends on desired stories (ideally all three)

### User Story Dependencies

- **User Story 1 (P1)**: After Foundational — no dependency on US2/US3 (uses default all-eight languages)
- **User Story 2 (P1)**: After Foundational — independently testable via language filtering; integrates with US1 index path
- **User Story 3 (P2)**: After Foundational — independently testable via error fixtures; hardens US1 extract path

### Within Each User Story

- Tests (if included) SHOULD be written and FAIL before implementation
- Queries/registry before extract; extract before resolve; resolve before index wiring
- Story complete before moving to next priority when working solo

### Parallel Opportunities

- Phase 1: T002, T003, T004 in parallel after/with T001
- Phase 2: T008/T009 can proceed in parallel once T005–T007 direction is clear; T010–T011 after T005–T008
- US1: T012–T016 tests in parallel; T017–T019 query files in parallel; then T020→T021→T022→T023→T024/T025
- US2: T026–T027 in parallel; then T028→T029→T030→T031
- US3: T032–T033 in parallel; then T034→T035→T036
- Polish: T037, T038, T040 in parallel; T039 after fixes

---

## Parallel Example: User Story 1

```bash
# Tests in parallel:
Task: "Unit tests for code entities in tests/unit/test_graph_code_entities.py"
Task: "Unit tests for Python extract in tests/unit/test_extract_python.py"
Task: "Unit tests for resolve in tests/unit/test_resolve.py"
Task: "Contract tests in tests/contract/test_graph_json_v3.py"
Task: "Integration index code in tests/integration/test_cli_index_code.py"

# Query files in parallel:
Task: "Python queries in src/grapheinstein/core/parsers/queries/python.scm"
Task: "JS/TS queries in .../javascript.scm and typescript.scm"
Task: "Java/Go/Rust/C++/SQL queries in src/grapheinstein/core/parsers/queries/"
```

---

## Parallel Example: User Story 2

```bash
Task: "Unit tests in tests/unit/test_languages_config.py"
Task: "Integration tests in tests/integration/test_cli_languages.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Index `code_project`, inspect schema `3.0.0` entities/edges
5. Demo index → visualize loop with code counts

### Incremental Delivery

1. Setup + Foundational → v3 foundation ready
2. US1 → code structure graph (MVP)
3. US2 → configurable languages
4. US3 → resilient partial failures
5. Polish → quickstart green

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. After Foundational:
   - Dev A: US1 extract/resolve/index wiring
   - Dev B: US2 config/CLI (can stub filter until US1 lands)
   - Dev C: US3 error paths + fixtures
3. Integrate on shared `index.py` / `cli.py` carefully

---

## Notes

- [P] tasks = different files, no dependencies on incomplete work
- [Story] label maps task to US1/US2/US3 for traceability
- Prefer omitting ambiguous import/call edges over wrong links (research R5)
- SQL may emit zero entities for DDL-only files — not a failure (research R8)
- Commit after each task or logical group
- Avoid: silent schema 2→3 migration, runtime grammar downloads, inferred provenance on code edges
