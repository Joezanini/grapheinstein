---
description: "Task list for Serve & Agent API"
---

# Tasks: Serve & Agent API

**Input**: Design documents from `/specs/012-serve-api/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — constitution and plan require tests when CLI contracts change (`serve` subcommand) and for public Python/HTTP agent surfaces.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: `src/grapheinstein/`, `tests/` at repository root

## Grapheinstein Task Categories *(when applicable)*

- **Integration hooks**: Public `grapheinstein.api` for slash-command / agent hosts; optional HTTP serve
- **Query / index**: Reuse `core/index.py` + `core/query.py` via API (no second implementation)
- **CLI**: `serve` command, help/epilog (`cli.py`)
- **Contracts/tests**: Python API, HTTP JSON, CLI serve; graph schema stays `6.0.0`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package stubs, optional `[serve]` extras, and package layout for lazy FastAPI imports

- [x] T001 [P] Create `src/grapheinstein/api.py` stub with module docstring and placeholder `index` / `query` signatures plus `IndexResult` dataclass skeleton per `plan.md` / `contracts/python-api.md`
- [x] T002 [P] Create `src/grapheinstein/serve/__init__.py` and `src/grapheinstein/serve/app.py` stubs with docstrings; `ensure_serve_deps()` placeholder; no hard FastAPI import at package import time
- [x] T003 Add optional dependency group `[serve]` (`fastapi`, `uvicorn`) in `pyproject.toml` without adding them to core `dependencies`

**Checkpoint**: Core install still works without FastAPI; stubs importable; `[serve]` declared

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared config-loading helpers and error mapping that API + serve both use

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement `IndexResult` (`output_path`, `stats`, `artifact`) and shared config-resolution helpers in `src/grapheinstein/api.py` (call existing `load_config` / path resolution; no Typer imports)
- [x] T005 [P] Implement `ensure_serve_deps()` in `src/grapheinstein/serve/__init__.py` mirroring `ensure_media_deps` pattern (clear `pip install 'grapheinstein[serve]'` message; raise typed error e.g. `ServeExtrasError`)
- [x] T006 [P] Add unit tests for `ensure_serve_deps` missing-import behavior (mock ImportError) in `tests/unit/test_api_wrappers.py` or `tests/unit/test_serve_deps.py`

**Checkpoint**: Foundation ready — API types/helpers exist; serve deps check fails closed without loading FastAPI when missing

---

## Phase 3: User Story 1 - Call Indexing from Another Agent via Python (Priority: P1) 🎯 MVP

**Goal**: Agents call `grapheinstein.api.index(folder)` and get/persist a portable graph with CLI index semantics

**Independent Test**: From a Python script, index `tests/fixtures/config_cache/` via API; assert `graph.json` written and stats present; bad path raises clear error (quickstart Scenario A index half)

### Tests for User Story 1

- [x] T007 [P] [US1] Add contract tests for public `index` signature / `IndexResult` fields / hard-failure on missing path in `tests/contract/test_python_api.py`
- [x] T008 [P] [US1] Add unit/integration coverage that API index writes a valid schema `6.0.0` graph for a fixture in `tests/unit/test_api_wrappers.py` or `tests/integration/test_api_parity.py`

### Implementation for User Story 1

- [x] T009 [US1] Implement `index()` in `src/grapheinstein/api.py`: resolve config/flags, call `index_project`, return `IndexResult`; optional `include_artifact`; never return empty success on hard failure per `contracts/python-api.md`
- [x] T010 [US1] Refactor CLI `index` path in `src/grapheinstein/cli.py` to call `grapheinstein.api.index` (or shared helper) so CLI and API share one implementation
- [x] T011 [US1] Re-export or document import path in `src/grapheinstein/__init__.py` only if kept thin (prefer `from grapheinstein.api import index` as canonical)

**Checkpoint**: US1 MVP — agents can index a folder in-process without CLI subprocess

---

## Phase 4: User Story 2 - Ask Questions via Python Without Leaving the Agent Process (Priority: P1)

**Goal**: Agents call `grapheinstein.api.query(question, input=graph)` and receive query-answer schema `1.0.0` with CLI parity

**Independent Test**: Query a known fixture graph via API with `no_answer=True`; assert envelope shape; compare `hit_ids` to CLI query on same graph (quickstart Scenario B)

### Tests for User Story 2

- [x] T012 [P] [US2] Extend `tests/contract/test_python_api.py` for `query` success envelope (`schema_version` `1.0.0`) and error cases (`NoEvidenceError` / missing graph)
- [x] T013 [P] [US2] Add integration parity test CLI vs API `hit_ids` in `tests/integration/test_api_parity.py`

### Implementation for User Story 2

- [x] T014 [US2] Implement `query()` in `src/grapheinstein/api.py`: load config overrides, call `run_query`, return `query_answer_to_dict` envelope; map empty question / missing graph to clear exceptions per `contracts/python-api.md`
- [x] T015 [US2] Refactor CLI `query` path in `src/grapheinstein/cli.py` to call `grapheinstein.api.query` (or shared helper) for structural parity

**Checkpoint**: US1 + US2 — full agent index→query loop via Python API

---

## Phase 5: User Story 3 - Optional Local HTTP Serve for Index and Query (Priority: P2)

**Goal**: `grapheinstein serve --port 8000` (default) exposes `POST /index` and `POST /query` on loopback, backed by `api.index` / `api.query`

**Independent Test**: With `[serve]` installed, start serve or use TestClient; POST index + query; missing extras fails with install hint; port-in-use fails clearly (quickstart Scenarios C–E)

### Tests for User Story 3

- [x] T016 [P] [US3] Add CLI contract tests for `serve` help (`--port` default 8000, `--host`), `_KNOWN_COMMANDS` includes `serve`, missing-extras exit in `tests/contract/test_cli_serve.py`; extend `tests/contract/test_cli_help.py` to list `serve`
- [x] T017 [P] [US3] Add HTTP contract tests with FastAPI `TestClient` (skip if extras missing) for `/index` and `/query` success + validation errors in `tests/contract/test_http_api.py`
- [x] T018 [P] [US3] Add integration round-trip test (TestClient or free port) in `tests/integration/test_serve_roundtrip.py`

### Implementation for User Story 3

- [x] T019 [US3] Implement FastAPI app in `src/grapheinstein/serve/app.py`: `POST /index` and `POST /query` per `contracts/http-api.md` (locked response style: query envelope + `"ok": true` at top level); process-wide `threading.Lock`; map exceptions to error objects
- [x] T020 [US3] Implement `create_app()` / `run_server(host, port)` in `src/grapheinstein/serve/__init__.py` using lazy FastAPI/Uvicorn imports and `uvicorn.run(app, host=..., port=...)` after `ensure_serve_deps()`
- [x] T021 [US3] Add `grapheinstein serve` command in `src/grapheinstein/cli.py`: `--port` default `8000`, `--host` default `127.0.0.1`; register in `_KNOWN_COMMANDS`; bind failure → clear error; help points to `docs/agent-integration.md`
- [x] T022 [US3] Ensure importing `grapheinstein.api` or running core CLI never imports FastAPI; only `serve` command path triggers deps check

**Checkpoint**: US1–US3 — optional HTTP surface works; core remains lean

---

## Phase 6: User Story 4 - Documented Agent Integration Playbook (Priority: P2)

**Goal**: Ship `docs/agent-integration.md` with copy-paste Python + HTTP examples, parity notes, and `[serve]` install; link from README and serve help

**Independent Test**: Grep/docs checks from quickstart Scenario F; follow examples against installed package without reading source

### Tests for User Story 4

- [x] T023 [P] [US4] Add a lightweight docs presence/content test or contract assertion that `docs/agent-integration.md` exists and mentions `grapheinstein.api`, `/index`, `/query`, and `[serve]` in `tests/contract/test_cli_serve.py` or a small `tests/contract/test_agent_docs.py`

### Implementation for User Story 4

- [x] T024 [US4] Write `docs/agent-integration.md` with Python API examples, HTTP curl examples, CLI↔Python↔HTTP parity table, and `pip install 'grapheinstein[serve]'` per FR-011 / `research.md` R5
- [x] T025 [US4] Update `README.md` with a short Agent integration section linking to `docs/agent-integration.md` and noting optional serve
- [x] T026 [US4] Ensure `grapheinstein serve --help` epilog/help text references `docs/agent-integration.md` in `src/grapheinstein/cli.py`

**Checkpoint**: Agents can integrate from docs alone

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and schema hygiene

- [x] T027 [P] Confirm graph `schema_version` remains `6.0.0` and query-answer `1.0.0` with no accidental bumps in `src/grapheinstein/core/graph.py` / `src/grapheinstein/core/query.py`
- [x] T028 Run scenarios from `specs/012-serve-api/quickstart.md` and fix gaps in `src/grapheinstein/` or tests
- [x] T029 [P] Extend root CLI epilog in `src/grapheinstein/cli.py` with a `serve` example if not already covered

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **User Story 1 (Phase 3)**: After Foundational — MVP (Python `index`)
- **User Story 2 (Phase 4)**: After Foundational — ideally after US1 so `api.py` patterns exist; independently testable once `query()` lands
- **User Story 3 (Phase 5)**: After US1 + US2 (HTTP must call both API functions)
- **User Story 4 (Phase 6)**: After US1 at minimum; best after US3 so HTTP examples are accurate
- **Polish (Phase 7)**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependency on US2–US4
- **US2 (P1)**: After Foundational; practical dependency on US1 for shared `api.py` style
- **US3 (P2)**: Depends on US1 + US2 API functions
- **US4 (P2)**: Docs; depends on stable API names; HTTP section after US3

### Within Each User Story

- Tests marked first SHOULD fail before implementation
- API/core before CLI/HTTP wiring
- Story complete before next priority when sequential

### Parallel Opportunities

- T001 ∥ T002 (Setup; T003 after or with them)
- T005 ∥ T006 (Foundational after T004 starts)
- T007 ∥ T008 (US1 tests)
- T012 ∥ T013 (US2 tests)
- T016 ∥ T017 ∥ T018 (US3 tests)
- T024 ∥ T025 (US4 docs; T026 after serve help exists)
- T027 ∥ T029 (Polish)
- After Foundational: US1 then US2 sequential on `api.py`; US3 after both

---

## Parallel Example: User Story 1

```bash
# Tests in parallel:
Task: "Contract tests for index in tests/contract/test_python_api.py"
Task: "API index fixture graph in tests/unit/test_api_wrappers.py"

