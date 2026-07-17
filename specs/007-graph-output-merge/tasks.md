---
description: "Task list for Valid Graph Output, Compression, Versioning & Merge"
---

# Tasks: Valid Graph Output, Compression, Versioning & Merge

**Input**: Design documents from `/specs/007-graph-output-merge/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — constitution and plan require tests when graph persistence or CLI contracts change (atomic/gzip I/O, `--compress` / `--versioned`, `merge`). Schema remains `6.0.0` with additive merge metadata.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: `src/grapheinstein/`, `tests/` at repository root

## Grapheinstein Task Categories *(when applicable)*

- **Graph**: atomic validate-before-write, gzip load/save, versioned paths (`core/graph.py`)
- **Merge**: union + conflict detection + merge metadata (`core/merge.py`)
- **Index**: wire unified write helper with compress/versioned (`core/index.py`)
- **Config/CLI**: `--compress`, `--versioned`, `merge` (`cli.py`, `utils.py`)
- **Visualize/status**: gzip-aware load via shared loader (`core/visualize.py`, `cli.py`)
- **Contracts/tests**: CLI + graph I/O completeness tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Merge module stub and fixtures for union/conflict/gzip scenarios

- [x] T001 [P] Create `src/grapheinstein/core/merge.py` stub with module docstring and placeholder public API (`merge_artifacts`, `MergeConflictError`) per `plan.md`
- [x] T002 [P] Create `tests/fixtures/merge_graphs/` with minimal valid schema `6.0.0` JSON fixtures: `a.json` and `b.json` (disjoint node ids), `conflict_a.json` / `conflict_b.json` (same id, incompatible `type` or `metadata`), and brief notes in `tests/fixtures/merge_graphs/README.md` per `quickstart.md`

**Checkpoint**: Package still installable; merge stub and fixtures in place

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared I/O helpers (atomic write path shape, gzip-aware load, path/compression resolution, config keys) that all stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Implement `resolve_graph_output_path(path: Path, *, compress: bool) -> Path` in `src/grapheinstein/core/graph.py` (append `.gz` when compressing unless path already ends with `.gz`) per `contracts/cli.md`
- [x] T004 Implement gzip-aware read helper in `src/grapheinstein/core/graph.py` (open plain UTF-8 or gzip by `.gz` suffix and/or gzip magic) and route `load_artifact` through it so `.json.gz` loads validate like plain JSON
- [x] T005 Refactor `save_graph` in `src/grapheinstein/core/graph.py` to accept optional `compress: bool = False`, resolve path via T003, and write via same-directory temp file + `os.replace` (atomic) per `research.md` R1; keep public return as resolved `Path`
- [x] T006 Extend `AppConfig` and YAML coercion in `src/grapheinstein/utils.py` with `compress: bool = False` and `versioned: bool = False` per `contracts/cli.md`
- [x] T007 Route `status` / `visualize` loads in `src/grapheinstein/cli.py` and `src/grapheinstein/core/visualize.py` through the gzip-aware `load_artifact` (no behavior change for plain `.json`)

**Checkpoint**: Foundation ready — path resolution, gzip load, atomic save signature, and config keys available

---

## Phase 3: User Story 1 - Index Always Produces a Valid, Complete Graph Artifact (Priority: P1) 🎯 MVP

**Goal**: Every successful `index` publishes a validated schema `6.0.0` node-link artifact with full node `metadata`, edge attrs, and graph-level fields; failures leave no corrupt success file

**Independent Test**: Index a fixture project; assert envelope + every node has `metadata` + graph `project_root`/`generated_at`; simulate write failure / validate path leaves no truncated success artifact (quickstart Scenario A)

### Tests for User Story 1

- [x] T008 [P] [US1] Add unit tests for validate-before-write and atomic `save_graph` behavior in `tests/unit/test_graph_save_atomic.py`
- [x] T009 [P] [US1] Add contract tests asserting written artifacts include required completeness invariants (nodes `metadata`, links provenance, graph meta) in `tests/contract/test_graph_json_completeness.py`
- [x] T010 [P] [US1] Extend or add integration coverage in `tests/integration/test_cli_index.py` (or `tests/integration/test_cli_index_complete_write.py`) that successful index output passes completeness checks

### Implementation for User Story 1

- [x] T011 [US1] Call `validate_artifact` on the in-memory dict inside `save_graph` (or a dedicated write helper) in `src/grapheinstein/core/graph.py` **before** publishing bytes; on failure raise `GraphError` and do not replace the destination
- [x] T012 [US1] Audit `to_artifact_dict` in `src/grapheinstein/core/graph.py` so all collected node `metadata` and link attrs (`confidence`, `evidence`, `reason` when present) round-trip without silent drops per `contracts/graph-json.md`
- [x] T013 [US1] Ensure `src/grapheinstein/core/index.py` uses the hardened `save_graph` path for all successful writes (parents created; overwrite primary without prompt)

**Checkpoint**: US1 MVP — index always writes a valid, complete graph.json (or fails cleanly)

---

## Phase 4: User Story 4 - Merge Multiple Graphs into One (Priority: P1)

**Goal**: `grapheinstein merge` unions ≥2 valid graphs, preserves provenance/metadata, hard-fails on conflicts, writes merge metadata, accepts plain and gzip inputs

**Independent Test**: Merge `tests/fixtures/merge_graphs/a.json` + `b.json` → union with `graph.merged`; merge conflict fixtures → non-zero, no success output (quickstart Scenarios D–E)

### Tests for User Story 4

- [x] T014 [P] [US4] Add unit tests for union, dedupe, and hard-fail conflicts in `tests/unit/test_merge.py`
- [x] T015 [P] [US4] Add contract tests for merge CLI shape and merge graph metadata fields in `tests/contract/test_cli_merge.py`
- [x] T016 [P] [US4] Add integration tests for successful merge and conflict hard-fail (no success file) in `tests/integration/test_cli_merge_cmd.py`

### Implementation for User Story 4

- [x] T017 [US4] Implement `merge_artifacts` / conflict errors in `src/grapheinstein/core/merge.py`: same `schema_version` required; node union by `id` with deep-equal `type`+`metadata`; edge union with identity key + attr equality; diverge `project_root` → `project_roots`; set `merged`, `merged_from`, fresh `generated_at` per `data-model.md` and `research.md` R4
- [x] T018 [US4] Add `grapheinstein merge` command in `src/grapheinstein/cli.py` (≥2 inputs, required `--output`, optional `--compress` wired later or stubbed to config); load via gzip-aware `load_artifact`; write via `save_graph`; print merge summary on human-readable stream; errors on stderr
- [x] T019 [US4] Ensure merge failure paths in `src/grapheinstein/cli.py` / `src/grapheinstein/core/merge.py` never leave a success artifact at `--output` (validate + atomic write only after successful union)

**Checkpoint**: US1 + US4 — merge works offline on valid schema `6.0.0` graphs

---

## Phase 5: User Story 2 - Optionally Compress Graph Output (Priority: P2)

**Goal**: `--compress` writes gzip JSON (`.json.gz`); decompress equals uncompressed content; default remains plain `.json`

**Independent Test**: Index with `--compress` → `.json.gz` round-trips; without flag → plain JSON (quickstart Scenario B); merge with `--compress` and mixed inputs (Scenario F)

### Tests for User Story 2

- [x] T020 [P] [US2] Add unit tests for gzip save/load round-trip and path suffix rule in `tests/unit/test_graph_gzip.py`
- [x] T021 [P] [US2] Add integration tests for `index --compress` and `merge --compress` (including mixed plain+gzip inputs) in `tests/integration/test_cli_compress.py`

### Implementation for User Story 2

- [x] T022 [US2] Complete gzip write path in `src/grapheinstein/core/graph.py` `save_graph(..., compress=True)` (atomic temp still applies; write gzip bytes)
- [x] T023 [US2] Add `--compress` flag to `index` (and default-path alias) and to `merge` in `src/grapheinstein/cli.py`; plumb through `_run_index` / `index_project` and merge write; honor config `compress` when flag omitted
- [x] T024 [US2] Pass `compress` from CLI/config into `save_graph` from `src/grapheinstein/core/index.py` and merge command path

**Checkpoint**: US2 — optional gzip I/O works for index and merge

---

## Phase 6: User Story 3 - Versioned Graph Snapshots on Index (Priority: P2)

**Goal**: `--versioned` writes next `graph_vN.json[.gz]` beside primary latest without overwriting prior snapshots

**Independent Test**: Three versioned indexes produce `graph.json` + `graph_v1`…`v3`; earlier snapshots unchanged; with `--compress` uses `.json.gz` names (quickstart Scenario C)

### Tests for User Story 3

- [x] T025 [P] [US3] Add unit tests for next-version numbering (`graph_vN` scan, skip occupied N, compressed naming) in `tests/unit/test_graph_versioning.py`
- [x] T026 [P] [US3] Add integration tests for `--versioned` and `--versioned --compress` in `tests/integration/test_cli_versioned.py`

### Implementation for User Story 3

- [x] T027 [US3] Implement `next_versioned_graph_path(directory: Path, *, compress: bool) -> Path` in `src/grapheinstein/core/graph.py` scanning `graph_v(\d+)\.json(\.gz)?` per `research.md` R3
- [x] T028 [US3] Add `save_graph_with_options` (or extend write helper) in `src/grapheinstein/core/graph.py` / call site in `src/grapheinstein/core/index.py` to write primary latest **and**, when `versioned`, atomically write the next `graph_vN` with the same payload
- [x] T029 [US3] Add `--versioned` flag to `index` (and default-path alias) in `src/grapheinstein/cli.py`; plumb `versioned` through config/`index_project`; never overwrite existing `graph_vN`

**Checkpoint**: All user stories independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Help text, contract alignment, quickstart validation

- [x] T030 [P] Update CLI help / contract smoke expectations in `tests/contract/test_cli_help.py` for `--compress`, `--versioned`, and `merge`
- [x] T031 [P] Add config unit coverage for `compress` / `versioned` keys in `tests/unit/test_config.py`
- [x] T032 Run end-to-end validation from `specs/007-graph-output-merge/quickstart.md` and fix any gaps in `src/grapheinstein/` or tests
- [x] T033 Run full pytest suite (`tests/unit`, `tests/contract`, `tests/integration`) and fix regressions from I/O changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **User Story 1 (Phase 3)**: After Foundational — MVP
- **User Story 4 (Phase 4)**: After Foundational; ideally after US1 write hardening (uses `save_graph` / validate)
- **User Story 2 (Phase 5)**: After Foundational; builds on US1 write path; merge `--compress` also needs US4 CLI
- **User Story 3 (Phase 6)**: After Foundational; builds on US1 write path; compressed versioning needs US2
- **Polish (Phase 7)**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no story dependencies — **MVP**
- **US4 (P1)**: After Foundational; soft-depends on US1 validate/atomic write for safe outputs; gzip **read** available from Foundational
- **US2 (P2)**: Soft-depends on US1; merge compress soft-depends on US4
- **US3 (P2)**: Soft-depends on US1; `--versioned --compress` soft-depends on US2

### Within Each User Story

- Tests (listed) SHOULD be written to fail before implementation where practical
- Core helpers before CLI wiring
- Story complete before moving to next priority when staffing is serial

### Parallel Opportunities

- T001–T002 (Setup) in parallel
- T008–T010 (US1 tests) in parallel after Foundational
- T014–T016 (US4 tests) in parallel
- T020–T021 (US2 tests) in parallel
- T025–T026 (US3 tests) in parallel
- T030–T031 (Polish) in parallel
- After Foundational, US1 can proceed while US4 tests/fixtures are prepared; full US2/US3 wait on write path

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together:
Task: "Unit tests for atomic save in tests/unit/test_graph_save_atomic.py"
Task: "Contract tests for completeness in tests/contract/test_graph_json_completeness.py"
Task: "Integration completeness checks in tests/integration/test_cli_index.py"

# Then implement write hardening in core/graph.py → index.py
```

## Parallel Example: User Story 4

```bash
# Launch US4 tests together:
Task: "Unit tests in tests/unit/test_merge.py"
Task: "Contract tests in tests/contract/test_cli_merge.py"
Task: "Integration tests in tests/integration/test_cli_merge_cmd.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Index always emits valid complete graphs
5. Demo/ship MVP persistence hardening

### Incremental Delivery

1. Setup + Foundational → shared I/O ready
2. US1 → valid complete writes (MVP)
3. US4 → `merge` command
4. US2 → `--compress`
5. US3 → `--versioned`
6. Polish → quickstart + full suite

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Developer A: US1 write completeness
3. Developer B: US4 merge module + CLI (after atomic save lands)
4. Then US2 / US3 on the shared write helper

---

## Notes

- [P] tasks = different files, no dependencies on incomplete sibling tasks
- [Story] labels: US1 = valid output, US2 = compress, US3 = versioned, US4 = merge
- Schema stays `6.0.0`; do not bump for additive `merged` / `merged_from` / `project_roots`
- Commit after each task or logical group
- Stop at checkpoints to validate stories independently
