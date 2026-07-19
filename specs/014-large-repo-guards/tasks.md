---
description: "Task list for Large Repo Guards"
---

# Tasks: Large Repo Guards

**Input**: Design documents from `/specs/014-large-repo-guards/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — constitution and plan require tests when CLI contracts change (new index flags, config keys, exit codes `2`/`3`, reference eligibility).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: `src/grapheinstein/`, `tests/` at repository root

## Grapheinstein Task Categories *(when applicable)*

- **Config**: New `AppConfig` keys, `CODE_ONLY_DEFAULT_IGNORES`, init template (`utils.py`)
- **Ingest**: Effective ignore merge + inventory size/count gates (`core/index.py`)
- **Graph**: Bounded `references` linking (`core/references.py`); schema stays `6.0.0`
- **CLI/API**: `--code-only`, `--include-generated-docs`, `--allow-large-repo`; `api.index` + serve parity
- **Contracts/tests**: Fixture + unit/integration/contract coverage per `quickstart.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Fixture tree mimicking google-api-python-client proportions for all stories

- [x] T001 [P] Create `tests/fixtures/large_repo_guards/` with `pkg/__init__.py`, `pkg/a.py` (whole-token mention of `b.py`), `pkg/b.py`, `docs/dyn/` HTML dump (generate many small files in fixture builder or committed sample set), and `discovery_cache/service.json` per `quickstart.md`
- [x] T002 [P] Add `tests/fixtures/large_repo_guards/README.md` documenting expected code-only exclusions, reference edge `pkg/a.py` → `pkg/b.py`, and how to regenerate the HTML dump if generated at test time

**Checkpoint**: Fixture installable/usable by pytest; package unchanged

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config surface, error types, and ignore-merge helpers all stories share

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Extend `AppConfig` and YAML coercion in `src/grapheinstein/utils.py` with `code_only` (bool, default `false`), `include_generated_docs` (bool, default `false`), `max_reference_scan_bytes` (int, default `262144`), `max_reference_scan_ops` (int, default `5000000`), `max_non_code_share` (float, default `0.85`), `max_total_bytes` (int, default `838860800`), `max_file_count` (int, default `20000`), `timeout_seconds` (int, default `0`), `large_repo_policy` (`reject`|`allow`, default `reject`) per `contracts/cli.md`
- [x] T004 [P] Add `CODE_ONLY_DEFAULT_IGNORES` constant in `src/grapheinstein/utils.py` (`docs/`, `docs/dyn/`, `**/docs/dyn/`, `discovery_cache/`, `**/discovery_cache/`) and helper `effective_ignored_patterns(config_patterns, *, code_only, include_generated_docs) -> tuple[str, ...]`
- [x] T005 [P] Add domain errors `LargeRepoError` and `IndexTimeoutError` in `src/grapheinstein/utils.py` (or `src/grapheinstein/core/errors.py` if split) with message fields for tripped gates / phase name per `contracts/python-api.md`
- [x] T006 Update `DEFAULT_CONFIG_TEMPLATE` / init comments in `src/grapheinstein/utils.py` to document the new keys and code-only default-ignore behavior
- [x] T007 [P] Extend unit tests in `tests/unit/test_config.py` for new key defaults, invalid thresholds (`max_file_count < 1`, `max_non_code_share` out of range, bad `large_repo_policy`), and `effective_ignored_patterns` merge / opt-out via `include_generated_docs`

**Checkpoint**: Config loads with new defaults; ignore helper and error types ready; existing indexes still work with old configs

---

## Phase 3: User Story 1 - Code-Only Indexes the Real Package, Not Doc Dumps (Priority: P1) 🎯 MVP

**Goal**: `--code-only` excludes generated docs/discovery caches from inventory by default; `--include-generated-docs` opts back in

**Independent Test**: Index `tests/fixtures/large_repo_guards` with `--code-only`; graph has `pkg/*`, no `docs/` or `discovery_cache/` nodes; with `--include-generated-docs` those paths may appear (quickstart Scenario A/B)

### Tests for User Story 1

- [x] T008 [P] [US1] Add contract tests for `--code-only` / `--include-generated-docs` help and flag parsing in `tests/contract/test_cli_index_guards.py`
- [x] T009 [P] [US1] Add unit tests for code-only default ignore application in `tests/unit/test_ignore_patterns.py` (extend): paths under `docs/dyn/` and `discovery_cache/` excluded when `code_only` and not `include_generated_docs`
- [x] T010 [P] [US1] Add integration test indexing the large-repo fixture with `--code-only` in `tests/integration/test_cli_large_repo_guards.py` asserting graph nodes omit generated dumps and include `pkg/a.py` / `pkg/b.py`

### Implementation for User Story 1

- [x] T011 [US1] Wire `code_only` / `include_generated_docs` into discovery in `src/grapheinstein/core/index.py`: merge `effective_ignored_patterns(...)` into the ignore set passed to `discover_paths` / inventory build
- [x] T012 [US1] Add CLI flags `--code-only` and `--include-generated-docs` on `index` (and bare-path alias) in `src/grapheinstein/cli.py`; pass through config overrides
- [x] T013 [US1] Mirror kwargs `code_only` and `include_generated_docs` on `index()` in `src/grapheinstein/api.py` and on serve `IndexBody` / `POST /index` in `src/grapheinstein/serve/app.py` per `contracts/python-api.md`