# Then implementation:
Task: "Implement index() in src/grapheinstein/api.py"
Task: "Refactor CLI index to call api in src/grapheinstein/cli.py"
```

---

## Parallel Example: User Story 3

```bash
# Tests in parallel:
Task: "CLI serve contract in tests/contract/test_cli_serve.py"
Task: "HTTP TestClient contracts in tests/contract/test_http_api.py"
Task: "Serve round-trip in tests/integration/test_serve_roundtrip.py"

# Then implementation (serve package then CLI):
Task: "FastAPI routes in src/grapheinstein/serve/app.py"
Task: "run_server in src/grapheinstein/serve/__init__.py"
Task: "serve command in src/grapheinstein/cli.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (`api.index`)
4. **STOP and VALIDATE**: quickstart Scenario A (index portion)
5. Demo: `from grapheinstein.api import index; index(".", output="graph.json")`

### Incremental Delivery

1. Setup + Foundational → stubs + deps check
2. US1 → Python index (MVP)
3. US2 → Python query + CLI parity
4. US3 → optional `serve` HTTP
5. US4 → agent docs + README
6. Polish → quickstart green

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Then:
   - Developer A: US1 + US2 (`api.py` + CLI refactor)
   - Developer B: US3 stubs/tests (blocked on API until T009/T014 land)
3. US4 after API (+ HTTP) names stabilize

---

## Notes

- [P] tasks = different files, no dependencies on incomplete work
- Graph schema stays `6.0.0`; query-answer stays `1.0.0`
- Never import FastAPI from `api.py` or core CLI command modules at import time
- Default bind `127.0.0.1`; default port `8000`
- Commit after each task or logical group
- Stop at checkpoints to validate stories independently
