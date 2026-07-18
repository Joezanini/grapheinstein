---
description: "Task list for Contribution Documentation"
---

# Tasks: Contribution Documentation

**Input**: Design documents from `/specs/013-contribution-docs/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — plan and `contracts/docs.md` require `tests/contract/test_contributing_docs.py` (same pattern as `tests/contract/test_agent_docs.py`) to enforce README link resolution and required guide themes.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: docs at repository root (`README.md`, `CONTRIBUTING.md`); tests under `tests/contract/`

## Grapheinstein Task Categories *(when applicable)*

- **Documentation**: Root `CONTRIBUTING.md` + README Contributing entry point
- **Contracts/tests**: Docs contract markers per `contracts/docs.md`; no graph schema / CLI changes
- **Principles**: Link to `.specify/memory/constitution.md` (do not edit constitution)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm deliverable paths and contract markers before writing docs

- [x] T001 Confirm deliverable paths and required themes against `specs/013-contribution-docs/contracts/docs.md` and `specs/013-contribution-docs/research.md` (targets: `CONTRIBUTING.md`, `README.md` Contributing section, `tests/contract/test_contributing_docs.py`)

**Checkpoint**: Implementer knows exact files, headings, and marker phrases to satisfy

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the contribution guide file and contract-test scaffold so stories can link and assert against a real path

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Create `CONTRIBUTING.md` at repository root with stub section headings for all required themes from `specs/013-contribution-docs/research.md` R2 (Welcome, Development setup, Validate, Propose a change, Discuss large changes, Project principles, Optional extras) — placeholders OK
- [x] T003 [P] Add failing contract-test scaffold in `tests/contract/test_contributing_docs.py` modeled on `tests/contract/test_agent_docs.py` (assert `CONTRIBUTING.md` exists; stub theme/README assertions that will fail until story content lands)

**Checkpoint**: `CONTRIBUTING.md` exists and is linkable; contract test file is in place and fails on incomplete content

---

## Phase 3: User Story 1 - Discover How to Contribute from the README (Priority: P1) 🎯 MVP

**Goal**: Visitors find a clear Contributing section in `README.md` that links to `CONTRIBUTING.md`

**Independent Test**: Open `README.md` alone, locate `## Contributing`, follow the relative link, and land on an existing `CONTRIBUTING.md` (quickstart Scenario A)

### Tests for User Story 1

- [x] T004 [P] [US1] Extend `tests/contract/test_contributing_docs.py` to assert `README.md` has a level-2 Contributing heading, a welcoming sentence, and a relative Markdown link whose target resolves to `CONTRIBUTING.md` per `specs/013-contribution-docs/contracts/docs.md`

### Implementation for User Story 1

- [x] T005 [US1] Add `## Contributing` section to `README.md` (prefer after `## Validation`) with a short welcome and link to [`CONTRIBUTING.md`](CONTRIBUTING.md) per `specs/013-contribution-docs/research.md` R3
- [x] T006 [US1] Run `pytest tests/contract/test_contributing_docs.py -q` and confirm README-link assertions pass (theme assertions may still fail until US2/US3)

**Checkpoint**: US1 MVP — README discovers and opens the contribution guide; link is guarded by contract tests

---

## Phase 4: User Story 2 - Follow a Standard Contribution Path (Priority: P1)

**Goal**: First-time contributors learn setup → validate → propose, plus welcome contribution types and optional-extras note

**Independent Test**: Using only `CONTRIBUTING.md` (+ linked README Install/Validation), list end-to-end steps and answer setup / pytest / submit / what-to-work-on questions (quickstart Scenario B rows 1–4)

### Tests for User Story 2

- [x] T007 [P] [US2] Extend `tests/contract/test_contributing_docs.py` with case-insensitive markers for welcome types, development setup (`venv` or `pip install` + `[dev]`), validation (`pytest`), propose-change (`pull request` / `merge request` / `PR`), and optional extras (`[serve]` or `optional` + `serve`) per `specs/013-contribution-docs/contracts/docs.md`

### Implementation for User Story 2

- [x] T008 [US2] Write Welcome / contribution-types content in `CONTRIBUTING.md` (bug fixes, documentation, tests, features aligned with project principles)
- [x] T009 [US2] Write Development setup in `CONTRIBUTING.md` consistent with `README.md` Install (`python -m venv`, `pip install -e ".[dev]"`); state that optional `[serve]` / media extras are not required for core contributions
- [x] T010 [US2] Write Validate-before-proposing guidance in `CONTRIBUTING.md` requiring at least `pytest`, aligned with `README.md` Validation
- [x] T011 [US2] Write Propose-a-change guidance in `CONTRIBUTING.md` describing fork/branch → pull/merge request style process and high-level reviewer expectations in plain language
- [x] T012 [US2] Run `pytest tests/contract/test_contributing_docs.py -q` and confirm US2 theme markers pass (principles/discuss markers may still fail until US3)

**Checkpoint**: US1 + US2 — discoverable guide with a complete standard contribution path

---

## Phase 5: User Story 3 - Understand Project Norms Before Investing Time (Priority: P2)

