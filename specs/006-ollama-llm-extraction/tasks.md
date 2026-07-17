---
description: "Task list for Local LLM Entity & Relation Extraction"
---

# Tasks: Local LLM Entity & Relation Extraction

**Input**: Design documents from `/specs/006-ollama-llm-extraction/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — constitution and plan require tests when `graph.json` schema or CLI contracts change (bump to `6.0.0`, `concept` / `implements` / `depends_on`, `--enrich-llm`). Prefer injectable/fake Ollama chat backends in unit/CI tests; real Ollama covered by quickstart.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: `src/grapheinstein/`, `tests/` at repository root

## Grapheinstein Task Categories *(when applicable)*

- **Extract**: Ollama client + LLM enrich merge (`core/parsers/llm_ollama.py`, `llm_enrich.py`)
- **Graph**: schema `6.0.0` `concept` nodes, `implements` / `depends_on` / enrichment `mentions` with `confidence` + `evidence` (`core/graph.py`)
- **Index**: wire optional LLM pass after media (`core/index.py`)
- **Config/CLI**: `--enrich-llm`, `--llm-model`, `--llm-base-url`, YAML `llm_*` keys (`cli.py`, `utils.py`)
- **Visualize/status**: concept / implements / depends_on counts (`core/visualize.py`, `cli.py`)
- **Contracts/tests**: CLI + graph schema tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Parser stubs, LLM fixture project, and old-schema rejection fixture

- [x] T001 [P] Create parser stubs `src/grapheinstein/core/parsers/llm_ollama.py` and `src/grapheinstein/core/parsers/llm_enrich.py` with module docstrings and placeholder public functions per `plan.md`
- [x] T002 [P] Create `tests/fixtures/llm_project/` with `src/auth.py` (define `validate_token`, optional jwt/PyJWT mention), `docs/auth.md` (literal `Auth Middleware` + validation description), `.gitignore` excluding `ignored/`, `ignored/secret.md`, and notes in `tests/fixtures/llm_project/README.md` per `quickstart.md`
- [x] T003 [P] Add sample schema `5.0.0` graph fixture at `tests/fixtures/old_schema_v5_graph.json` for rejection tests (minimal valid v5 envelope)

**Checkpoint**: Package still installable (`pip install -e ".[dev]"`); fixtures and stubs in place

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema `6.0.0` graph primitives, concept/enrichment edge helpers, config fields, and baseline suite migration shared by all stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Bump NetworkX build/save/load in `src/grapheinstein/core/graph.py` to `schema_version` `6.0.0`; extend node allow-list with `concept` and edge allow-list with `implements`|`depends_on` per `contracts/graph-json.md` and `data-model.md`
- [x] T005 Implement concept node helper(s) in `src/grapheinstein/core/graph.py` (`concept::{slug}` id, required `metadata.name`, optional `kind`/`aliases`) with deterministic slug normalization per `research.md` R5
- [x] T006 Extend edge serialization/load in `src/grapheinstein/core/graph.py` to round-trip optional `confidence` and `evidence` on links; validate when present (`confidence` ∈ `[0.0, 1.0]`, non-empty `evidence`)
- [x] T007 Implement enrichment edge helpers in `src/grapheinstein/core/graph.py` for `implements` (`inferred`), `depends_on` (`inferred`), and enrichment `mentions`→concept (`extracted`) that **require** `confidence` + `evidence` (extend `_add_typed_edge` or add provenance-aware helper)
- [x] T008 Update strict load validation in `src/grapheinstein/core/graph.py` to accept only `6.0.0`, reject `5.0.0`/older with clear unsupported-format / re-index error, and require `confidence`+`evidence` on `implements`/`depends_on` edges
- [x] T009 Extend `GraphStats` / `stats_from_artifact` in `src/grapheinstein/core/graph.py` to count `concept`, `implements`, and `depends_on` (retain inventory + code + docs + media counts)
- [x] T010 Extend `AppConfig` and YAML coercion in `src/grapheinstein/utils.py` with `llm_model` (default `qwen3.5-2b-mlx:fp16-8gbGPU`), `llm_base_url` (default `http://localhost:11434`), and `llm_confidence_threshold` (default `0.5`) per `contracts/cli.md`
- [x] T011 Update `status` / visualize load paths in `src/grapheinstein/cli.py` and `src/grapheinstein/core/visualize.py` to use v6 stats and fail clearly on schema `5.0.0` graphs
- [x] T012 Update existing suite expectations that hard-code `schema_version` `5.0.0` in `tests/contract/`, `tests/unit/`, and `tests/integration/` so baseline tests assert `6.0.0` inventory/code/docs/PDF/media still work before LLM enrich is wired

