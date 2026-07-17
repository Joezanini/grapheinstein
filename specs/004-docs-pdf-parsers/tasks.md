---
description: "Task list for Docs and PDF Parsers"
---

# Tasks: Docs and PDF Parsers

**Input**: Design documents from `/specs/004-docs-pdf-parsers/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — constitution and plan require tests when `graph.json` schema or CLI contracts change (bump to `4.0.0`, `heading` / `section_of` / `mentions`, `--include-docs` / `--include-pdfs`).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: `src/grapheinstein/`, `tests/` at repository root

## Grapheinstein Task Categories *(when applicable)*

- **Ingest/parsers**: Markdown/TXT/RST + PDF (`core/parsers/docs.py`, `pdf.py`, `resolve_docs.py`)
- **Graph**: schema `4.0.0` heading nodes, `section_of` / `mentions` (`core/graph.py`)
- **Index**: wire optional docs/PDF passes after code extract (`core/index.py`)
- **Config/CLI**: `--include-docs` / `--include-pdfs` (`cli.py`)
- **Visualize/status**: heading and new edge counts (`core/visualize.py`, `cli.py`)
- **Contracts/tests**: CLI + graph schema tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add PyMuPDF dependency, docs/PDF parser stubs, and fixtures

- [x] T001 Add `pymupdf` to `pyproject.toml` dependencies per `research.md` R1
- [x] T002 [P] Create parser stubs `src/grapheinstein/core/parsers/docs.py`, `src/grapheinstein/core/parsers/pdf.py`, and `src/grapheinstein/core/parsers/resolve_docs.py` with module docstrings and placeholder public functions per plan.md structure
- [x] T003 [P] Create `tests/fixtures/docs_pdf_project/` with `README.md`, nested `docs/guide.md` (headings + link to README), `docs/notes.txt`, `docs/overview.rst`, `manuals/sample.pdf` (multi-section), `manuals/corrupt.pdf` (invalid bytes), `.gitignore` excluding `ignored_docs/`, `ignored_docs/secret.md`, and expected heading notes in `tests/fixtures/docs_pdf_project/README.md`
- [x] T004 [P] Add sample schema `3.0.0` graph fixture at `tests/fixtures/old_schema_v3_graph.json` for rejection tests

**Checkpoint**: Package still installable after dependency edit; fixtures and stubs in place

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema `4.0.0` graph primitives, heading helpers, and baseline suite migration shared by all stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Bump NetworkX build/save/load in `src/grapheinstein/core/graph.py` to `schema_version` `4.0.0`; extend node allow-list with `heading` and edge allow-list with `section_of`|`mentions` per `contracts/graph-json.md` and `data-model.md`
- [x] T006 Implement helpers in `src/grapheinstein/core/graph.py` to add heading nodes (`{file}::heading::{slug}::{locator}` + required metadata) and `section_of`/`mentions` edges with `provenance: extracted`
- [x] T007 Update strict load validation in `src/grapheinstein/core/graph.py` to accept only `4.0.0`, reject `3.0.0`/older with clear unsupported-format / re-index error, and validate heading metadata keys (`name`, `file`, `source`, plus `start_line` and/or `page`)
- [x] T008 Extend `GraphStats` / `stats_from_artifact` in `src/grapheinstein/core/graph.py` to count heading nodes and `section_of`/`mentions` edges (retain existing inventory + code counts)
- [x] T009 Update `status` / visualize load paths in `src/grapheinstein/cli.py` and `src/grapheinstein/core/visualize.py` to use v4 stats and fail clearly on schema `3.0.0` graphs
- [x] T010 Update existing suite expectations that hard-code `schema_version` `3.0.0` in `tests/contract/`, `tests/unit/`, and `tests/integration/` so baseline tests assert `4.0.0` inventory/code still works before docs/PDF extract is wired

**Checkpoint**: Foundation ready — v4 graph round-trip, old schemas rejected, heading helpers available

---

## Phase 3: User Story 1 - Index Documentation Structure (Priority: P1) 🎯 MVP

**Goal**: With docs inclusion enabled, index adds `heading` nodes and `section_of` / `mentions` edges (`extracted`) from Markdown, TXT, and RST

**Independent Test**: Index `tests/fixtures/docs_pdf_project` with `--include-docs` → nested headings + `section_of` for `guide.md`/`notes.txt`/`overview.rst`; resolvable Markdown `mentions` to `README.md`; ignored `secret.md` absent; all new edges `extracted` (quickstart Scenario B)

### Tests for User Story 1

- [x] T011 [P] [US1] Add unit tests for heading id/slug/metadata and `section_of`/`mentions` helpers in `tests/unit/test_graph_heading_entities.py`
- [x] T012 [P] [US1] Add unit tests for Markdown/TXT/RST heading + link extraction in `tests/unit/test_docs_extract.py`
- [x] T013 [P] [US1] Add unit tests for docs link resolution (unique hit, ambiguous skip, unresolved omit) in `tests/unit/test_resolve_docs.py`
- [x] T014 [P] [US1] Add contract tests for schema `4.0.0` heading nodes and `section_of`/`mentions` links/provenance in `tests/contract/test_graph_json_v4.py`
- [x] T015 [P] [US1] Add integration test that `index --include-docs` on `docs_pdf_project` writes expected headings/edges in `tests/integration/test_cli_index_docs.py`

### Implementation for User Story 1

- [x] T016 [US1] Implement Markdown/TXT/RST heading stack extraction and link fact collection in `src/grapheinstein/core/parsers/docs.py` per `research.md` R3 (UTF-8 decode failure → skip with warning)
- [x] T017 [US1] Implement unambiguous link/heading target resolution and `section_of`/`mentions` emission in `src/grapheinstein/core/parsers/resolve_docs.py` per `research.md` R5
- [x] T018 [US1] Expose docs merge entrypoint (e.g. `merge_docs_structure`) from `src/grapheinstein/core/parsers/__init__.py` (or docs module) that merges into an existing DiGraph and returns skip count
- [x] T019 [US1] Add `--include-docs` boolean flag to `index` (and default-path alias) in `src/grapheinstein/cli.py`; ensure it is **not** listed in `_OPTS_WITH_VALUE`; pass through to `index_project`
- [x] T020 [US1] Wire docs-structure pass into `src/grapheinstein/core/index.py` after code extract when `include_docs` is true; set `graph.graph["include_docs"]`; respect ignore rules; accumulate parse skips
- [x] T021 [US1] Update index success summary in `src/grapheinstein/cli.py` to report heading and `section_of`/`mentions` counts
- [x] T022 [US1] Update visualize summary/DOT in `src/grapheinstein/core/visualize.py` to include `heading` / `section_of` / `mentions` without crashing

**Checkpoint**: US1 MVP complete — `--include-docs` produces schema `4.0.0` digraph with documentation structure

---

## Phase 4: User Story 2 - Index PDF Documents by Section (Priority: P1)

**Goal**: With PDF inclusion enabled, extract text via PyMuPDF, chunk by sections, and add `heading` nodes + `section_of` edges (`extracted`); bad PDFs do not abort the index

**Independent Test**: Index with `--include-pdfs` → section headings + `section_of` for `sample.pdf`; `corrupt.pdf` skipped with warning; exit 0; docs structure absent unless docs flag also set (quickstart Scenario C)

### Tests for User Story 2

- [x] T023 [P] [US2] Add unit tests for PDF section extraction (TOC / fallback page sections) and failure handling in `tests/unit/test_pdf_extract.py`
- [x] T024 [P] [US2] Add integration test that `index --include-pdfs` on `docs_pdf_project` writes PDF headings, skips corrupt PDF, and exits 0 in `tests/integration/test_cli_index_pdfs.py`

### Implementation for User Story 2

- [x] T025 [US2] Implement PyMuPDF text extraction and section chunking in `src/grapheinstein/core/parsers/pdf.py` per `research.md` R1 (TOC preferred; page fallback; encrypted/empty → skip)
- [x] T026 [US2] Merge PDF headings into the DiGraph with `section_of` edges via helpers in `src/grapheinstein/core/parsers/pdf.py` (or shared resolve helper); return skip count
- [x] T027 [US2] Add `--include-pdfs` boolean flag to `index` (and default-path alias) in `src/grapheinstein/cli.py`; ensure it is **not** listed in `_OPTS_WITH_VALUE`; pass through to `index_project`
- [x] T028 [US2] Wire PDF-structure pass into `src/grapheinstein/core/index.py` after docs pass when `include_pdfs` is true; set `graph.graph["include_pdfs"]`; respect ignore rules; accumulate parse skips
- [x] T029 [US2] Ensure per-PDF exceptions are logged and do not abort index in `src/grapheinstein/core/parsers/pdf.py` / `src/grapheinstein/core/index.py`; surface skip count in summary when non-zero

**Checkpoint**: US1 + US2 — docs and PDF structure enrichment each work behind their flags

---

## Phase 5: User Story 3 - Opt Into Docs and PDFs via Index Flags (Priority: P1)

**Goal**: Default index (no flags) adds no docs/PDF structure; each flag independently enables only its modality; both flags combine; default-path alias preserves flag tokens

**Independent Test**: Same fixture indexed three ways (default / docs-only / pdfs-only / both) matches quickstart Scenarios A–D and F

### Tests for User Story 3

- [x] T030 [P] [US3] Add integration tests for flag matrix (default off, `--include-docs` only, `--include-pdfs` only, both) and default-path alias with flags in `tests/integration/test_cli_include_flags.py`
- [x] T031 [P] [US3] Add contract/CLI assertion that schema `4.0.0` graphs record `include_docs` / `include_pdfs` metadata when flags are used in `tests/contract/test_graph_json_v4.py` (or dedicated contract file)

### Implementation for User Story 3

- [x] T032 [US3] Verify and harden `prepend_index_if_needed` in `src/grapheinstein/cli.py` so `--include-docs` / `--include-pdfs` never consume the project path as an option value
- [x] T033 [US3] Ensure `index_project` / `build_inventory_graph` in `src/grapheinstein/core/index.py` skip docs and PDF merge when flags are false while still writing schema `4.0.0` inventory + code structure
- [x] T034 [US3] Persist boolean `include_docs` / `include_pdfs` on `graph.graph` for every successful index run in `src/grapheinstein/core/index.py` (explicit false when off)
- [x] T035 [US3] Confirm ignored paths never receive docs/PDF structure even when flags are on (coverage in `tests/integration/test_cli_include_flags.py` and ignore-aware discovery already used by index)

**Checkpoint**: All three stories — opt-in flag contract matches CLI/graph contracts

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cross-story validation and suite hygiene

- [x] T036 [P] Add unit tests for visualize/status heading counts in `tests/unit/test_visualize_summary.py` (extend existing expectations for v4)
- [x] T037 [P] Ensure `tests/contract/` rejects `old_schema_v3_graph.json` with re-index messaging in `tests/contract/test_graph_json_v4.py`
- [x] T038 Run full pytest suite and fix regressions from schema bump across `tests/`
- [x] T039 Run manual validation scenarios from `specs/004-docs-pdf-parsers/quickstart.md` (A–F) and fix any gaps

**Checkpoint**: Feature ready for `/speckit-implement` completion criteria

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS** all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP
- **User Story 2 (Phase 4)**: Depends on Foundational; can proceed after or in parallel with US1 if `--include-pdfs` wiring does not conflict on `cli.py`/`index.py` (coordinate shared files)
- **User Story 3 (Phase 5)**: Depends on US1 + US2 flag wiring being present (validates matrix)
- **Polish (Phase 6)**: Depends on desired stories complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — introduces `--include-docs` + docs parsers
- **US2 (P1)**: After Foundational — introduces `--include-pdfs` + PDF parser; independently testable with docs flag off
- **US3 (P1)**: After US1 + US2 — flag matrix / default-off / alias hardening

### Within Each User Story

- Tests marked first SHOULD fail before implementation where practical
- Extract/resolve before index wiring
- CLI flag before or with index wiring for that modality
- Story checkpoint before moving on

### Parallel Opportunities

- T002–T004 in Setup
- T011–T015 tests in US1; T016 can start after T011/T012 shape is clear
- T023–T024 tests in US2 while US1 implementation finishes (different test files)
- T030–T031 in US3 once both flags exist
- T036–T037 in Polish

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together:
Task: "Unit tests for heading helpers in tests/unit/test_graph_heading_entities.py"
Task: "Unit tests for docs extract in tests/unit/test_docs_extract.py"
Task: "Unit tests for resolve_docs in tests/unit/test_resolve_docs.py"
Task: "Contract tests schema 4.0.0 in tests/contract/test_graph_json_v4.py"
Task: "Integration test --include-docs in tests/integration/test_cli_index_docs.py"
```

