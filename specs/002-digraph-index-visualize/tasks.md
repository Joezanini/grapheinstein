---
description: "Task list for Directed File Graph Index & Visualize"
---

# Tasks: Directed File Graph Index & Visualize

**Input**: Design documents from `/specs/002-digraph-index-visualize/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — constitution and plan require tests when `graph.json` schema or CLI contracts change (bump to `2.0.0`, new `visualize`).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: `src/grapheinstein/`, `tests/` at repository root

## Grapheinstein Task Categories *(when applicable)*

- **Ingest**: symlink-safe discovery, `.gitignore` (`core/index.py`)
- **Graph**: v2 node/edge model, provenance, `graph.json` (`core/graph.py`)
- **Extract**: whole-token basename `references` (`core/references.py`)
- **Visualize**: console summary + DOT (`core/visualize.py`, `cli.py`)
- **Contracts/tests**: CLI + graph schema tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Extend fixtures and module stubs for schema v2 work on the existing package

- [x] T001 [P] Extend `tests/fixtures/sample_project/README.md` with a whole-token mention of `main.py` for references acceptance
- [x] T002 [P] Add empty module stubs `src/grapheinstein/core/references.py` and `src/grapheinstein/core/visualize.py` (docstrings only) per plan.md structure
- [x] T003 [P] Add fixture helper or sample v1 graph JSON at `tests/fixtures/old_schema_v1_graph.json` using `kind`/`directory` / `schema_version` `1.0.0` for rejection tests

**Checkpoint**: Fixtures and stubs ready; existing package remains installable

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema `2.0.0` graph primitives, validation, and symlink-safe discovery shared by all stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Migrate NetworkX build/save/load in `src/grapheinstein/core/graph.py` to schema_version `2.0.0` with nodes `{id, type: file|dir, metadata}` and links `{source, target, type, provenance}` per `contracts/graph-json.md` and `data-model.md`
- [x] T005 Implement strict load validation in `src/grapheinstein/core/graph.py` that rejects missing fields, non-`2.0.0` schema, and old `kind`/`directory` shapes with a clear unsupported-format / re-index error (no silent mapping)
- [x] T006 Update `GraphStats` / `stats_from_artifact` in `src/grapheinstein/core/graph.py` to count `type == file|dir` and expose contains/references edge counts for summarize/status
- [x] T007 Update discovery in `src/grapheinstein/core/index.py` to treat symlinks as `file` nodes without following (`is_symlink()` before `is_dir()`), set optional `metadata.symlink`, and keep `.gitignore` / `.git` behavior
- [x] T008 Update inventory builders in `src/grapheinstein/core/index.py` / `src/grapheinstein/core/graph.py` to emit `type` `file`|`dir` and `contains`/`extracted` edges for the directory tree (overwrite output without prompt via existing `save_graph`)
- [x] T009 Update `status` path in `src/grapheinstein/cli.py` to use v2 stats fields and fail clearly on unsupported old graphs

**Checkpoint**: Foundation ready — v2 graph round-trip and symlink-safe tree work from Python; old graphs rejected

---

## Phase 3: User Story 1 - Index a Project into a Directed Graph (Priority: P1) 🎯 MVP

**Goal**: `grapheinstein index <path> --output graph.json` writes a v2 directed graph with file/dir nodes, `contains` edges, and whole-token basename `references` edges

**Independent Test**: Index `tests/fixtures/sample_project` → v2 JSON has `contains` tree, a `references` edge README→`src/main.py`, ignored paths absent; symlink fixture not followed (quickstart Scenarios A, E, F)

### Tests for User Story 1

- [x] T010 [P] [US1] Add unit tests for whole-token matching, ambiguous basename skip, self-edge skip, and substring-negative cases in `tests/unit/test_references.py`
- [x] T011 [P] [US1] Add unit tests for symlink-as-file / no-follow discovery in `tests/unit/test_index_symlinks.py`
- [x] T012 [P] [US1] Add contract tests for schema `2.0.0` node/link shape and `contains`/`references` provenance in `tests/contract/test_graph_json_v2.py`
- [x] T013 [P] [US1] Add integration tests for `index` / default-path invocation writing v2 graph with references in `tests/integration/test_cli_index_v2.py`

### Implementation for User Story 1

- [x] T014 [US1] Implement whole-token basename mention extraction (unique basename map, longest-first, UTF-8 text skip on decode failure) in `src/grapheinstein/core/references.py` per research R3
- [x] T015 [US1] Wire references into index orchestration so `index_project` / `build_inventory_graph` adds `references`/`extracted` edges in `src/grapheinstein/core/index.py`
- [x] T016 [US1] Ensure `index` CLI summary in `src/grapheinstein/cli.py` reports v2 counts (files/dirs/total; optionally edge counts) and overwrites `--output` without prompting
- [x] T017 [US1] Update or replace obsolete v1 expectations in `tests/contract/test_graph_json.py`, `tests/unit/test_index_discovery.py`, and `tests/integration/test_cli_index.py` so the suite asserts schema `2.0.0` / `type`/`dir`

**Checkpoint**: US1 MVP complete — working `index` produces v2 digraph with contains + references

---

## Phase 4: User Story 2 - Inspect a Graph from the Console (Priority: P1)

**Goal**: `grapheinstein visualize --input graph.json` prints a console summary of node/edge counts (and a brief sample); clear errors for missing/unsupported graphs

**Independent Test**: After indexing, visualize summary counts match JSON; old v1 fixture fails clearly; missing input non-zero (quickstart Scenarios B, D)

### Tests for User Story 2

- [x] T018 [P] [US2] Add unit tests for summary stats derivation from a v2 artifact dict in `tests/unit/test_visualize_summary.py`
- [x] T019 [P] [US2] Add integration tests for visualize success, missing input, and old-schema rejection in `tests/integration/test_cli_visualize.py`

### Implementation for User Story 2

- [x] T020 [US2] Implement load + Rich console summary (file/dir/total nodes, contains/references counts, brief sample) in `src/grapheinstein/core/visualize.py`
- [x] T021 [US2] Add `visualize` subcommand with required `--input`/`-i` in `src/grapheinstein/cli.py` and register `visualize` in `_KNOWN_COMMANDS` so default-path rewrite does not capture it
- [x] T022 [US2] Map `GraphError` / unsupported-format / missing file to non-zero exits with clear messages in `src/grapheinstein/cli.py`

**Checkpoint**: US1 + US2 work — index → visualize summary loop complete

---

## Phase 5: User Story 3 - Export a DOT View of the Graph (Priority: P2)

**Goal**: `visualize --dot PATH` writes a DOT file representing all nodes/edges while still printing the console summary; overwrite without prompt

**Independent Test**: `visualize --input ... --dot /tmp/g.dot` writes DOT covering all nodes/edges and still prints summary (quickstart Scenario C)

### Tests for User Story 3

- [x] T023 [P] [US3] Add unit tests for hand-written DOT emitter covering nodes and typed edges in `tests/unit/test_visualize_dot.py`
- [x] T024 [P] [US3] Add integration test for `--dot` overwrite + summary still printed in `tests/integration/test_cli_visualize.py` (extend file from US2)

### Implementation for User Story 3

- [x] T025 [US3] Implement hand-written DOT export (no pydot) writing UTF-8 to a path with overwrite in `src/grapheinstein/core/visualize.py`
- [x] T026 [US3] Wire optional `--dot` on `visualize` in `src/grapheinstein/cli.py` so DOT is written and summary still prints on success; clear error if DOT path unwritable

**Checkpoint**: All user stories independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Align docs and validate end-to-end quickstart

- [x] T027 [P] Update root `README.md` (if present) with `index` v2 node shape and `visualize [--dot]` usage notes
- [x] T028 Run full pytest suite and fix any remaining v1→v2 fallout across `tests/`
- [x] T029 Manually execute quickstart Scenarios A–G in `specs/002-digraph-index-visualize/quickstart.md` and record/fix gaps

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP
- **User Story 2 (Phase 4)**: Depends on Foundational; practically needs a v2 graph from US1 (or a hand-built fixture) for integration tests
- **User Story 3 (Phase 5)**: Depends on US2 visualize command existing (`T021`); extends same module/CLI
- **Polish (Phase 6)**: Depends on desired stories complete

### User Story Dependencies

- **User Story 1 (P1)**: After Foundational — no dependency on US2/US3
- **User Story 2 (P1)**: After Foundational — independently testable with a static v2 fixture if index not finished; CLI integrate after T004–T006
- **User Story 3 (P2)**: After US2 visualize command scaffold (`T021`); DOT logic can be unit-tested in parallel once `visualize.py` exists

### Parallel Opportunities

- T001–T003 in parallel
- T010–T013 in parallel (after Foundational, before/during US1 impl)
- T018–T019 in parallel once summary API shape is known
- T023 can proceed in parallel with T025 once emitter API is sketched
- US2 library work (`T020`) can start after T005–T006 even before US1 references land, using a hand-authored v2 JSON fixture

---

## Parallel Example: User Story 1

```bash
# After Foundational, launch US1 tests together:
Task: "Unit tests in tests/unit/test_references.py"
Task: "Unit tests in tests/unit/test_index_symlinks.py"
Task: "Contract tests in tests/contract/test_graph_json_v2.py"
Task: "Integration tests in tests/integration/test_cli_index_v2.py"

