# Implementation Plan: Code Node Signatures and Snippets

**Branch**: `015-node-signatures-snippets` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-node-signatures-snippets/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Attach optional callable signatures and capped source snippets to function, method, and class nodes for TypeScript, JavaScript, Python, and Dart. Signatures record parameter name, collapsed source type text, passing kind (`positional` | `named` | `rest` | `keywords`), and `required`, plus `return_type` when declared. Snippets are verbatim declaration-through-body text, including an attached decorator or annotation, truncated at 40 lines and 2048 bytes by default. Operators can disable snippets or lower the caps from config or the index command. Secret-pattern file names never receive a snippet. Graph `schema_version` stays `6.0.0`. Product version becomes `0.4.0`. No PyPI publish.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing Tree-sitter grammars (`tree-sitter-python`, `tree-sitter-javascript`, `tree-sitter-typescript`, `tree-sitter-dart`) plus Typer, NetworkX, PyYAML. No new third-party packages. See [research.md](./research.md).

**Storage**: Portable `graph.json` at schema `6.0.0` with optional code-entity metadata. Local YAML config gains snippet keys. AST cache payload grows with signature fields; parser cache version bumps so old pickles are not reused.

**Testing**: pytest unit tests, one module per language, plus snippet policy (cap, disable, secret paths) and a graph-load check that `schema_version` stays `6.0.0` and old nodes still validate.

**Target Platform**: Local CLI on macOS / Linux (Windows best-effort via pathlib). Fully offline.

**Project Type**: Installable CLI package. Extend parser extraction, graph metadata, config, CLI, Python API, and serve index body. Explain/query already copy node metadata and need no new projection.

**Performance Goals**: Signature and snippet work is a single extra walk of nodes already parsed for structure extraction. Snippet text is sliced from the file bytes already read. No extra file I/O and no network.

**Constraints**: Local-first. New metadata keys optional. Caps cannot be configured above 40 lines or 2048 bytes. Snippets off still leaves signatures. Secret rule is basename-only, as specified. Other languages unchanged. Do not publish to PyPI.

**Scale/Scope**: Four languages that already have Tree-sitter queries. ClickUp-shaped methods (`createTask`, `setCustomFieldValue`, `createWebhook`) are covered by an in-repo TypeScript fixture, not by cloning `clickup-kitchen-sink`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Source text is read from the local file already being parsed. No cloud calls. Ignore rules unchanged. |
| CLI-first parity | PASS | Snippet controls on `index`, `api.index`, and serve `POST /index`. |
| Provenance graph | PASS | No new edge types. Existing `defines` / `calls` / `imports` stay `extracted`. |
| Multi-modal scope | PASS | Code only, and only TypeScript, JavaScript, Python, and Dart. Docs, PDF, media, SQL, and other code languages unchanged. |
| Incremental simplicity | PASS | Extend `CodeEntity` and metadata. No new service, database, or parser package. |
| Schema/contract | PASS | Required graph fields stay. `schema_version` stays `6.0.0` because the loader rejects any other version and the spec requires old and new graphs to load. Product version `0.4.0` records the minor addition. Optional keys documented in `contracts/graph-json.md`. |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R1–R6. Quickstart uses local fixtures only. |
| CLI-first parity | PASS | [contracts/cli.md](./contracts/cli.md) and [contracts/python-api.md](./contracts/python-api.md). |
| Provenance graph | PASS | Metadata-only. Edge provenance untouched. |
| Multi-modal scope | PASS | Language gate is the four named languages. |
| Incremental simplicity | PASS | No Complexity Tracking violations. |
| Schema/contract | PASS | Additive optional metadata on schema `6.0.0`. Constitution "breaking schema change" rule is not triggered: required fields, edge types, and provenance do not change. |

## Project Structure

### Documentation (this feature)

```text
specs/015-node-signatures-snippets/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── graph-json.md
│   ├── cli.md
│   └── python-api.md
└── tasks.md             # /speckit-tasks — not created here
```

### Source Code (repository root)

```text
src/grapheinstein/
├── __init__.py            # __version__ = 0.4.0
├── cli.py                 # --no-snippets, --snippet-max-lines, --snippet-max-bytes
├── api.py                 # same kwargs on index()
├── utils.py               # AppConfig keys, validation, init template
├── serve/app.py           # IndexBody fields
└── core/
    ├── graph.py           # add_code_entity optional metadata; schema stays 6.0.0
    ├── index.py           # pass snippet settings into merge
    └── parsers/
        ├── extract.py     # signature + snippet on CodeEntity
        ├── resolve.py     # copy metadata onto nodes; bump AST cache version
        └── queries/__init__.py  # only if a capture is missing a needed node

tests/unit/
├── test_signatures_python.py
├── test_signatures_javascript.py
├── test_signatures_typescript.py
├── test_signatures_dart.py
└── test_snippet_policy.py

README.md                  # operator section
docs/agent-integration.md  # field names for agents
CHANGELOG.md               # 0.4.0
pyproject.toml             # version 0.4.0
```

**Structure Decision**: Single Python CLI package. Signature parsing lives next to the existing Tree-sitter extract pass. Caps, the disable switch, and secret-path skipping are applied when metadata is written so the graph contract does not depend on query changes. Explain and query already persist the node `metadata` object.

## Complexity Tracking

No constitution violations. Additive optional metadata on schema `6.0.0` is the compatible reading of the constitution's breaking-change rule: required fields, relationship types, and provenance labels do not change, and the loader cannot accept a second schema version without rejecting older graphs.

## Agent context

This repository has no `.specify/scripts/bash/update-agent-context.sh` (and no `AGENTS.md`). Operator and agent-facing context for this feature is `README.md` and `docs/agent-integration.md`, updated in implementation. The plan phase does not invent that script.