**Checkpoint**: US1 MVP — code-only indexing of the fixture finishes with a usable graph and no doc-dump nodes

---

## Phase 4: User Story 2 - Reference Linking Stays Bounded (Priority: P1)

**Goal**: Reference scan skips oversize/non-code (when code-only), caps bytes per file, preserves whole-token edges among eligible code files

**Independent Test**: Unit/integration fixtures show no full read of oversize/HTML sources under code-only; `pkg/a.py` → `pkg/b.py` edge still created; mention past byte cap does not create edge (quickstart Scenario D/E)

### Tests for User Story 2

- [x] T014 [P] [US2] Extend `tests/unit/test_references.py` for: skip `metadata.skipped == "oversize"`, skip non-code sources when `code_only=True`, honor `max_reference_scan_bytes` prefix, and keep happy-path whole-token edge among `.py` files
- [x] T015 [P] [US2] Add integration assertion in `tests/integration/test_cli_large_repo_guards.py` that `--code-only` index produces `references` from `pkg/a.py` to `pkg/b.py` and does not hang on HTML dump

### Implementation for User Story 2

- [x] T016 [US2] Refactor `add_reference_edges` in `src/grapheinstein/core/references.py` to accept eligibility options (`code_only`, `max_reference_scan_bytes`, code-suffix set from `EXTENSION_MAP` in `src/grapheinstein/core/parsers/registry.py`); skip oversize/symlink/non-eligible; read at most N bytes before UTF-8 decode; preserve longest-basename-first whole-token match and `extracted` provenance
- [x] T017 [US2] Pass eligibility options from `build_inventory_graph` / `index_project` in `src/grapheinstein/core/index.py` into `add_reference_edges`
- [x] T018 [US2] Ensure `max_reference_scan_bytes` from config flows CLI → `api.index` → index core in `src/grapheinstein/cli.py` and `src/grapheinstein/api.py` (config-driven; no new CLI flag required)

**Checkpoint**: US1+US2 — fixture indexes quickly with bounded scans and correct code references

---

## Phase 5: User Story 3 - Preflight Rejects Hopeless Jobs Early (Priority: P2)

**Goal**: After inventory, reject on `max_total_bytes` / `max_file_count` / `estimated_scan_ops` / `max_non_code_share` unless `--allow-large-repo`; clear stderr remediation; exit code `2`

**Independent Test**: Low `max_reference_scan_ops` config against full fixture without code-only ignores rejects in &lt;30s with no success graph; `--allow-large-repo` proceeds subject to hard caps (quickstart Scenario C)

### Tests for User Story 3

- [x] T019 [P] [US3] Add unit tests for scan-cost estimate and gate decisions in `tests/unit/test_preflight_scan_cost.py` (`eligible_scan_files * unique_basenames`, non-code share, policy allow vs reject, hard caps always win)
- [x] T020 [P] [US3] Extend `tests/contract/test_cli_index_guards.py` for `--allow-large-repo` and exit code `2` on preflight reject
- [x] T021 [P] [US3] Add integration test in `tests/integration/test_cli_large_repo_guards.py` for fast reject (no output graph) and override path with `--allow-large-repo`

### Implementation for User Story 3

- [x] T022 [US3] Implement `compute_scan_cost_estimate(graph, *, code_only, ...)` and `enforce_large_repo_gates(...)` in `src/grapheinstein/core/index.py` (or `src/grapheinstein/core/preflight.py`) per `data-model.md` / `research.md` R4; raise `LargeRepoError` with tripped gates + remediation hints
- [x] T023 [US3] Call gates after inventory / before heavy reference work in `src/grapheinstein/core/index.py`; map `LargeRepoError` to CLI exit code `2` in `src/grapheinstein/cli.py` without writing a successful graph
- [x] T024 [US3] Add `--allow-large-repo` flag in `src/grapheinstein/cli.py` and kwargs on `src/grapheinstein/api.py` + `src/grapheinstein/serve/app.py`; set `large_repo_policy=allow` for the run (does not bypass `max_total_bytes` / `max_file_count`)

**Checkpoint**: Hopeless jobs fail fast with actionable messages; modest projects unaffected

---

## Phase 6: User Story 4 - Timeouts Fail Clearly Without Fake Success (Priority: P3)

**Goal**: Cooperative `timeout_seconds` aborts with exit code `3`, phase in message, no success graph

**Independent Test**: Config `timeout_seconds: 1` on a job that cannot finish → non-zero, phase mentioned, no successful complete graph claim (spec US4)

### Tests for User Story 4

- [x] T025 [P] [US4] Add unit/integration coverage for timeout phase reporting and exit code `3` in `tests/unit/test_preflight_scan_cost.py` and/or `tests/integration/test_cli_large_repo_guards.py` (force short timeout; assert no success graph)
- [x] T026 [P] [US4] Extend contract tests in `tests/contract/test_cli_index_guards.py` documenting timeout exit code `3` behavior

