---
description: "Task list for CLI Project Index Skeleton"
---

# Tasks: CLI Project Index Skeleton

**Input**: Design documents from `/specs/001-cli-project-index/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — plan Constitution Check and contracts require tests when CLI/`graph.json` schema are introduced.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: `src/grapheinstein/`, `tests/` at repository root

## Grapheinstein Task Categories *(when applicable)*

- **Ingest/parsers**: discovery, ignore rules (`core/index.py`; parsers stub only)
- **Graph**: node/edge model, `extracted` provenance, `graph.json` (`core/graph.py`)
- **Config/cache**: YAML config (`utils.py` / config helpers)
- **Contracts/tests**: CLI + graph schema tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Installable package skeleton and tooling

- [x] T001 Create package directories `src/grapheinstein/`, `src/grapheinstein/core/`, `src/grapheinstein/core/parsers/`, `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/fixtures/` per plan.md
- [x] T002 Create `pyproject.toml` with Python ≥3.11, package `grapheinstein` (src layout), console script `grapheinstein = grapheinstein.cli:app`, and dependencies typer, networkx, pathspec, rich, loguru, pyyaml; add optional `[project.optional-dependencies] dev` with pytest
- [x] T003 [P] Add package init modules `src/grapheinstein/__init__.py`, `src/grapheinstein/core/__init__.py`, and stub `src/grapheinstein/core/parsers/__init__.py`
- [x] T004 [P] Add `src/grapheinstein/__main__.py` that invokes the Typer app so `python -m grapheinstein` works
- [x] T005 [P] Create sample fixture project at `tests/fixtures/sample_project/` with `.gitignore` excluding `ignored_dir/`, plus `README.md`, `src/main.py`, and `ignored_dir/secret.txt`

**Checkpoint**: Package layout and fixture exist; editable install can be configured next

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared utilities, config, logging, and graph primitives required by all user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Implement path helpers and Rich/Loguru console setup in `src/grapheinstein/utils.py` (stderr human output; configurable log level)
- [x] T007 Implement config loading with precedence CLI flags > `--config` > `~/.grapheinstein/config.yaml` > defaults (`output`, `log_level`) in `src/grapheinstein/utils.py` (or `src/grapheinstein/core/config.py` if split; keep importable from CLI)
- [x] T008 Implement NetworkX graph build/load/save for schema_version `1.0.0` node-link envelope (nodes with `id`/`kind`/`path`; links with `type`/`provenance`) in `src/grapheinstein/core/graph.py` per `contracts/graph-json.md` and `data-model.md`
- [x] T009 Implement ignore-aware discovery and inventory orchestration (walk project, pathspec `.gitignore`, create file/directory nodes and `contains`/`extracted` edges, write artifact) in `src/grapheinstein/core/index.py`
- [x] T010 Create minimal Typer app shell with global `--config` / `--output` options wired to config helpers in `src/grapheinstein/cli.py` (subcommands can be stubs until story phases)

**Checkpoint**: Foundation ready — `index` core library callable from Python; CLI shell imports cleanly

---

## Phase 3: User Story 1 - Install and Index a Project (Priority: P1) 🎯 MVP

**Goal**: Installable CLI indexes a project path into portable `graph.json` with file/directory nodes, respecting `.gitignore`; default invocation equals `index`

**Independent Test**: `pip install -e .` then `grapheinstein tests/fixtures/sample_project -o /tmp/g.json` writes a valid graph; ignored paths absent; included files present (quickstart Scenarios A/B/E)

### Tests for User Story 1

- [x] T011 [P] [US1] Add unit tests for `.gitignore` exclusion and parent directory node creation in `tests/unit/test_index_discovery.py`
- [x] T012 [P] [US1] Add contract tests asserting `schema_version`, required node fields, and `contains`/`extracted` links per `contracts/graph-json.md` in `tests/contract/test_graph_json.py`
- [x] T013 [P] [US1] Add integration tests for default path invocation and `index` subcommand via CliRunner against `tests/fixtures/sample_project` in `tests/integration/test_cli_index.py`

### Implementation for User Story 1

- [x] T014 [US1] Wire `index` subcommand in `src/grapheinstein/cli.py` to call `core.index` and print Rich success summary (counts + output path) on stderr
- [x] T015 [US1] Wire default callback so `grapheinstein PROJECT_PATH` performs the same indexing as `index` per `contracts/cli.md` in `src/grapheinstein/cli.py`
- [x] T016 [US1] Ensure output parent directories are created and clear non-zero errors for bad project path / unwritable output in `src/grapheinstein/cli.py` and `src/grapheinstein/core/index.py`
- [x] T017 [US1] Verify editable install entry points: console script and `python -m grapheinstein` both run index successfully (touch `pyproject.toml` / `__main__.py` only if fixes needed)

**Checkpoint**: US1 MVP complete — working CLI produces `graph.json` inventory

---

## Phase 4: User Story 2 - Check Index Status (Priority: P2)

**Goal**: `status` reports file/directory/total node counts from an existing graph, or clearly reports missing index (exit 2)

**Independent Test**: After indexing, `grapheinstein status --output ...` matches JSON counts; missing file exits 2 (quickstart Scenarios C/D)

### Tests for User Story 2

- [x] T018 [P] [US2] Add contract/integration tests for status success and exit code 2 when graph missing in `tests/integration/test_cli_status.py`

### Implementation for User Story 2

- [x] T019 [US2] Implement graph stats helper (file count, directory count, total nodes) in `src/grapheinstein/core/graph.py`
- [x] T020 [US2] Implement `status` subcommand with Rich summary and exit codes 0/1/2 per `contracts/cli.md` in `src/grapheinstein/cli.py`

**Checkpoint**: US1 + US2 work — index then status without re-scanning the tree

---

## Phase 5: User Story 3 - Configure Defaults Locally (Priority: P3)

**Goal**: User config at `~/.grapheinstein/config.yaml` or `--config` supplies defaults; missing default config is fine; invalid config fails clearly

**Independent Test**: Index with no config succeeds; `--config` sets output path; bad YAML exits 1 (quickstart Scenarios E/F)

### Tests for User Story 3

- [x] T021 [P] [US3] Add unit tests for config precedence and invalid YAML errors in `tests/unit/test_config.py`
- [x] T022 [P] [US3] Add integration test that `--config` output path is honored in `tests/integration/test_cli_config.py`

### Implementation for User Story 3

- [x] T023 [US3] Finish config merge edge cases (unknown keys warn; malformed explicit config fails) in `src/grapheinstein/utils.py` (or config module from T007)
- [x] T024 [US3] Ensure CLI applies resolved `output` and `log_level` from config when flags omitted in `src/grapheinstein/cli.py`

**Checkpoint**: All three user stories independently demonstrable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Docs and validation pass for handoff

- [x] T025 [P] Add minimal root `README.md` with install and `grapheinstein` / `index` / `status` usage pointing to `specs/001-cli-project-index/quickstart.md`
- [x] T026 [P] Add `tests/contract/test_cli_help.py` asserting `--help` lists `index` and `status`
- [x] T027 Run full `pytest` and manually walk quickstart Scenarios A–F; fix any contract mismatches in `src/grapheinstein/` or tests
- [x] T028 Confirm offline-only behavior (no network imports/calls in index/status paths) and note in `README.md` if needed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP
- **User Story 2 (Phase 4)**: Depends on Foundational; practically needs a graph from US1 library/CLI to demo, but stats helper can be tested with a hand-written fixture JSON
- **User Story 3 (Phase 5)**: Depends on Foundational; integrates with US1 CLI flags
- **Polish (Phase 6)**: Depends on desired stories being complete (at least US1 for MVP)

### User Story Dependencies

- **US1 (P1)**: No dependency on US2/US3
- **US2 (P2)**: Reads artifact format from US1; can use fixture graph JSON without full CLI if needed
- **US3 (P3)**: Extends config used by US1/US2; should not break defaults from US1

### Within Each User Story

- Tests marked [P] can be written first and should fail until implementation lands
- Core library behavior before CLI wiring where noted
- Story complete before moving to next priority for MVP discipline

### Parallel Opportunities

- T003, T004, T005 after T001
- T011, T012, T013 in parallel (US1 tests)
- T018 alone or alongside T019 once graph load exists
- T021, T022 in parallel (US3 tests)
- T025, T026 in parallel during polish

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together:
Task: "Unit tests for discovery in tests/unit/test_index_discovery.py"
Task: "Contract tests in tests/contract/test_graph_json.py"
Task: "Integration CLI index tests in tests/integration/test_cli_index.py"

# After foundation, implementation sequence:
Task: "Wire index subcommand in src/grapheinstein/cli.py"
Task: "Wire default callback in src/grapheinstein/cli.py"
```

---

## Parallel Example: User Story 2

```bash
Task: "Status integration tests in tests/integration/test_cli_status.py"
Task: "Stats helper in src/grapheinstein/core/graph.py"
# Then:
Task: "status subcommand in src/grapheinstein/cli.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: quickstart Scenarios A, B, E
5. Demo install + index → `graph.json`

### Incremental Delivery

1. Setup + Foundational → library ready
2. US1 → MVP CLI index
3. US2 → status
4. US3 → config defaults
5. Polish → README + full pytest / quickstart

### Parallel Team Strategy

1. Together: Setup + Foundational
2. Then: Dev A finishes US1 CLI; Dev B can draft US2 tests + stats against fixture JSON; Dev C drafts US3 config tests
3. Integrate on shared `cli.py` carefully (avoid file conflicts)

---

## Notes

- [P] = different files, no incomplete dependencies
- [USn] maps to spec user stories for traceability
- Do not implement explain/path/ask, media parsers, or MCP in this feature
- Commit after each task or logical group when asked
- Format validation: all tasks use `- [ ] Tnnn ...` with file paths; story labels only on US phases
