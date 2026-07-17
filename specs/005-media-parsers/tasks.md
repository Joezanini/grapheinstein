---
description: "Task list for Media Parsers"
---

# Tasks: Media Parsers

**Input**: Design documents from `/specs/005-media-parsers/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — constitution and plan require tests when `graph.json` schema or CLI contracts change (bump to `5.0.0`, `media_text` / `transcript_chunk` / `related_to`, `--transcribe-media`). Prefer injectable/fake OCR/ASR backends in unit/CI tests; real Tesseract/Whisper covered by quickstart.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: `src/grapheinstein/`, `tests/` at repository root

## Grapheinstein Task Categories *(when applicable)*

- **Ingest/parsers**: image OCR + A/V transcription (`core/parsers/media_ocr.py`, `media_av.py`, `media_link.py`)
- **Graph**: schema `5.0.0` `media_text` / `transcript_chunk` nodes, `section_of` / `related_to` (`core/graph.py`)
- **Index**: wire optional media pass after docs/PDF (`core/index.py`)
- **Config/CLI**: `--transcribe-media`, long-file warnings, `[media]` extras gate (`cli.py`, `pyproject.toml`)
- **Visualize/status**: media node/edge counts (`core/visualize.py`, `cli.py`)
- **Contracts/tests**: CLI + graph schema tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Optional `[media]` dependencies, parser stubs, and fixtures

- [x] T001 Add optional `[media]` extras (`pytesseract`, `Pillow`, `faster-whisper`) to `pyproject.toml` per `research.md` R1–R3
- [x] T002 [P] Create parser stubs `src/grapheinstein/core/parsers/media_ocr.py`, `src/grapheinstein/core/parsers/media_av.py`, and `src/grapheinstein/core/parsers/media_link.py` with module docstrings and placeholder public functions per `plan.md`
- [x] T003 [P] Create `tests/fixtures/media_project/` with `src/login.py`, `docs/install.md`, `assets/login.png` (text-bearing), `assets/blank.png`, `demos/setup.wav` (or short speech fixture), `demos/corrupt.mp3`, oversized/long stub for warn tests, `.gitignore` excluding `ignored_media/`, `ignored_media/secret.png`, and notes in `tests/fixtures/media_project/README.md`
- [x] T004 [P] Add sample schema `4.0.0` graph fixture at `tests/fixtures/old_schema_v4_graph.json` for rejection tests

**Checkpoint**: Package still installable (`pip install -e ".[dev]"`); fixtures and stubs in place

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema `5.0.0` graph primitives, media helpers, and baseline suite migration shared by all stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Bump NetworkX build/save/load in `src/grapheinstein/core/graph.py` to `schema_version` `5.0.0`; extend node allow-list with `media_text`|`transcript_chunk` and edge allow-list with `related_to` per `contracts/graph-json.md` and `data-model.md`
- [x] T006 Implement helpers in `src/grapheinstein/core/graph.py` to add `media_text` / `transcript_chunk` nodes (id patterns + required metadata) and `section_of` containment edges with `provenance: extracted`
- [x] T007 Implement `add_related_to_edge` (or equivalent) in `src/grapheinstein/core/graph.py` that writes `type: related_to` with `provenance: inferred` (extend `_add_typed_edge` or add provenance-aware helper so inferred is not forced to extracted)
- [x] T008 Update strict load validation in `src/grapheinstein/core/graph.py` to accept only `5.0.0`, reject `4.0.0`/older with clear unsupported-format / re-index error, and validate media node metadata (`file`, `text`, `source`; transcript also `start_sec`/`end_sec`)
- [x] T009 Extend `GraphStats` / `stats_from_artifact` in `src/grapheinstein/core/graph.py` to count `media_text`, `transcript_chunk`, and `related_to` (retain inventory + code + heading counts)
- [x] T010 Update `status` / visualize load paths in `src/grapheinstein/cli.py` and `src/grapheinstein/core/visualize.py` to use v5 stats and fail clearly on schema `4.0.0` graphs
- [x] T011 Update existing suite expectations that hard-code `schema_version` `4.0.0` in `tests/contract/`, `tests/unit/`, and `tests/integration/` so baseline tests assert `5.0.0` inventory/code/docs/PDF still work before media extract is wired

**Checkpoint**: Foundation ready — v5 graph round-trip, old schemas rejected, media helpers available

---

## Phase 3: User Story 1 - Index Images via OCR Text (Priority: P1) 🎯 MVP

**Goal**: With `--transcribe-media`, offline OCR produces `media_text` nodes + `section_of` (`extracted`) for images; flag off adds none

**Independent Test**: Index `tests/fixtures/media_project` with `--transcribe-media` → `media_text` for `assets/login.png`, none for `blank.png`, ignored `secret.png` absent; without flag no OCR nodes (quickstart Scenarios A–B OCR portion)

### Tests for User Story 1

- [x] T012 [P] [US1] Add unit tests for `media_text` id/metadata and `section_of` helpers in `tests/unit/test_graph_media_entities.py`
- [x] T013 [P] [US1] Add unit tests for image OCR extract (injectable/fake engine: text vs empty vs failure) in `tests/unit/test_media_ocr.py`
- [x] T014 [P] [US1] Add contract tests for schema `5.0.0` `media_text` nodes and `section_of` provenance in `tests/contract/test_graph_json_v5.py`
- [x] T015 [P] [US1] Add integration test that `index --transcribe-media` OCR path writes expected `media_text` / skips ignored images in `tests/integration/test_cli_index_media_ocr.py` (stub OCR if needed)

### Implementation for User Story 1

- [x] T016 [US1] Implement lazy-import OCR path and image extension filter in `src/grapheinstein/core/parsers/media_ocr.py` per `research.md` R1/R9 (Pillow + pytesseract; empty text → no node; decode/OCR errors → warn + skip)
- [x] T017 [US1] Expose OCR merge entrypoint (e.g. `merge_media_ocr`) from `src/grapheinstein/core/parsers/media_ocr.py` that merges into an existing DiGraph and returns skip count
- [x] T018 [US1] Add `--transcribe-media` boolean flag to `index` (and default-path alias) in `src/grapheinstein/cli.py`; ensure it is **not** listed in `_OPTS_WITH_VALUE`; pass through to `index_project`
- [x] T019 [US1] Implement `[media]` import gate in `src/grapheinstein/core/index.py` (or small helper module): when `transcribe_media` is true and extras missing → raise clear error for CLI exit 1 before success write
- [x] T020 [US1] Wire OCR pass into `src/grapheinstein/core/index.py` after docs/PDF when `transcribe_media` is true; set `graph.graph["transcribe_media"]`; respect ignore rules; accumulate parse skips
- [x] T021 [US1] Update index success summary in `src/grapheinstein/cli.py` to report `media_text` (and later chunk/`related_to`) counts
- [x] T022 [US1] Update visualize summary/DOT in `src/grapheinstein/core/visualize.py` to include `media_text` without crashing

**Checkpoint**: US1 MVP complete — `--transcribe-media` produces schema `5.0.0` digraph with OCR text nodes

---

## Phase 4: User Story 2 - Transcribe Audio and Video into Chunked Nodes (Priority: P1)

**Goal**: With `--transcribe-media`, local faster-whisper transcription yields `transcript_chunk` nodes + `section_of` (`extracted`); corrupt A/V does not abort index

**Independent Test**: Index with `--transcribe-media` → one or more `transcript_chunk` for short speech fixture with `start_sec`/`end_sec`; `corrupt.mp3` skipped with warning; exit 0 (quickstart Scenario B A/V portion)

### Tests for User Story 2

- [x] T023 [P] [US2] Add unit tests for segment→chunk merge policy (R8) and timed metadata in `tests/unit/test_media_av_chunk.py`
- [x] T024 [P] [US2] Add unit tests for A/V transcription failure handling with injectable/fake Whisper backend in `tests/unit/test_media_av.py`
- [x] T025 [P] [US2] Extend contract tests for `transcript_chunk` nodes and `section_of` in `tests/contract/test_graph_json_v5.py`
- [x] T026 [P] [US2] Add integration test that `index --transcribe-media` writes transcript chunks and skips corrupt A/V in `tests/integration/test_cli_index_media_av.py` (stub ASR if needed)

### Implementation for User Story 2

- [x] T027 [US2] Implement lazy-import faster-whisper transcription and A/V extension filter in `src/grapheinstein/core/parsers/media_av.py` per `research.md` R2/R8/R9 (`base` model, CPU; empty speech → no chunks)
- [x] T028 [US2] Implement segment merge → `transcript_chunk` nodes + `section_of` to file in `src/grapheinstein/core/parsers/media_av.py`; return skip count
- [x] T029 [US2] Wire A/V pass into `src/grapheinstein/core/index.py` after OCR within the `transcribe_media` block; accumulate parse skips; ensure per-file exceptions do not abort index
- [x] T030 [US2] Update index/visualize summaries in `src/grapheinstein/cli.py` and `src/grapheinstein/core/visualize.py` to include `transcript_chunk` counts

**Checkpoint**: US1 + US2 — OCR and A/V enrichment both work behind `--transcribe-media`

---

## Phase 5: User Story 3 - Link Media to Related Code and Docs (Priority: P2)

**Goal**: After media text exists, create unambiguous `related_to` edges (`inferred`) via filename similarity and/or content overlap

**Independent Test**: Fixture where `login.png` uniquely pairs with `login.py` → at least one `related_to` with `provenance: inferred`; ambiguous multi-match fixture skips (quickstart Scenario C)

### Tests for User Story 3

- [x] T031 [P] [US3] Add unit tests for unambiguous stem/basename media→file matching and ambiguous skip in `tests/unit/test_media_link_filename.py`
- [x] T032 [P] [US3] Add unit tests for content-overlap linking (unique hit / no hit / ambiguous) in `tests/unit/test_media_link_content.py`
- [x] T033 [P] [US3] Extend contract tests asserting `related_to` requires `provenance: inferred` in `tests/contract/test_graph_json_v5.py`
- [x] T034 [P] [US3] Add integration test for `related_to` edges after `--transcribe-media` on `media_project` in `tests/integration/test_cli_index_media_link.py`

### Implementation for User Story 3

- [x] T035 [US3] Implement filename-similarity linker (unique stem/basename only) in `src/grapheinstein/core/parsers/media_link.py` per `research.md` R6
- [x] T036 [US3] Implement conservative lexical content-overlap linker in `src/grapheinstein/core/parsers/media_link.py` (local only; no cloud embeddings)
- [x] T037 [US3] Expose merge entrypoint (e.g. `merge_media_links`) that emits `related_to` via graph helpers and skips ambiguous targets
- [x] T038 [US3] Wire linking pass into `src/grapheinstein/core/index.py` after OCR/A/V when `transcribe_media` is true; do not run when flag is false
- [x] T039 [US3] Update index/visualize summaries in `src/grapheinstein/cli.py` and `src/grapheinstein/core/visualize.py` to include `related_to` counts

**Checkpoint**: US3 — inferred media↔code/docs links present and filterable by provenance

---

## Phase 6: User Story 4 - Opt In with --transcribe-media and Warn on Long Files (Priority: P1)

**Goal**: Flag off skips all media enrichment; long files warn-and-continue; missing `[media]` extras fail closed when flag is set; default-path alias preserves the flag

**Independent Test**: Flag matrix + long-file warning + missing-extras exit match quickstart Scenarios A, D, E, F

### Tests for User Story 4

- [x] T040 [P] [US4] Add integration tests for flag off vs on (no media nodes when off; OCR+A/V+links when on) and default-path alias in `tests/integration/test_cli_transcribe_media_flag.py`
- [x] T041 [P] [US4] Add unit/integration tests that oversized/long media emit a warning naming the path without failing the run in `tests/unit/test_media_long_file_warn.py` (and/or integration companion)
- [x] T042 [P] [US4] Add CLI/contract test that `--transcribe-media` without importable extras exits non-zero with install hint in `tests/integration/test_cli_media_extras_missing.py`
- [x] T043 [P] [US4] Assert `graph.transcribe_media` metadata true/false on schema `5.0.0` artifacts in `tests/contract/test_graph_json_v5.py`

### Implementation for User Story 4

- [x] T044 [US4] Implement long-file threshold checks (100 MB and/or 600 s when duration known) and stderr/log warnings in `src/grapheinstein/core/parsers/media_av.py` (and size check for large images in `media_ocr.py` if applicable) per `research.md` R7
- [x] T045 [US4] Harden `prepend_index_if_needed` in `src/grapheinstein/cli.py` so `--transcribe-media` never consumes the project path as an option value
- [x] T046 [US4] Persist boolean `transcribe_media` on `graph.graph` for every successful index run in `src/grapheinstein/core/index.py` (explicit false when off)
- [x] T047 [US4] Ensure flag-off path skips OCR, A/V, and linking while still writing schema `5.0.0` inventory + prior modalities in `src/grapheinstein/core/index.py`
- [x] T048 [US4] Surface missing-extras errors clearly on CLI stderr in `src/grapheinstein/cli.py` (exit code 1; no success graph claiming media ran)

**Checkpoint**: All four stories — opt-in flag, warnings, and extras gate match CLI/graph contracts

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Cross-story validation and suite hygiene

- [x] T049 [P] Add/extend unit tests for visualize/status media counts in `tests/unit/test_visualize_summary.py` (v5 expectations)
- [x] T050 [P] Ensure `tests/contract/` rejects `old_schema_v4_graph.json` with re-index messaging in `tests/contract/test_graph_json_v5.py`
- [x] T051 Run full pytest suite and fix regressions from schema bump across `tests/`
- [x] T052 Run manual validation scenarios from `specs/005-media-parsers/quickstart.md` (A–F) and fix any gaps

**Checkpoint**: Feature ready for `/speckit-implement` completion criteria

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP (OCR + flag + extras gate skeleton)
- **User Story 2 (Phase 4)**: Depends on Foundational; best after US1 flag/`index.py` wiring exists (shared files)
- **User Story 3 (Phase 5)**: Depends on US1 and/or US2 producing media text nodes (linking needs content)
- **User Story 4 (Phase 6)**: Depends on US1–US3 flag/media paths present (validates matrix, warnings, extras)
- **Polish (Phase 7)**: Depends on desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — introduces `--transcribe-media` + OCR
- **US2 (P1)**: After US1 wiring preferred — adds A/V under same flag; independently testable with stubbed ASR
- **US3 (P2)**: After US1 (OCR text) minimum; fuller with US2 chunks
- **US4 (P1)**: After US1–US3 — flag matrix / long-file warn / missing extras / alias hardening

### Within Each User Story

- Tests marked first SHOULD fail before implementation where practical
- Parser merge before index wiring
- CLI flag with US1 before modality expansion
- Story checkpoint before moving on

### Parallel Opportunities

- T002–T004 in Setup
- T012–T015 tests in US1
- T023–T026 tests in US2 while US1 implementation finishes (different test files)
- T031–T034 tests in US3 once media nodes exist
- T040–T043 tests in US4 once flag exists
- T049–T050 in Polish

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together:
Task: "Unit tests for media_text helpers in tests/unit/test_graph_media_entities.py"
Task: "Unit tests for OCR extract in tests/unit/test_media_ocr.py"
Task: "Contract tests schema 5.0.0 in tests/contract/test_graph_json_v5.py"
Task: "Integration test OCR index in tests/integration/test_cli_index_media_ocr.py"
```