**Checkpoint**: Foundation ready — v6 graph round-trip, old schemas rejected, concept/enrichment helpers and config fields available

---

## Phase 3: User Story 1 - Enrich Index with Local LLM Concepts and Relations (Priority: P1) 🎯 MVP

**Goal**: With `--enrich-llm` and a usable injectable/local model, enrichment adds `concept` nodes and typed relations while retaining AST functions; flag off adds none

**Independent Test**: Index `tests/fixtures/llm_project` with `--include-docs --enrich-llm` and a fake LLM returning Auth Middleware + implements → concept node + relation; without flag no concepts (quickstart Scenarios A–B core)

### Tests for User Story 1

- [x] T013 [P] [US1] Add unit tests for concept id/slug helpers and enrichment edge helpers in `tests/unit/test_graph_llm_entities.py`
- [x] T014 [P] [US1] Add unit tests for LLM response parse → entities/relations merge (injectable fake chat) in `tests/unit/test_llm_enrich.py`
- [x] T015 [P] [US1] Add contract tests for schema `6.0.0` `concept` nodes and enrichment edge shapes in `tests/contract/test_graph_json_v6.py`
- [x] T016 [P] [US1] Add integration test that `index --enrich-llm` writes expected concepts/relations with injectable LLM and skips ignored files in `tests/integration/test_cli_index_llm_enrich.py`

### Implementation for User Story 1

- [x] T017 [US1] Implement Ollama HTTP client in `src/grapheinstein/core/parsers/llm_ollama.py`: `list_models` / tags check and `chat` with `stream=false` + structured `format` via stdlib `urllib` per `research.md` R1/R8 (injectable for tests)
- [x] T018 [US1] Implement chunk build, prompt/schema parse, concept upsert, and relation merge in `src/grapheinstein/core/parsers/llm_enrich.py` (`merge_llm_enrichment`); do not create AST function/class/method nodes; resolve in-file symbols when possible; respect truncate budget + warn per R7
- [x] T019 [US1] Add `--enrich-llm` boolean flag to `index` (and default-path alias) in `src/grapheinstein/cli.py`; ensure value-bearing LLM options are listed in `_OPTS_WITH_VALUE`; pass `enrich_llm` through to `index_project`
- [x] T020 [US1] Wire LLM enrichment pass into `src/grapheinstein/core/index.py` after media when `enrich_llm` is true; set `graph.graph["enrich_llm"]` and `graph.graph["llm_model"]`; call injectable `llm_chat=` / client; respect ignore rules; accumulate skips
- [x] T021 [US1] Update index success summary in `src/grapheinstein/cli.py` to report `concept`, `implements`, and `depends_on` counts
- [x] T022 [US1] Update visualize summary/DOT in `src/grapheinstein/core/visualize.py` to include `concept` / enrichment edge counts without crashing

**Checkpoint**: US1 MVP complete — `--enrich-llm` produces schema `6.0.0` digraph with concepts and relations (via fake or live Ollama)

---

## Phase 4: User Story 2 - Provenance, Confidence, and Evidence on Every New Edge (Priority: P1)

**Goal**: Every enrichment edge has `provenance`, `confidence`, and grounded `evidence`; low-confidence and ungrounded suggestions are dropped; AST edges stay `extracted` without requiring new attrs

**Independent Test**: After enriched index (fake LLM), all enrichment edges pass contract fields; below-threshold and bad-evidence relations omitted; filter `extracted` excludes `implements`/`depends_on` (quickstart Scenario D)

### Tests for User Story 2

- [x] T023 [P] [US2] Add unit tests for confidence threshold filtering (inclusive `>=`) and evidence grounding checks in `tests/unit/test_llm_enrich_filter.py`
- [x] T024 [P] [US2] Extend contract tests in `tests/contract/test_graph_json_v6.py` asserting enrichment edges always include `provenance` + `confidence` + `evidence`, and `implements`/`depends_on` are `inferred`
- [x] T025 [P] [US2] Add integration assertion in `tests/integration/test_cli_index_llm_enrich.py` (or new file) that low-confidence fake responses produce no kept enrichment edges

