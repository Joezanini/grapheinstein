---
description: "Task list for Hybrid Natural-Language Query"
---

# Tasks: Hybrid Natural-Language Query

**Input**: Design documents from `/specs/010-hybrid-query/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — constitution and plan require tests when CLI contracts or portable graph outputs change (`query` subcommand, supporting subgraph metadata, query-answer JSON, provenance preservation on copied edges).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: `src/grapheinstein/`, `tests/` at repository root

## Grapheinstein Task Categories *(when applicable)*

- **Query**: chunk corpus + hybrid expand + cited answer (`core/query.py`; reuse `core/match.py`, `undirected_neighborhood` from `core/explain.py`)
- **Graph**: reuse `load_artifact` / `write_artifact_dict` / `artifact_to_digraph` (`core/graph.py`)
- **Extract/LLM**: reuse `chat_text` + `embed_texts` (`core/parsers/llm_ollama.py`)
- **Config/CLI**: `query` command and `query_*` keys (`cli.py`, `utils.py`)
- **Contracts/tests**: CLI + supporting subgraph + query-answer JSON tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module stub and fixture graphs for hybrid query / chunk-hit scenarios

- [x] T001 [P] Create `src/grapheinstein/core/query.py` stub with module docstring and placeholder public API (`build_chunk_corpus`, `select_chunk_hits`, `build_supporting_subgraph`, `format_visualization_summary`, `generate_cited_answer`, `run_query`, `QueryResult` / `QueryError` / `NoEvidenceError` types) per `plan.md` and `data-model.md`
- [x] T002 [P] Create `tests/fixtures/query_graphs/` with minimal valid schema `6.0.0` JSON graphs: (1) answerable question with `metadata.text` chunks plus related neighbors, (2) composed-text-only graph (code/concept nodes, no media text) still queryable, (3) sparse/noise graph for no-evidence cases, plus brief notes in `tests/fixtures/query_graphs/README.md` documenting questions, expected hit ids, and `--k` expectations per `quickstart.md`

**Checkpoint**: Package still installable; query stub and fixtures in place

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Query config keys and thin helpers that all stories depend on (reuse existing match / neighborhood / chat_text / embed_texts)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Extend `AppConfig` and YAML coercion in `src/grapheinstein/utils.py` with `query_k: int = 20`, `query_hops: int = 1`, `query_match_threshold: float = 0.40`, `query_node_cap: int = 500` per `contracts/cli.md`
- [x] T004 Confirm reuse of `artifact_to_digraph` / `load_artifact` / `write_artifact_dict` in `src/grapheinstein/core/graph.py`, `score_nodes` / `select_matches` / `node_search_text` in `src/grapheinstein/core/match.py`, and `undirected_neighborhood` in `src/grapheinstein/core/explain.py` from query orchestration (import/wrap in `src/grapheinstein/core/query.py` rather than duplicating)
- [x] T005 [P] Add query-answer serialization helper stub in `src/grapheinstein/core/query.py` (`query_answer_to_dict` / JSON dump) matching `contracts/query-answer-json.md` field names (`schema_version`, `question`, `visualization`, `answer`, …) without full hybrid retrieval yet

**Checkpoint**: Foundation ready — query config keys and answer shape helpers available; match/neighborhood/LLM reuse confirmed

---

## Phase 3: User Story 1 - Ask a Plain-Language Question Over a Project Graph (Priority: P1) 🎯 MVP

**Goal**: `grapheinstein query "<question>" --input --output` retrieves evidence, writes a supporting subgraph, emits a visualization summary, and produces a cited local-LLM answer (or skips answer cleanly with `--no-answer`)

**Independent Test**: Run query on `tests/fixtures/query_graphs/` with `--no-answer`; assert schema `6.0.0` subgraph with `query_*` metadata, stdout query-answer JSON, stderr viz summary; with injectable fake `chat_text`, assert cited answer on human stream and in JSON (quickstart Scenarios A, E)

### Tests for User Story 1

- [x] T006 [P] [US1] Add unit tests for supporting-subgraph artifact metadata and visualization summary shape in `tests/unit/test_query_viz.py`
- [x] T007 [P] [US1] Add unit tests for cited-answer generation / citation validation with injectable chat in `tests/unit/test_query_citations.py`
- [x] T008 [P] [US1] Add contract tests for `query` CLI shape (`QUESTION`, `--input`, `--output`, `--k`, `--no-answer`) in `tests/contract/test_cli_query.py`
- [x] T009 [P] [US1] Add integration tests for happy-path query write + stdout answer JSON + `--no-answer` in `tests/integration/test_cli_query_cmd.py`

### Implementation for User Story 1

- [x] T010 [US1] Implement baseline `build_chunk_corpus` + scoring/selection of primary hits (fuzzy via `score_nodes` on corpus texts; default threshold/k) in `src/grapheinstein/core/query.py` sufficient for clear fixture hits per `research.md` R2–R3
- [x] T011 [US1] Implement hybrid expand + supporting subgraph write in `src/grapheinstein/core/query.py`: seeds → `undirected_neighborhood` (default hops 1), induced links preserving `type`/`provenance`/optional attrs, graph metadata (`query_question`, `query_hit_ids`, `query_k`, `query_hops`, fresh `generated_at`) via validate + atomic `write_artifact_dict` per `data-model.md` and `contracts/graph-json.md`
- [x] T012 [US1] Implement `format_visualization_summary` and `generate_cited_answer` in `src/grapheinstein/core/query.py` (deterministic viz counts/types/sample hits; prompt + citation parse/filter against subgraph; Sources fallback when model cites nothing valid) per `research.md` R5–R6
- [x] T013 [US1] Implement `run_query` orchestration in `src/grapheinstein/core/query.py`: load → corpus → hits → expand → write → viz → optional answer via injectable `chat_text` + `check_ready`; return structured `QueryResult` for CLI; build stdout envelope via `query_answer_to_dict`
- [x] T014 [US1] Add `grapheinstein query` command in `src/grapheinstein/cli.py`: add `query` to `_KNOWN_COMMANDS`; positional `QUESTION`; required `--input`/`-i` and `--output`/`-o`; `--no-answer`; wire config/LLM overrides; dump query-answer JSON to **stdout**; print viz summary + human answer on stderr; errors via `_fail`
- [x] T015 [US1] Ensure success path never mixes prose into the subgraph file or stdout JSON envelope, and never leaves a partial corrupt success artifact at `--output` (validate + atomic write only) in `src/grapheinstein/core/query.py` / `src/grapheinstein/cli.py` per `research.md` R1/R7

**Checkpoint**: US1 MVP — query writes a valid supporting subgraph, prints viz summary, and can answer with citations (or `--no-answer`)

---

## Phase 4: User Story 2 - Hybrid Retrieval: Chunk Similarity Plus Graph Context (Priority: P1)

**Goal**: Primary hits prefer native `metadata.text` chunks and expand via graph traversal; optional local embeddings re-rank; embeddings unavailable does not break fuzzy-only query; composed-text graphs remain usable

**Independent Test**: Chunk-rich fixture includes hit nodes and traversed neighbors in subgraph; composed-text-only fixture still retrieves; with fake embeddings, paraphrase re-ranks; with embeddings failing, fuzzy still succeeds and notes skip (quickstart Scenarios A, B)

### Tests for User Story 2

- [x] T016 [P] [US2] Add unit tests for chunk corpus construction (`metadata_text` vs `composed`), thresholding, and `--k` primary-hit capping in `tests/unit/test_query_chunks.py`
- [x] T017 [P] [US2] Add unit tests for hybrid expansion (seeds + undirected hops, induced edges, prefer `metadata_text` tie-break) in `tests/unit/test_query_hybrid.py`
- [x] T018 [P] [US2] Extend integration coverage in `tests/integration/test_cli_query_cmd.py` for embedding soft-skip note, composed-text-only fixture success, and subgraph containing traversed neighbors of primary hits

### Implementation for User Story 2

- [x] T019 [US2] Harden `build_chunk_corpus` in `src/grapheinstein/core/query.py` so nodes with `metadata.text` are preferred (`source=metadata_text`) and other nodes use composed search text; empty corpus fails clearly per `research.md` R2
- [x] T020 [US2] Integrate optional Ollama embeddings into hit ranking in `src/grapheinstein/core/query.py` (reuse match prefilter + `max(fuzzy, embedding)`; single clear skip note when unavailable) per `research.md` R3
- [x] T021 [US2] Ensure hybrid expand records all primary ids in `query_hit_ids` / optional `query_hit_scores` and includes traversed neighbors within hops in `src/grapheinstein/core/query.py` per `research.md` R4
- [x] T022 [US2] Expose `--k` and `--match-threshold` (and config overrides) on `query` in `src/grapheinstein/cli.py` / `src/grapheinstein/utils.py` per `contracts/cli.md`; enforce primary hit count ≤ `k` before expansion (SC-003)

**Checkpoint**: US1 + US2 — hybrid chunk + traversal retrieval with optional vectors

---

## Phase 5: User Story 3 - Control Result Size and Fail Clearly (Priority: P2)

**Goal**: `--k` / `--hops` control breadth; no-evidence and bad input fail clearly without success artifacts; LLM-down still writes subgraph + viz; large expansions truncate with visible flag

**Independent Test**: smaller vs larger `--k` hit counts; nonsense question → non-zero and no output file; invalid `--k`; model unavailable → subgraph + viz + skip message (quickstart Scenarios B, C, D, E-offline)

### Tests for User Story 3

- [x] T023 [P] [US3] Extend unit tests in `tests/unit/test_query_hybrid.py` for hops 1 vs 2, `query_node_cap` truncation (`query_truncated`), and empty-corpus / no-evidence errors
- [x] T024 [P] [US3] Extend contract/integration tests in `tests/contract/test_cli_query.py` and `tests/integration/test_cli_query_cmd.py` for empty question, invalid `--k`, missing/invalid input, no-evidence (no success file / no success stdout JSON), and LLM-unavailable answer skip with exit `0` after write

### Implementation for User Story 3

- [x] T025 [US3] Enforce non-empty question, `--k` ∈ [1, 200], hops ∈ {1, 2}, threshold validation, and no-evidence non-zero exit with **no** success write in `src/grapheinstein/cli.py` / `src/grapheinstein/core/query.py` per `research.md` R1
- [x] T026 [US3] Implement `query_node_cap` truncation (BFS keep seeds, set `graph.query_truncated`, warn on human stream and in viz summary) in `src/grapheinstein/core/query.py` per `research.md` R4
- [x] T027 [US3] Wire `--hops` and ensure LLM-unavailable / `--no-answer` paths still write subgraph + viz and report answer status clearly in `src/grapheinstein/cli.py` / `src/grapheinstein/core/query.py` (reuse `check_ready`; no cloud fallback)
- [x] T028 [US3] Accept gzip inputs via existing `load_artifact` for query in `src/grapheinstein/cli.py` / `src/grapheinstein/core/query.py` (parity with explain/path/merge)

**Checkpoint**: All user stories independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Help text, config coverage, quickstart validation, full suite

- [x] T029 [P] Update CLI help expectations in `tests/contract/test_cli_help.py` so `query` is listed and `query --help` surfaces key options
- [x] T030 [P] Add config unit coverage for `query_k` / `query_hops` / `query_match_threshold` / `query_node_cap` in `tests/unit/test_config.py`
- [x] T031 Run end-to-end validation from `specs/010-hybrid-query/quickstart.md` and fix any gaps in `src/grapheinstein/` or tests
- [x] T032 Run full pytest suite (`tests/unit`, `tests/contract`, `tests/integration`) and fix regressions from query changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **User Story 1 (Phase 3)**: After Foundational — **MVP**
- **User Story 2 (Phase 4)**: After Foundational; soft-depends on US1 corpus/expand/write pipeline
- **User Story 3 (Phase 5)**: After Foundational; soft-depends on US1 CLI/write path
- **Polish (Phase 6)**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no story dependencies — **MVP**
- **US2 (P1)**: Soft-depends on US1 baseline retrieval + subgraph write
- **US3 (P2)**: Soft-depends on US1 CLI/write; hardens validation, truncation, and failure modes

### Within Each User Story

- Tests (listed) SHOULD be written to fail before implementation where practical
- Core helpers before CLI wiring
- Story complete before moving to next priority when staffing is serial

### Parallel Opportunities

- T001–T002 (Setup) in parallel
- T005 can proceed alongside T003/T004 once stub exists
- T006–T009 (US1 tests) in parallel after Foundational
- T016–T018 (US2 tests) in parallel
- T023–T024 (US3 tests) in parallel
- T029–T030 (Polish) in parallel
- Safest serial order: US1 → US2 → US3

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together:
Task: "Unit tests in tests/unit/test_query_viz.py"
Task: "Unit tests in tests/unit/test_query_citations.py"
Task: "Contract tests in tests/contract/test_cli_query.py"
Task: "Integration tests in tests/integration/test_cli_query_cmd.py"

# Then implement: query.py (corpus + subgraph + answer) → cli.py
```