## Parallel Example: User Story 2

```bash
# Launch US2 tests together:
Task: "Unit tests for PDF extract in tests/unit/test_pdf_extract.py"
Task: "Integration test --include-pdfs in tests/integration/test_cli_index_pdfs.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (schema 4.0.0)
3. Complete Phase 3: User Story 1 (`--include-docs`)
4. **STOP and VALIDATE**: quickstart Scenario B
5. Demo/ship MVP docs structure

### Incremental Delivery

1. Setup + Foundational → v4 foundation
2. US1 → docs structure behind `--include-docs`
3. US2 → PDF structure behind `--include-pdfs`
4. US3 → flag matrix / default-off guarantees
5. Polish → full quickstart A–F

### Parallel Team Strategy

1. Team completes Setup + Foundational together
2. Developer A: US1 (docs); Developer B: US2 (PDF) — merge carefully on `cli.py` / `index.py`
3. Together: US3 flag matrix + Polish

---

## Notes

- [P] tasks = different files, no dependencies on incomplete work
- [Story] label maps task to US1/US2/US3
- Do not rename existing `references` edges; `mentions` is additive
- Prefer omitting ambiguous `mentions` over wrong links
- No OCR for image-only PDFs in this feature
- Commit after each task or logical group
- Avoid: vague tasks, same-file conflicts without sequencing, cross-story coupling that breaks independent tests
