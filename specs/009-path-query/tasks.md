---
description: "Task list for Path Between Concepts"
---

# Tasks: Path Between Concepts

**Input**: Design documents from `/specs/009-path-query/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — constitution and plan require tests when CLI contracts or provenance-labeled query outputs change (`path` subcommand, path-answer JSON, edge `type`/`provenance` on steps).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: `src/grapheinstein/`, `tests/` at repository root

## Grapheinstein Task Categories *(when applicable)*

- **Query**: endpoint match + weighted shortest path + explanation (`core/match.py`, `core/path.py`)
- **Graph**: reuse `load_artifact` / `artifact_to_digraph` (`core/graph.py`)
- **Extract/LLM**: optional explanation polish via existing `chat_text` (`core/parsers/llm_ollama.py`)
- **Config/CLI**: `path` command and `path_*` keys (`cli.py`, `utils.py`)
- **Contracts/tests**: CLI + path-answer JSON tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module stub and fixture graphs for path / competing-route scenarios

- [x] T001 [P] Create `src/grapheinstein/core/path.py` stub with module docstring and placeholder public API (`edge_cost`, `find_weighted_path`, `build_path_answer`, `format_deterministic_explanation`, `PathAnswer` / `PathError` types) per `plan.md` and `data-model.md`
- [x] T002 [P] Create `tests/fixtures/path_graphs/` with minimal valid schema `6.0.0` JSON graphs: (1) a simple directed chain for happy-path, (2) two competing routes where weighting prefers one, (3) a disconnected pair / island nodes, plus brief notes in `tests/fixtures/path_graphs/README.md` documenting node phrases and expected preferred midpoints per `quickstart.md`

**Checkpoint**: Package still installable; path stub and fixtures in place

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Path config keys and thin helpers that all stories depend on (reuse existing match / DiGraph / chat_text from explain)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Extend `AppConfig` and YAML coercion in `src/grapheinstein/utils.py` with `path_match_threshold: float = 0.55`, `path_max_hops: int = 32`, `path_confidence_default: float = 0.5`, `path_confidence_floor: float = 0.35`, `path_provenance_inferred_factor: float = 1.75` per `contracts/cli.md` (alias unset threshold to explain match threshold only if documented and tested)
- [x] T004 Confirm reuse of `artifact_to_digraph` in `src/grapheinstein/core/graph.py` and `select_matches` / scoring in `src/grapheinstein/core/match.py` from path orchestration (add a small `resolve_endpoint` helper in `src/grapheinstein/core/path.py` that wraps top-1 match selection if cleaner than duplicating call sites)
- [x] T005 [P] Add shared path-answer serialization helper stub in `src/grapheinstein/core/path.py` (`path_answer_to_dict` / JSON dump) matching `contracts/path-json.md` field names (`kind`, `version`, `steps`, …) without full path-finding yet

**Checkpoint**: Foundation ready — path config keys and answer shape helpers available; match/DiGraph reuse confirmed

---

## Phase 3: User Story 1 - Find How Two Concepts Connect (Priority: P1) 🎯 MVP

**Goal**: `grapheinstein path <start> <end> --input` resolves endpoints, finds a directed path, emits path-answer JSON on stdout with per-step `type`/`provenance`, and prints a deterministic explanation on stderr

**Independent Test**: Run path on `tests/fixtures/path_graphs/` chain fixture with `--no-llm-explain`; assert `kind == path_answer`, ordered nodes, each step has `type`+`provenance`, explanation present (quickstart Scenario A, E)

### Tests for User Story 1

- [x] T006 [P] [US1] Add unit tests for path finding on a simple chain and path-answer dict shape in `tests/unit/test_path_find.py`
- [x] T007 [P] [US1] Add unit tests for deterministic explanation text grounded in steps in `tests/unit/test_path_explain.py`
- [x] T008 [P] [US1] Add contract tests for `path` CLI shape (`START`, `END`, `--input`, `--output`, `--no-llm-explain`) in `tests/contract/test_cli_path.py`
- [x] T009 [P] [US1] Add integration tests for happy-path path JSON on stdout + optional `--output` file parity in `tests/integration/test_cli_path_cmd.py`

### Implementation for User Story 1

- [x] T010 [US1] Implement baseline `edge_cost` and `find_weighted_path` in `src/grapheinstein/core/path.py` using NetworkX `shortest_path` with a weight callable; support trivial same-node path (`steps=[]`) and map `NetworkXNoPath` to a clear `PathError` per `research.md` R3–R4 (usable defaults for type/provenance/confidence even if US2 hardens weights)
- [x] T011 [US1] Implement `build_path_answer` + `format_deterministic_explanation` in `src/grapheinstein/core/path.py` producing `path_answer` v1.0.0 with `start`/`end` endpoint objects, `nodes`, `steps` (`type`, `provenance`, optional `confidence`, `cost`), `hop_count`, `total_cost`, `explanation`, `explanation_mode`, `generated_at` per `contracts/path-json.md`
- [x] T012 [US1] Implement `find_path` (or equivalent) orchestration in `src/grapheinstein/core/path.py`: `load_artifact` → `artifact_to_digraph` → resolve start/end (top-1 match) → weighted path → build answer; optional LLM polish injectable later; return structured result for CLI
- [x] T013 [US1] Add `grapheinstein path` command in `src/grapheinstein/cli.py`: add `path` to `_KNOWN_COMMANDS`; positionals `START`/`END`; required `--input`/`-i`; optional `--output`/`-o`; `--no-llm-explain`; wire config overrides; dump path-answer JSON to **stdout**; print explanation/summary on stderr; errors via `_fail`
- [x] T014 [US1] Ensure success path never mixes prose into stdout JSON and optional `--output` uses atomic write of the same document in `src/grapheinstein/cli.py` / `src/grapheinstein/core/path.py` per `research.md` R1/R6

**Checkpoint**: US1 MVP — path emits valid path-answer JSON with labeled steps and deterministic explanation

---

## Phase 4: User Story 2 - Prefer Stronger, More Trustworthy Routes (Priority: P1)

**Goal**: Multi-factor edge costs (relation type, confidence, provenance) select the preferred route when competitors exist; missing confidence uses defaults; explanation describes the chosen route only

**Independent Test**: Competing-routes fixture returns the weighting-policy winner (not the short inferred-heavy alternate); explanation mentions chosen edge types (quickstart Scenario B)

### Tests for User Story 2

- [x] T015 [P] [US2] Add unit tests for `edge_cost` defaults (extracted vs inferred, high vs low confidence, missing confidence → default) in `tests/unit/test_path_weights.py`
- [x] T016 [P] [US2] Add unit/integration coverage that competing routes pick the preferred path in `tests/unit/test_path_find.py` and/or `tests/integration/test_cli_path_cmd.py` using `tests/fixtures/path_graphs/` weighted fixture

### Implementation for User Story 2

- [x] T017 [US2] Harden `edge_cost` in `src/grapheinstein/core/path.py` with documented `type_base` table, `provenance_factor`, `path_confidence_default` / `path_confidence_floor`, and positive finite costs per `research.md` R4
- [x] T018 [US2] Wire cost-policy config fields from `src/grapheinstein/utils.py` into path finding in `src/grapheinstein/core/path.py` / `src/grapheinstein/cli.py` so inferred/low-confidence edges are disfavored vs extracted/high-confidence when types are equal
- [x] T019 [US2] Ensure `total_cost` / per-step `cost` in the path answer reflect the chosen route and that deterministic explanation narrates only those steps in `src/grapheinstein/core/path.py`

**Checkpoint**: US1 + US2 — weighted preferred paths with trustworthy-route fixtures green

---

## Phase 5: User Story 3 - Resolve Endpoints Flexibly and Fail Clearly (Priority: P2)

**Goal**: Fuzzy/approximate endpoint phrases resolve; unresolved endpoints, no path, bad input, empty args, and over-long paths fail clearly with no fabricated success JSON; optional embeddings soft-skip

**Independent Test**: Approximate phrases succeed; nonsense endpoint and disconnected pair → non-zero, empty stdout; invalid input → clear error (quickstart Scenarios C, D)

### Tests for User Story 3

- [x] T020 [P] [US3] Extend unit tests in `tests/unit/test_path_find.py` for unresolved endpoint errors (which side failed), `NetworkXNoPath`, trivial same-node, and `max_hops` exceeded
- [x] T021 [P] [US3] Extend contract/integration tests in `tests/contract/test_cli_path.py` and `tests/integration/test_cli_path_cmd.py` for empty start/end, missing/invalid input, no-match, disconnected pair (no success JSON on stdout), and fuzzy approximate phrases

### Implementation for User Story 3

- [x] T022 [US3] Enforce non-empty start/end, match-threshold validation, and per-endpoint unresolved errors naming the failed side(s) in `src/grapheinstein/cli.py` / `src/grapheinstein/core/path.py` per `research.md` R1–R2
- [x] T023 [US3] Enforce directed no-path and `path_max_hops` / `--max-hops` failures (non-zero exit, no success JSON) in `src/grapheinstein/core/path.py` / `src/grapheinstein/cli.py`
- [x] T024 [US3] Expose `--match-threshold` and `--max-hops` on `path` in `src/grapheinstein/cli.py` / `src/grapheinstein/utils.py` per `contracts/cli.md`
- [x] T025 [US3] Integrate optional local embeddings into endpoint ranking via existing match helpers (soft-skip with clear note when unavailable) in `src/grapheinstein/core/path.py`; keep fuzzy-only success path
- [x] T026 [US3] Optional LLM explanation polish via injectable `chat_text` with deterministic fallback; `--no-llm-explain` skips polish in `src/grapheinstein/core/path.py` / `src/grapheinstein/cli.py` (no cloud fallback)
- [x] T027 [US3] Accept gzip inputs via existing `load_artifact` for path in `src/grapheinstein/cli.py` / `src/grapheinstein/core/path.py` (parity with explain/merge)

**Checkpoint**: All user stories independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Help text, config coverage, quickstart validation, full suite

- [x] T028 [P] Update CLI help expectations in `tests/contract/test_cli_help.py` so `path` is listed and `path --help` surfaces key options
- [x] T029 [P] Add config unit coverage for `path_match_threshold` / `path_max_hops` / `path_confidence_default` / `path_confidence_floor` / `path_provenance_inferred_factor` in `tests/unit/test_config.py`
- [x] T030 Run end-to-end validation from `specs/009-path-query/quickstart.md` and fix any gaps in `src/grapheinstein/` or tests
- [x] T031 Run full pytest suite (`tests/unit`, `tests/contract`, `tests/integration`) and fix regressions from path/query changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **User Story 1 (Phase 3)**: After Foundational — **MVP**
- **User Story 2 (Phase 4)**: After Foundational; soft-depends on US1 path-finding / answer build
- **User Story 3 (Phase 5)**: After Foundational; soft-depends on US1 CLI / orchestration
- **Polish (Phase 6)**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no story dependencies — **MVP**
- **US2 (P1)**: Soft-depends on US1 `find_weighted_path` + answer serialization
- **US3 (P2)**: Soft-depends on US1 CLI/orchestration; hardens matching and failure modes

### Within Each User Story

- Tests (listed) SHOULD be written to fail before implementation where practical
- Core helpers before CLI wiring
- Story complete before moving to next priority when staffing is serial

### Parallel Opportunities

- T001–T002 (Setup) in parallel
- T005 can proceed alongside T003/T004 once stub exists
- T006–T009 (US1 tests) in parallel after Foundational
- T015–T016 (US2 tests) in parallel
- T020–T021 (US3 tests) in parallel
- T028–T029 (Polish) in parallel
- Safest serial order: US1 → US2 → US3

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together:
Task: "Unit tests in tests/unit/test_path_find.py"
Task: "Unit tests in tests/unit/test_path_explain.py"
Task: "Contract tests in tests/contract/test_cli_path.py"
Task: "Integration tests in tests/integration/test_cli_path_cmd.py"

# Then implement: path.py (cost + find + answer) → cli.py
```