### Implementation for User Story 2

- [x] T026 [US2] Enforce evidence grounding (substring / whitespace-normalized excerpt ≤ 240 chars) and drop ungrounded suggestions in `src/grapheinstein/core/parsers/llm_enrich.py` per `research.md` R6
- [x] T027 [US2] Apply `llm_confidence_threshold` (default `0.5`, inclusive keep) when merging relations in `src/grapheinstein/core/parsers/llm_enrich.py`; plumb threshold from `index_project` / config
- [x] T028 [US2] Ensure load/save path in `src/grapheinstein/core/graph.py` rejects `implements`/`depends_on` missing `confidence` or `evidence`; keep legacy edges without those fields valid

**Checkpoint**: US1 + US2 — enrichment edges are trustworthy and filterable by provenance/confidence

---

## Phase 5: User Story 3 - Configure Local Model Name and Fall Back Gracefully (Priority: P1)

**Goal**: Users set model/base URL via CLI/config; missing Ollama or model skips enrichment with a clear warning and still writes a valid structural graph; no cloud fallback

**Independent Test**: Index with `--llm-model` override used by client; missing model tag → warning + structural `6.0.0` graph, exit 0 (quickstart Scenario C)

### Tests for User Story 3

- [x] T029 [P] [US3] Add unit tests for model availability check / skip decision in `tests/unit/test_llm_ollama.py` (fake tags list, unreachable base URL)
- [x] T030 [P] [US3] Add unit/config tests for `llm_model`, `llm_base_url`, `llm_confidence_threshold` YAML + CLI precedence in `tests/unit/test_config.py` (or `tests/unit/test_llm_config.py`)
- [x] T031 [P] [US3] Add integration test that missing model skips enrichment and still writes schema `6.0.0` structural graph in `tests/integration/test_cli_index_llm_skip.py`

### Implementation for User Story 3

- [x] T032 [US3] Add `--llm-model` and `--llm-base-url` options to `index` (and default-path alias) in `src/grapheinstein/cli.py`; wire into `_OPTS_WITH_VALUE` and config precedence with `AppConfig`
- [x] T033 [US3] Implement preflight in `src/grapheinstein/core/parsers/llm_ollama.py` / `src/grapheinstein/core/index.py`: if Ollama unreachable or configured model not in tags → log clear warning, skip enrichment (zero successful cloud calls), continue index write
- [x] T034 [US3] Persist attempted/used `graph.llm_model` and `graph.enrich_llm` metadata in `src/grapheinstein/core/index.py` / `src/grapheinstein/core/graph.py` serialization per `data-model.md`

**Checkpoint**: US1–US3 — configurable local model with graceful skip

---

## Phase 6: User Story 4 - Pipeline Integration Without Breaking Existing Index (Priority: P2)

**Goal**: LLM stage sits after structural/modality parsers; prior edges retained; per-chunk failures do not abort; progress visible on long runs

**Independent Test**: Multi-file fixture with one bad chunk response → other chunks enriched, prior `contains`/`defines`/docs edges present, progress logged (quickstart multi-chunk + Scenario A retention)

### Tests for User Story 4

- [x] T035 [P] [US4] Add unit test that one failing chunk does not stop enrichment of subsequent chunks in `tests/unit/test_llm_enrich_partial.py`
- [x] T036 [P] [US4] Add integration test that enriched index retains inventory/code/docs edges alongside concepts in `tests/integration/test_cli_index_llm_pipeline.py`
- [x] T037 [P] [US4] Extend schema rejection test using `tests/fixtures/old_schema_v5_graph.json` in `tests/contract/test_graph_json_v6.py` or `tests/integration/test_cli_status.py`

### Implementation for User Story 4