# Then implement:
Task: "references.py extraction"
Task: "Wire into index.py"
Task: "CLI summary + migrate old tests"
```

---

## Parallel Example: User Story 2

```bash
Task: "tests/unit/test_visualize_summary.py"
Task: "tests/integration/test_cli_visualize.py"
Task: "core/visualize.py summary"
Task: "cli.py visualize subcommand"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (schema v2 + symlink-safe discovery)
3. Complete Phase 3: User Story 1 (references + index)
4. **STOP and VALIDATE**: Index fixture → inspect `graph.json` for contains + references
5. Demo/install path ready before visualize

### Incremental Delivery

1. Setup + Foundational → v2 graph library ready
2. US1 → Index digraph MVP
3. US2 → Visualize console summary
4. US3 → DOT export
5. Polish → quickstart A–G green

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Dev A: US1 references + index tests
3. Dev B: US2 visualize summary (with static v2 fixture)
4. After T021: Dev C or A/B: US3 DOT export

---

## Notes

- [P] tasks = different files, no incomplete-task dependencies
- [Story] label maps task to US1/US2/US3 for traceability
- Do not keep dual-read for schema `1.0.0` — reject and re-index
- Commit after each task or logical group
- Stop at checkpoints to validate independently
- Suggested MVP scope: **Phases 1–3 (US1 only)**
