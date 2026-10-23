---
description: "Task list for code node signatures and snippets"
---

# Tasks: Code Node Signatures and Snippets

**Input**: Design documents from `/specs/015-node-signatures-snippets/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. The spec requires automated checks for TypeScript, JavaScript, Python, and Dart, plus secret-path and cap behavior.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project (Grapheinstein default)**: `src/grapheinstein/`, `tests/` at repository root

## Grapheinstein Task Categories *(when applicable)*

- **Extract**: Tree-sitter signature and snippet capture for Python, JavaScript, TypeScript, and Dart (`core/parsers/signatures.py`, `core/parsers/extract.py`)
- **Graph**: Optional code-entity metadata; schema stays `6.0.0` (`core/graph.py`, `core/parsers/resolve.py`)
- **Config**: `snippets`, `snippet_max_lines`, `snippet_max_bytes` (`utils.py`, CLI, API, serve)
- **Contracts/tests**: Per-language unit tests and snippet policy tests

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the repo can host the feature without new packages

- [x] T001 Confirm `pyproject.toml` gains no new dependencies and `.gitignore` already ignores Python bytecode, virtualenvs, and `.env` files

**Checkpoint**: Existing install path remains `pip install -e ".[dev]"`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Metadata channel and cache identity shared by every story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Add `Parameter`-shaped dicts and optional signature/snippet fields on `CodeEntity` in `src/grapheinstein/core/parsers/extract.py`, preserving them when functions inside classes are reclassified as methods
- [x] T003 Extend `add_code_entity` in `src/grapheinstein/core/graph.py` to copy optional `signature`, `parameters`, `return_type`, `signature_truncated`, `snippet`, and `snippet_truncated` without changing `SCHEMA_VERSION`
- [x] T004 Pass those fields through `apply_entities` in `src/grapheinstein/core/parsers/resolve.py` and bump `_AST_PARSER_VERSION` to `tree-sitter-v2`, including snippet settings in the AST cache settings hash
- [x] T005 Add `SnippetSettings` plus basename secret detection, whitespace collapse, and line/byte truncation helpers in `src/grapheinstein/core/parsers/signatures.py`

**Checkpoint**: A code entity can carry the new metadata, old graphs still validate, and a changed extractor does not reuse `tree-sitter-v1` cache entries

---

## Phase 3: User Story 1 - Callable Signatures (Priority: P1) 🎯 MVP

**Goal**: Function and method nodes for TypeScript, JavaScript, Python, and Dart expose parameter name, collapsed source type, passing kind, required flag, and declared return type

**Independent Test**: `pytest tests/unit/test_signatures_python.py tests/unit/test_signatures_javascript.py tests/unit/test_signatures_typescript.py tests/unit/test_signatures_dart.py`

### Tests for User Story 1

- [x] T006 [P] [US1] Add Python signature tests (annotations, keyword-only, `*args`, `**kwargs`, no invented types) in `tests/unit/test_signatures_python.py`
- [x] T007 [P] [US1] Add JavaScript signature tests (names, defaults, rest, no invented types) in `tests/unit/test_signatures_javascript.py`
- [x] T008 [P] [US1] Add TypeScript tests for `createTask`, `setCustomFieldValue`, `createWebhook`, and overloads in `tests/unit/test_signatures_typescript.py`
- [x] T009 [P] [US1] Add Dart tests for positional, required named, optional named, optional positional, and a constructor in `tests/unit/test_signatures_dart.py`

### Implementation for User Story 1

- [x] T010 [US1] Implement signature extraction for the four languages in `src/grapheinstein/core/parsers/signatures.py` and call it from `src/grapheinstein/core/parsers/extract.py` for function and method nodes
- [x] T011 [US1] Keep class nodes to a declaration line with no `parameters` list in `src/grapheinstein/core/parsers/signatures.py`

**Checkpoint**: Each language test shows the declared contract without opening the source by hand

---

## Phase 4: User Story 2 - Capped Source Snippets (Priority: P1)

**Goal**: Function, method, and class nodes carry a verbatim excerpt from decorators/annotations through the body, truncated at 40 lines and 2048 bytes

**Independent Test**: Snippet assertions in the language tests plus `tests/unit/test_snippet_policy.py` line and byte caps

### Tests for User Story 2

- [x] T012 [P] [US2] Assert decorator-inclusive, JSDoc-exclusive snippets and class-versus-method spans in `tests/unit/test_signatures_python.py` and `tests/unit/test_signatures_typescript.py`
- [x] T013 [P] [US2] Add line-cap and byte-cap tests in `tests/unit/test_snippet_policy.py`

### Implementation for User Story 2

- [x] T014 [US2] Capture snippet spans (Python `decorated_definition`, Dart `function_body` sibling, no comment/JSDoc) and apply caps in `src/grapheinstein/core/parsers/signatures.py`

**Checkpoint**: Excerpts stay within both caps and `snippet_truncated` is set whenever a snippet is stored

---

## Phase 5: User Story 4 - Secret Paths (Priority: P1)

**Goal**: Secret basenames never receive a snippet; signatures still may

**Independent Test**: `pytest tests/unit/test_snippet_policy.py -k secret`

### Tests for User Story 4

- [x] T015 [P] [US4] Add secret-basename cases (`.env`, `.env.local`, `secret`, `credential`, `password`, `.pem`, `.key`, `id_rsa`) and a normal-file control in `tests/unit/test_snippet_policy.py`

### Implementation for User Story 4

- [x] T016 [US4] Skip snippet metadata when `is_secret_basename` matches in `src/grapheinstein/core/parsers/signatures.py`

**Checkpoint**: A secret-pattern file contributes no `snippet` key

---

## Phase 6: User Story 3 - Disable Snippets and Tighten Caps (Priority: P2)

**Goal**: Config and one-run flags turn snippets off or lower the caps without dropping signatures

**Independent Test**: Config rejection of caps above 40/2048, and an index run with snippets disabled, in `tests/unit/test_snippet_policy.py`

### Tests for User Story 3

- [x] T017 [P] [US3] Add config and `index_project` tests for `snippets: false`, tighter caps, and out-of-range values in `tests/unit/test_snippet_policy.py`

### Implementation for User Story 3

- [x] T018 [US3] Add `snippets`, `snippet_max_lines`, and `snippet_max_bytes` to `AppConfig`, coercion, and `DEFAULT_CONFIG_TEMPLATE` in `src/grapheinstein/utils.py`
- [x] T019 [US3] Thread the settings through `index_project` / `build_inventory_graph` in `src/grapheinstein/core/index.py` and `merge_code_structure` in `src/grapheinstein/core/parsers/resolve.py`
- [x] T020 [US3] Add `--no-snippets`, `--snippet-max-lines`, and `--snippet-max-bytes` in `src/grapheinstein/cli.py` (including `_OPTS_WITH_VALUE`), `index()` in `src/grapheinstein/api.py`, and `IndexBody` in `src/grapheinstein/serve/app.py`

**Checkpoint**: Disabling snippets removes excerpts only; illegal caps fail configuration before a success graph

---

## Phase 7: User Story 5 - Docs and Minor Version (Priority: P2)

**Goal**: Operators and agents can read the optional fields, and the product version is 0.4.0

**Independent Test**: `README.md`, `docs/agent-integration.md`, and `CHANGELOG.md` describe the fields, caps, disable switch, and secret rule; package version is `0.4.0`

### Implementation for User Story 5

- [x] T021 [P] [US5] Document signatures, snippets, caps, `--no-snippets`, and secret basenames in `README.md`
- [x] T022 [P] [US5] Document the optional metadata keys for agents in `docs/agent-integration.md`
- [x] T023 [US5] Set version `0.4.0` in `pyproject.toml` and `src/grapheinstein/__init__.py`, and add the `0.4.0` entry in `CHANGELOG.md`. Do not publish to PyPI

**Checkpoint**: A reader can find the minor version note and the operator controls

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Schema compatibility and the quickstart command

- [x] T024 Reject malformed optional signature metadata in `src/grapheinstein/core/graph.py` while still loading graphs that omit the new keys and still reporting `schema_version` `6.0.0`
- [x] T025 Run `pytest` for the new unit tests and `ruff check` on the touched modules; fix failures before finishing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — blocks all stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP
- **User Story 2 (Phase 4)**: Depends on Foundational and the signature module from US1
- **User Story 4 (Phase 5)**: Depends on snippet capture from US2
- **User Story 3 (Phase 6)**: Depends on snippet capture so the disable switch has an effect
- **User Story 5 (Phase 7)**: Depends on the final flag and field names
- **Polish (Phase 8)**: Depends on the desired stories

### User Story Dependencies

- **User Story 1 (P1)**: First increment after Foundational
- **User Story 2 (P1)**: Adds excerpts on the same entities
- **User Story 4 (P1)**: Secret skip on top of excerpts
- **User Story 3 (P2)**: Config and CLI around the same excerpt path
- **User Story 5 (P2)**: Docs after the contract is implemented

### Parallel Opportunities

- T006–T009 can be written together
- T012 and T013 can be written together
- T021 and T022 touch different docs

---

## Parallel Example: User Story 1

```bash
# Language tests are independent files:
tests/unit/test_signatures_python.py
tests/unit/test_signatures_javascript.py
tests/unit/test_signatures_typescript.py
tests/unit/test_signatures_dart.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2
2. Complete Phase 3 (signatures on the four languages)
3. Stop and run the four signature test modules

### Incremental Delivery

1. Signatures (US1)
2. Capped snippets (US2)
3. Secret skip (US4)
4. Config and CLI caps (US3)
5. Docs and 0.4.0 (US5)
6. Loader checks and the quickstart pytest command

---

## Notes

- Schema version stays `6.0.0`
- Do not publish to PyPI
- Tests are local fixtures, not a clone of `clickup-kitchen-sink`