## Parallel Example: User Story 2

```bash
# Launch US2 tests together:
Task: "Weight unit tests in tests/unit/test_path_weights.py"
Task: "Competing-route coverage in tests/unit/test_path_find.py / tests/integration/test_cli_path_cmd.py"
```

## Parallel Example: User Story 3

```bash
# Launch US3 tests together:
Task: "Failure/max-hops unit tests in tests/unit/test_path_find.py"
Task: "CLI failure + fuzzy integration in tests/contract/test_cli_path.py / tests/integration/test_cli_path_cmd.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently (path-answer JSON + labeled steps + explanation)
5. Demo/ship MVP if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 → Happy-path path query (MVP)
3. US2 → Weighted preferred routes
4. US3 → Fuzzy endpoints + clear failures + optional LLM polish
5. Polish → help/config/quickstart/full suite

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (orchestration + CLI)
   - Developer B: User Story 2 (weight policy + fixtures) after US1 path finder lands
   - Developer C: User Story 3 failure modes / CLI flags after US1 CLI lands
3. Integrate and run full suite in Polish

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Reuse `core/match.py`, `artifact_to_digraph`, and `chat_text` — do not reimplement fuzzy matching
- Path answer is **not** a `graph.json` envelope; do not validate via `validate_artifact`
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same-file conflicts, inventing reverse edges for undirected shortcuts