**Goal**: Contributors know to discuss large/architectural changes first and can find project principles (local-first, CLI-first, provenance, incremental scope)

**Independent Test**: From `CONTRIBUTING.md` alone, state when to discuss first and open the principles link to `.specify/memory/constitution.md` (quickstart Scenarios B row 5 + E)

### Tests for User Story 3

- [x] T013 [P] [US3] Extend `tests/contract/test_contributing_docs.py` with markers for discuss-large-changes (`discuss` / `issue` plus `large` / `architect`) and project principles (`local-first` or `offline`, plus `constitution` or `.specify/memory/constitution.md`) per `specs/013-contribution-docs/contracts/docs.md`

### Implementation for User Story 3

- [x] T014 [US3] Write Discuss-large-changes guidance in `CONTRIBUTING.md` advising confirmation (issue/discussion) before substantial architectural effort
- [x] T015 [US3] Write Project principles section in `CONTRIBUTING.md` summarizing local-first/offline, CLI-first, provenance-labeled graph, and incremental simplicity; link to `.specify/memory/constitution.md` without modifying that file
- [x] T016 [US3] Run `pytest tests/contract/test_contributing_docs.py -q` and confirm all contract themes pass

**Checkpoint**: All user stories independently satisfied; full docs contract green

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and consistency across README + guide

- [x] T017 Walk all scenarios in `specs/013-contribution-docs/quickstart.md` (A–E) against the implemented `README.md` and `CONTRIBUTING.md`
- [x] T018 [P] Proofread `CONTRIBUTING.md` for first-time-contributor readability (ordered steps, no source-diving required) and FR-008 consistency with `README.md` Install / Validation
- [x] T019 Confirm no Code of Conduct or private security-reporting channel was invented (out of scope per spec assumptions); keep respectful-collaboration note brief if present in `CONTRIBUTING.md`
- [x] T020 Run full `pytest -q` to ensure docs contract changes did not break the suite

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (`CONTRIBUTING.md` must exist before README can link)
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP discovery
- **User Story 2 (Phase 4)**: Depends on Foundational; builds on guide file from Phase 2; can proceed after or in parallel with US1 if README link already present (prefer after US1 for MVP demo)
- **User Story 3 (Phase 5)**: Depends on Foundational; content-independent of US2 but same file — serialize edits to `CONTRIBUTING.md` after US2 to avoid merge conflicts
- **Polish (Phase 6)**: Depends on US1–US3 complete

### User Story Dependencies

- **User Story 1 (P1)**: Needs `CONTRIBUTING.md` file to exist (Phase 2); no dependency on full guide body
- **User Story 2 (P1)**: Fills core contribution path in `CONTRIBUTING.md`; independently testable via quickstart Scenario B
- **User Story 3 (P2)**: Adds norms/principles; independently testable via principles + discuss sections; share file with US2 so implement sequentially

### Within Each User Story

- Contract-test extensions for the story SHOULD be written and fail before (or while) filling the matching content
- Finish story checkpoint (`pytest` for that story’s assertions) before moving on when editing the same files

### Parallel Opportunities

- T003 can run in parallel with T002 (different files)
- T004 can be prepared in parallel with T005 once Phase 2 is done
- T007 can be written in parallel with early US2 drafting if careful about markers
- T013 can be prepared while US2 finishes, but T014–T015 should wait until US2 content is stable
- T018 can run in parallel with mental walkthrough notes from T017

---

## Parallel Example: User Story 1

```bash
# After Phase 2:
# Terminal A — contract assertions for README discovery
Task: "Extend tests/contract/test_contributing_docs.py for README Contributing heading + resolvable CONTRIBUTING.md link"

# Terminal B — README entry point (same story; coordinate if both touch test expectations)
Task: "Add ## Contributing section to README.md linking to CONTRIBUTING.md"
```

## Parallel Example: User Story 2

```bash
# Prefer single writer for CONTRIBUTING.md body; parallelize only the test markers file if a second person helps:
Task: "Extend tests/contract/test_contributing_docs.py for setup/validate/propose/welcome/optional markers"
Task: "Fill Welcome + Setup + Validate + Propose sections in CONTRIBUTING.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (`CONTRIBUTING.md` stub + test scaffold)
3. Complete Phase 3: User Story 1 (README Contributing + link tests)
4. **STOP and VALIDATE**: Quickstart Scenario A
5. Demo discoverability even if guide body is still stubs

### Incremental Delivery

1. Setup + Foundational → linkable stub guide
2. US1 → README discovery (MVP)
3. US2 → full contribution path
4. US3 → norms and principles
5. Polish → quickstart + full pytest

### Parallel Team Strategy

With two contributors:

1. Complete Setup + Foundational together
2. Person A: US1 (README + link tests)
3. Person B: Prepare US2/US3 contract markers, then serialize `CONTRIBUTING.md` body edits (US2 then US3)
4. Together: Polish / quickstart

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Do not modify `.specify/memory/constitution.md` in this feature
- Do not change CLI, graph schema, or runtime APIs
- Commit after each task or logical group
- Stop at any checkpoint to validate the story independently