### Implementation for User Story 4

- [x] T027 [US4] Add phase markers and cooperative deadline checks between major phases and periodically during reference scan in `src/grapheinstein/core/index.py` and `src/grapheinstein/core/references.py`; raise `IndexTimeoutError` with phase name when `timeout_seconds > 0` exceeded
- [x] T028 [US4] Map `IndexTimeoutError` to CLI exit code `3` in `src/grapheinstein/cli.py`; ensure `api.index` / serve do not return success; never persist a successful complete graph on timeout

**Checkpoint**: All four stories independently verifiable; wrappers get clear timeout semantics

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Docs, regression, quickstart validation

- [x] T029 [P] Update user-facing help strings in `src/grapheinstein/cli.py` for the three new flags and point operators at config keys for numeric thresholds
- [x] T030 [P] Run regression index on an existing small code fixture (e.g. current code integration fixture) and assert reference happy-path unchanged in `tests/integration/test_cli_large_repo_guards.py` or existing `tests/integration/test_cli_index_code.py`
- [x] T031 Execute `specs/014-large-repo-guards/quickstart.md` scenarios A–E manually or via pytest markers; fix any gaps
- [x] T032 [P] Confirm graph `schema_version` remains `6.0.0` in contract/integration assertions (no accidental bump in `src/grapheinstein/core/graph.py`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP
- **US2 (Phase 4)**: Depends on Foundational; ideally after US1 so fixture path is code-only-scoped, but reference bounds can be unit-tested independently
- **US3 (Phase 5)**: Depends on Foundational; benefits from US1/US2 eligibility rules for accurate `eligible_scan_files`
- **US4 (Phase 6)**: Depends on Foundational + index phase structure from US2/US3 wiring
- **Polish (Phase 7)**: Depends on desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — no dependency on US2–US4
- **US2 (P1)**: After Phase 2 — independent unit tests; integration strongest after US1
- **US3 (P2)**: After Phase 2 — should use US2 eligibility when computing ops (implement US2 first recommended)
- **US4 (P3)**: After Phase 2 — needs phase hooks in index/references (after US2/US3 implementation tasks)

### Within Each User Story

- Tests marked first SHOULD fail before implementation
- Config/helpers before CLI/API wiring
- Core behavior before serve parity
- Story checkpoint before next priority

### Parallel Opportunities

- T001 ∥ T002 (Setup)
- T004 ∥ T005 ∥ T007 (within Foundational after T003 starts; T007 after T003–T004)
- T008 ∥ T009 ∥ T010 (US1 tests)
- T014 ∥ T015 (US2 tests)
- T019 ∥ T020 ∥ T021 (US3 tests)
- T025 ∥ T026 (US4 tests)
- T029 ∥ T030 ∥ T032 (Polish)
- After Foundational: US1 and US2 test authoring can proceed in parallel; implementation of US3 should follow US2 eligibility

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together:
Task: "Contract tests for --code-only / --include-generated-docs in tests/contract/test_cli_index_guards.py"
Task: "Unit tests for code-only ignores in tests/unit/test_ignore_patterns.py"
Task: "Integration test fixture --code-only in tests/integration/test_cli_large_repo_guards.py"

# Then implement core → CLI → API/serve sequentially:
Task: "Wire effective ignores in src/grapheinstein/core/index.py"
Task: "CLI flags in src/grapheinstein/cli.py"
Task: "API/serve kwargs in src/grapheinstein/api.py and src/grapheinstein/serve/app.py"
```

---

## Parallel Example: User Story 3

```bash
Task: "Unit tests in tests/unit/test_preflight_scan_cost.py"
Task: "Contract exit code 2 in tests/contract/test_cli_index_guards.py"
Task: "Integration reject/override in tests/integration/test_cli_large_repo_guards.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (fixture)
2. Complete Phase 2: Foundational (config + ignore helper + errors)
3. Complete Phase 3: US1 (`--code-only` scoping)
4. **STOP and VALIDATE**: Fixture indexes under 2 minutes with no doc-dump nodes
5. Demo/ship MVP to unblock OpenClaw-style code-only runs

### Incremental Delivery

1. Setup + Foundational → config ready
2. US1 → scoped inventory (MVP!)
3. US2 → bounded references (stops CPU peg on remaining files)
4. US3 → fast reject for remaining hopeless trees
5. US4 → clear timeout semantics for wrappers
6. Polish → quickstart + regression

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Dev A: US1 | Dev B: US2 unit/`references.py` (coordinate on `index.py` merge)
3. Dev C: US3 preflight module after eligibility API from US2 is sketched
4. US4 last on shared phase-marker hooks

---

## Notes

- [P] = different files, no incomplete-task dependencies
- [USn] maps to spec user stories (US1 scoping, US2 refs, US3 preflight, US4 timeout)
- Graph schema must remain `6.0.0`; sharding/merge is out of scope (FR-012)
- Hard caps (`max_total_bytes`, `max_file_count`) always win over `--allow-large-repo`
- Commit after each task or logical group; stop at checkpoints to validate independently