## Parallel Example: User Story 2

```bash
# Launch US2 tests together:
Task: "Unit tests chunk merge in tests/unit/test_media_av_chunk.py"
Task: "Unit tests A/V failure handling in tests/unit/test_media_av.py"
Task: "Extend contract transcript_chunk in tests/contract/test_graph_json_v5.py"
Task: "Integration test A/V index in tests/integration/test_cli_index_media_av.py"
```

## Parallel Example: User Story 3

```bash
# Launch US3 tests together:
Task: "Unit tests filename linking in tests/unit/test_media_link_filename.py"
Task: "Unit tests content linking in tests/unit/test_media_link_content.py"
Task: "Contract related_to inferred in tests/contract/test_graph_json_v5.py"
Task: "Integration test media link in tests/integration/test_cli_index_media_link.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (OCR + `--transcribe-media`)
4. **STOP and VALIDATE**: Independent OCR index test / quickstart A–B (images)
5. Demo portable schema `5.0.0` graph with `media_text` nodes

### Incremental Delivery

1. Setup + Foundational → v5 foundation ready
2. US1 → OCR MVP behind `--transcribe-media`
3. US2 → A/V chunks behind same flag
4. US3 → inferred `related_to` links
5. US4 → long-file warn, extras gate hardening, flag matrix
6. Polish → full suite + quickstart A–F

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. After Foundational:
   - Developer A: US1 (OCR + CLI flag)
   - Developer B: US2 tests + `media_av.py` (merge carefully on `index.py`)
3. US3 after media text exists; US4 last for cross-cutting flag/warn/extras

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing where practical
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same-file conflicts without coordination, cloud OCR/ASR, always-on media parsing
- System deps (Tesseract, ffmpeg) are documented in quickstart; CI should stub engines rather than requiring GPU/model downloads