## Parallel Example: User Story 2

```bash
# Launch US2 tests together:
Task: "Chunk corpus tests in tests/unit/test_query_chunks.py"
Task: "Hybrid expand tests in tests/unit/test_query_hybrid.py"
Task: "Integration embedding/composed coverage in tests/integration/test_cli_query_cmd.py"
```

## Parallel Example: User Story 3

```bash
# Launch US3 tests together:
Task: "Truncation/no-evidence unit tests in tests/unit/test_query_hybrid.py"
Task: "Failure-mode contract/integration in tests/contract/test_cli_query.py and tests/integration/test_cli_query_cmd.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `--no-answer` query writes subgraph + viz + stdout JSON; injectable chat proves citations
5. Demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → MVP query loop
3. US2 → hybrid chunk preference + embeddings soft-skip
4. US3 → `--k`/`--hops` validation, truncation, clear failures
5. Polish → help, config tests, quickstart, full suite

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (CLI + orchestration)
   - Developer B: User Story 2 (corpus/hybrid unit depth) after US1 APIs exist
   - Developer C: User Story 3 failure/truncation tests in parallel with care
3. Prefer serial US1 → US2 → US3 if a single implementer

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Reuse `match.py` / `explain.undirected_neighborhood` / `llm_ollama` — do not reintroduce vector DBs or cloud APIs
- Citations MUST be filtered to subgraph entities (FR-013 / SC-002)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same-file conflicts, inventing new node/edge types, embedding persistence in `graph.json`