- [x] T038 [US4] Ensure pipeline order in `src/grapheinstein/core/index.py` runs LLM enrichment only after inventory/references/code/docs/PDF/media merges; without `--enrich-llm` make zero HTTP calls
- [x] T039 [US4] Add periodic enrichment progress logging (per file or every N chunks) on the human-readable stream in `src/grapheinstein/core/parsers/llm_enrich.py` / `src/grapheinstein/core/index.py`
- [x] T040 [US4] Confirm per-chunk exception handling warns, increments skips, and continues in `src/grapheinstein/core/parsers/llm_enrich.py`; do not abort whole index for one bad response
- [x] T041 [US4] Verify index overwrite semantics and success summary/visualize remain consistent when enrichment adds zero concepts in `src/grapheinstein/cli.py` and `src/grapheinstein/core/visualize.py`

**Checkpoint**: Full feature — LLM enrichment integrated without breaking prior modalities

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation alignment and end-to-end quickstart validation

- [x] T042 [P] Align README or inline CLI help text for `--enrich-llm` / `--llm-model` / `--llm-base-url` with `specs/006-ollama-llm-extraction/contracts/cli.md` (update `src/grapheinstein/cli.py` help strings; README only if one already documents index flags)
- [x] T043 [P] Add/adjust CLI help contract coverage for new flags in `tests/contract/test_cli_help.py`
- [x] T044 Run manual validation scenarios from `specs/006-ollama-llm-extraction/quickstart.md` (A–E) and fix any gaps discovered
- [x] T045 Run full pytest suite (`pytest`) and fix regressions from schema `6.0.0` migration

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP
- **User Story 2 (Phase 4)**: Depends on Foundational; builds on US1 enrich merge (filter/validate path)
- **User Story 3 (Phase 5)**: Depends on Foundational; integrates with US1 client/index wire for preflight skip
- **User Story 4 (Phase 6)**: Depends on US1 pipeline wire; hardening + retention
- **Polish (Phase 7)**: Depends on desired stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: After Foundational — core enrich path (MVP)
- **User Story 2 (P1)**: After US1 merge exists — confidence/evidence filtering
- **User Story 3 (P1)**: After US1 client/index stubs — config + graceful skip (can overlap US2 on different files)
- **User Story 4 (P2)**: After US1 index wire — progress, partial failure, retention

### Within Each User Story

- Tests (if included) SHOULD be written and fail before implementation where practical
- Graph helpers / client before merge wiring
- Merge before CLI flag integration
- Story complete before moving to next priority when sequential

### Parallel Opportunities

- T001–T003 setup tasks marked [P]
- T013–T016 US1 tests marked [P]
- T023–T025 US2 tests marked [P]
- T029–T031 US3 tests marked [P]
- T035–T037 US4 tests marked [P]
- T042–T043 polish docs/help marked [P]
- After Foundational, US2 filter work and US3 config/preflight can proceed in parallel on different files if US1 client+merge stubs exist

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together:
Task: "Unit tests for concept helpers in tests/unit/test_graph_llm_entities.py"
Task: "Unit tests for enrich merge in tests/unit/test_llm_enrich.py"
Task: "Contract tests in tests/contract/test_graph_json_v6.py"
Task: "Integration test in tests/integration/test_cli_index_llm_enrich.py"

# Then implement client → enrich → CLI → index wire sequentially (T017–T020)
```

---

## Parallel Example: User Story 3

```bash
# Launch US3 tests together:
Task: "Unit tests in tests/unit/test_llm_ollama.py"
Task: "Config tests for llm_* keys"
Task: "Integration skip test in tests/integration/test_cli_index_llm_skip.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `--enrich-llm` with fake LLM produces concepts/relations on `llm_project`
5. Demo/ship MVP if ready

### Incremental Delivery

1. Setup + Foundational → v6 foundation ready
2. Add US1 → concepts/relations MVP
3. Add US2 → confidence/evidence trust filters
4. Add US3 → configurable model + graceful skip
5. Add US4 → pipeline hardening + progress
6. Polish → quickstart + full suite green

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Once Foundational + US1 merge stubs exist:
   - Developer A: US2 filtering
   - Developer B: US3 config/preflight
   - Developer C: US4 progress/partial failure
3. Integrate and run quickstart

---

## Notes

- [P] tasks = different files, no dependencies on incomplete siblings
- [Story] label maps task to US1–US4 for traceability
- Do not silently auto-select a different Ollama model when the configured tag is missing
- Prefer injectable `llm_chat` / fake tags in CI; live Ollama is for quickstart
- Commit after each task or logical group
- Avoid: vague tasks, same-file conflicts, cloud LLM defaults
