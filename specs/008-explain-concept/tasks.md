---
description: "Task list for Explain Concept Subgraph"
---

# Tasks: Explain Concept Subgraph

**Input**: Design documents from `/specs/008-explain-concept/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — constitution and plan require tests when CLI contracts or portable graph outputs change (`explain` subcommand, explanation subgraph schema metadata, provenance preservation).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: `src/grapheinstein/`, `tests/` at repository root

## Grapheinstein Task Categories *(when applicable)*

- **Query**: match + neighborhood + explain orchestration (`core/match.py`, `core/explain.py`)
- **Graph**: artifact↔DiGraph helpers, subgraph write via existing I/O (`core/graph.py`)
- **Extract/LLM**: plain-text chat + optional embeddings (`core/parsers/llm_ollama.py`)
- **Config/CLI**: `explain` command and explain_* keys (`cli.py`, `utils.py`)
- **Contracts/tests**: CLI + subgraph artifact tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module stubs and fixture graphs for explain matching / neighborhood scenarios

- [x] T001 [P] Create `src/grapheinstein/core/match.py` stub with module docstring and placeholder public API (`score_nodes`, `select_matches`, `MatchCandidate`) per `plan.md` and `data-model.md`
- [x] T002 [P] Create `src/grapheinstein/core/explain.py` stub with module docstring and placeholder public API (`explain_concept`, `ExplainResult`, `ExplainError` / no-match error) per `plan.md` and `research.md` R1
- [x] T003 [P] Create `tests/fixtures/explain_graphs/` with minimal valid schema `6.0.0` JSON: a connected neighborhood around a known concept (e.g. `concept::auth` linked to file/function nodes at 1 and 2 hops), plus brief notes in `tests/fixtures/explain_graphs/README.md` per `quickstart.md`

**Checkpoint**: Package still installable; match/explain stubs and fixtures in place

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared config, graph conversion, and LLM text helpers that all stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add `artifact_to_digraph(artifact: dict) -> nx.DiGraph` (or equivalent) in `src/grapheinstein/core/graph.py` using NetworkX `node_link_graph(..., edges="links")` so explain can traverse neighborhoods without duplicating load logic
- [x] T005 Extend `AppConfig` and YAML coercion in `src/grapheinstein/utils.py` with `explain_hops: int = 2`, `explain_top_n: int = 3`, `explain_match_threshold: float = 0.55`, `explain_node_cap: int = 500` per `contracts/cli.md`
- [x] T006 Add plain-text `chat_text(...)` helper in `src/grapheinstein/core/parsers/llm_ollama.py` (Ollama `/api/chat` without JSON-schema `format`) returning assistant string; keep existing structured `chat()` unchanged per `research.md` R5
- [x] T007 [P] Add optional `embed_texts(...)` (or single-text) helper in `src/grapheinstein/core/parsers/llm_ollama.py` calling Ollama `/api/embeddings` via stdlib HTTP, returning vectors or raising a clear local error for callers to soft-skip per `research.md` R3

**Checkpoint**: Foundation ready — config keys, DiGraph conversion, and LLM text/embed helpers available

---

## Phase 3: User Story 1 - Explain a Concept from a Project Graph (Priority: P1) 🎯 MVP

**Goal**: `grapheinstein explain <concept> --input --output` finds a match, writes a portable neighborhood subgraph, and prints a local-LLM summary when available (or skips summary cleanly)

**Independent Test**: Run explain on `tests/fixtures/explain_graphs/` with `--no-summary`; assert schema `6.0.0` subgraph with match + neighbors and explain metadata; with injectable fake `chat_text`, assert summary on human stream (quickstart Scenarios A, E, F)

### Tests for User Story 1

- [x] T008 [P] [US1] Add unit tests for undirected neighborhood extraction and subgraph artifact metadata in `tests/unit/test_explain_neighborhood.py`
- [x] T009 [P] [US1] Add unit tests for summary prompt/status handling with injectable chat in `tests/unit/test_explain_summary.py`
- [x] T010 [P] [US1] Add contract tests for `explain` CLI shape (`--input`, `--output`, `--hops`, `--no-summary`) in `tests/contract/test_cli_explain.py`
- [x] T011 [P] [US1] Add integration tests for happy-path explain write + `--no-summary` in `tests/integration/test_cli_explain_cmd.py`

### Implementation for User Story 1

- [x] T012 [US1] Implement baseline node text extraction + scoring and `select_matches` in `src/grapheinstein/core/match.py` (exact/casefold, substring/token overlap, `difflib` ratio; threshold + top-N; concept-type tie-break) sufficient for clear fixture hits per `research.md` R2
- [x] T013 [US1] Implement neighborhood extract + explanation artifact build in `src/grapheinstein/core/explain.py`: undirected hops (default 2), induced links preserving `type`/`provenance`/optional attrs, graph metadata (`explained_concept`, `explain_match_ids`, `explain_hops`, fresh `generated_at`) per `data-model.md` and `contracts/graph-json.md`
- [x] T014 [US1] Implement `explain_concept` orchestration in `src/grapheinstein/core/explain.py`: `load_artifact` → match → neighborhood → `write_artifact_dict` / validate-atomic write; optional summary via injectable `chat_text` + `check_ready`; return structured result (paths, matches, summary status)
- [x] T015 [US1] Add `grapheinstein explain` command in `src/grapheinstein/cli.py`: add `explain` to `_KNOWN_COMMANDS`; positional `CONCEPT`; required `--input`/`-i` and `--output`/`-o`; `--no-summary`; wire config/LLM overrides; print match summary + narrative on human-readable stream; errors via `_fail`
- [x] T016 [US1] Ensure explain success path never mixes prose into the subgraph file and never leaves a partial corrupt success artifact at `--output` (validate + atomic write only) in `src/grapheinstein/core/explain.py` / `src/grapheinstein/cli.py`

**Checkpoint**: US1 MVP — explain writes a valid subgraph and can summarize with a local model (or `--no-summary`)

---

## Phase 4: User Story 2 - Match Concepts by Fuzzy Text and Semantic Similarity (Priority: P1)

**Goal**: Approximate phrases and (when available) local embeddings rank the right nodes; multiple strong matches merge neighborhoods; embeddings unavailable does not break fuzzy-only explain

**Independent Test**: Fixture typo/partial selects intended node; with fake embeddings, paraphrase re-ranks; with embeddings failing, fuzzy still succeeds and notes skip (quickstart Scenario C)

### Tests for User Story 2

- [x] T017 [P] [US2] Add unit tests for fuzzy scoring (typo/partial/plural-ish), thresholding, top-N, and concept tie-break in `tests/unit/test_match.py`
- [x] T018 [P] [US2] Extend `tests/unit/test_match.py` (or add sibling) for embedding score merge (`max(fuzzy, embedding)`), soft-skip when embed unavailable, and multi-match selection
- [x] T019 [P] [US2] Extend integration coverage in `tests/integration/test_cli_explain_cmd.py` for approximate concept phrases and multi-match merged neighborhoods

### Implementation for User Story 2

- [x] T020 [US2] Harden fuzzy scoring edge cases and documentable defaults in `src/grapheinstein/core/match.py` so approximate fixture phrases reliably beat noise above `explain_match_threshold`
- [x] T021 [US2] Integrate optional Ollama embeddings into ranking in `src/grapheinstein/core/match.py` / `src/grapheinstein/core/explain.py` (prefilter + re-rank or full small-graph embed; combine with fuzzy via max; single clear skip note when unavailable) per `research.md` R3
- [x] T022 [US2] Ensure multi-match path merges undirected neighborhoods for up to `explain_top_n` seeds in `src/grapheinstein/core/explain.py` and records all primary ids in `explain_match_ids` / optional `explain_match_scores`
- [x] T023 [US2] Expose `--top-n` and `--match-threshold` (and config overrides) on `explain` in `src/grapheinstein/cli.py` / `src/grapheinstein/utils.py` per `contracts/cli.md`

**Checkpoint**: US1 + US2 — fuzzy + optional vector matching with top-N merge

---

## Phase 5: User Story 3 - Control Neighborhood Depth and Handle Misses Gracefully (Priority: P2)

**Goal**: `--hops` 1|2 controls neighborhood size; no-match and bad input fail clearly without success artifacts; LLM-down still writes subgraph; large neighborhoods truncate with visible flag

**Independent Test**: hops 1 vs 2 node counts; nonsense concept → non-zero and no output file; model unavailable → subgraph written + skip message (quickstart Scenarios B, D, E-offline)

### Tests for User Story 3

- [x] T024 [P] [US3] Extend unit tests in `tests/unit/test_explain_neighborhood.py` for hops 1 vs 2, isolated node, and `explain_node_cap` truncation (`explain_truncated`)
- [x] T025 [P] [US3] Extend contract/integration tests in `tests/contract/test_cli_explain.py` and `tests/integration/test_cli_explain_cmd.py` for no-match (no success file), invalid hops, empty concept, and LLM-unavailable summary skip with exit `0` after write

### Implementation for User Story 3

- [x] T026 [US3] Enforce hops ∈ {1,2}, empty-concept rejection, and no-match non-zero exit with **no** success write in `src/grapheinstein/cli.py` / `src/grapheinstein/core/explain.py` per `research.md` R1
- [x] T027 [US3] Implement `explain_node_cap` truncation (BFS keep seeds, set `graph.explain_truncated`, warn on human stream) in `src/grapheinstein/core/explain.py` per `research.md` R4
- [x] T028 [US3] Wire `--hops` and ensure LLM-unavailable / `--no-summary` paths still write subgraph and report summary status clearly in `src/grapheinstein/cli.py` / `src/grapheinstein/core/explain.py` (reuse `check_ready`; no cloud fallback)
- [x] T029 [US3] Accept gzip inputs via existing `load_artifact` for explain in `src/grapheinstein/cli.py` / `src/grapheinstein/core/explain.py` (parity with visualize/merge)

**Checkpoint**: All user stories independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Help text, config coverage, quickstart validation, full suite

- [x] T030 [P] Update CLI help expectations in `tests/contract/test_cli_help.py` so `explain` is listed and `explain --help` surfaces key options
- [x] T031 [P] Add config unit coverage for `explain_hops` / `explain_top_n` / `explain_match_threshold` / `explain_node_cap` in `tests/unit/test_config.py`
- [x] T032 Run end-to-end validation from `specs/008-explain-concept/quickstart.md` and fix any gaps in `src/grapheinstein/` or tests
- [x] T033 Run full pytest suite (`tests/unit`, `tests/contract`, `tests/integration`) and fix regressions from explain/query changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **User Story 1 (Phase 3)**: After Foundational — **MVP**
- **User Story 2 (Phase 4)**: After Foundational; soft-depends on US1 match/explain orchestration
- **User Story 3 (Phase 5)**: After Foundational; soft-depends on US1 CLI/write path
- **Polish (Phase 6)**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no story dependencies — **MVP**
- **US2 (P1)**: Soft-depends on US1 baseline match + explain pipeline
- **US3 (P2)**: Soft-depends on US1 CLI/write; hop/truncation refine neighborhood from US1

### Within Each User Story

- Tests (listed) SHOULD be written to fail before implementation where practical
- Core helpers before CLI wiring
- Story complete before moving to next priority when staffing is serial

### Parallel Opportunities

- T001–T003 (Setup) in parallel
- T006–T007 (LLM helpers) in parallel after T004/T005 started
- T008–T011 (US1 tests) in parallel after Foundational
- T017–T019 (US2 tests) in parallel
- T024–T025 (US3 tests) in parallel
- T030–T031 (Polish) in parallel
- After Foundational, US2 matching work can proceed in `match.py` while US1 CLI wiring finishes if carefully sequenced; safest serial order is US1 → US2 → US3

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together:
Task: "Unit tests in tests/unit/test_explain_neighborhood.py"
Task: "Unit tests in tests/unit/test_explain_summary.py"
Task: "Contract tests in tests/contract/test_cli_explain.py"
Task: "Integration tests in tests/integration/test_cli_explain_cmd.py"

# Then implement: match.py → explain.py → cli.py
```

## Parallel Example: User Story 2

```bash
# Launch US2 tests together:
Task: "Fuzzy/embedding unit tests in tests/unit/test_match.py"
Task: "Integration approximate/multi-match in tests/integration/test_cli_explain_cmd.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: explain writes subgraph (+ optional summary / `--no-summary`)
5. Demo/ship MVP query command

### Incremental Delivery

1. Setup + Foundational → shared helpers ready
2. US1 → explain CLI + neighborhood + summary (MVP)
3. US2 → fuzzy quality + optional embeddings + top-N
4. US3 → hops, no-match, truncation, LLM-down resilience
5. Polish → quickstart + full suite

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Developer A: US1 explain orchestration + CLI
3. Developer B: US2 match scoring + embeddings (after baseline `select_matches` lands)
4. Then US3 hardening on the shared CLI path

---

## Notes

- [P] tasks = different files, no dependencies on incomplete sibling tasks
- [Story] labels: US1 = explain happy path, US2 = fuzzy/vector matching, US3 = hops/misses/resilience
- Schema stays `6.0.0`; do not bump for additive explain graph metadata
- Injectable `chat_text` / embed callables required for offline unit tests
- Commit after each task or logical group
- Stop at checkpoints to validate stories independently
