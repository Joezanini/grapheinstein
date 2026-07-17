# Implementation Plan: Directed File Graph Index & Visualize

**Branch**: `002-digraph-index-visualize` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-digraph-index-visualize/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Extend the existing `grapheinstein` CLI so `index` builds a NetworkX `DiGraph` with nodes `{id, type: file|dir, metadata}`, `contains` and whole-token basename `references` edges (both `extracted`), and writes portable node-link `graph.json` at **schema_version `2.0.0`** (breaking vs 1.0.0). Add `visualize --input` for a console summary and optional `--dot` file export (summary still prints). Reuse Typer/NetworkX/pathspec/Rich/Loguru; stay local-first; reject old-shape graphs without migration.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Typer, NetworkX, pathspec, Rich, Loguru, PyYAML (existing); no new required deps for DOT (hand-written DOT writer)

**Storage**: Local filesystem — `graph.json` (NetworkX node-link envelope v2); optional DOT file; optional `~/.grapheinstein/config.yaml`

**Testing**: pytest; Typer `CliRunner`; fixture projects under `tests/fixtures/` (extend sample + add mention/symlink cases)

**Target Platform**: macOS / Linux developer workstations (Windows best-effort via pathlib)

**Project Type**: Installable CLI package (extension of existing layout)

**Performance Goals**: Index ≥50 non-ignored files in under 2 minutes (SC-001); mention scan is linear over text files × unique basenames with indexing optimizations (see research)

**Constraints**: Offline-only; `.gitignore`; no symlink following; overwrite outputs without prompt; reject schema 1.0.0 / `kind` graphs; human output must not corrupt JSON/DOT files

**Scale/Scope**: Single-project trees; filesystem inventory + UTF-8 text basename mentions; no AST/SQL/PDF/media/query commands

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | No cloud; pathspec + local FS; ignore rules retained |
| CLI-first parity | PASS | `index` + new `visualize`; shared `core/` library for future slash/MCP |
| Provenance graph | PASS | `contains` / `references` with `provenance: extracted` |
| Multi-modal scope | PASS | Filesystem + UTF-8 text mention scan; AST/SQL/PDF/image/media **out of scope** |
| Incremental simplicity | PASS | NetworkX + JSON + hand-written DOT; no Graphviz Python binding required |
| Schema/contract | PASS | Breaking bump to `2.0.0`; contracts + tests required; no silent migration |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R1–R5 and quickstart offline scenarios |
| CLI-first parity | PASS | [contracts/cli.md](./contracts/cli.md) documents `index` / `visualize` / retained `status` |
| Provenance graph | PASS | [data-model.md](./data-model.md) + [graph-json.md](./contracts/graph-json.md) require typed edges + provenance |
| Multi-modal scope | PASS | Mentions treated as plain text; `core/parsers/` remains stub |
| Incremental simplicity | PASS | No Complexity Tracking violations |
| Schema/contract | PASS | `1.0.0` → `2.0.0` break documented; load rejects old shape |

## Project Structure

### Documentation (this feature)

```text
specs/002-digraph-index-visualize/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   └── graph-json.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/grapheinstein/
├── __init__.py
├── __main__.py
├── cli.py               # Typer: index, status, visualize; default→index
├── utils.py
└── core/
    ├── __init__.py
    ├── graph.py         # DiGraph build/load/save; schema 2.0.0; validation
    ├── index.py         # discovery (no symlink follow) + contains + references
    ├── references.py    # whole-token basename mention extraction (new)
    ├── visualize.py     # summary + DOT export (new)
    └── parsers/
        └── __init__.py  # stub (unchanged)

tests/
├── fixtures/
│   └── sample_project/  # extend for mentions / optional symlink
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Keep the existing flat `cli.py` + `core/` package from feature 001. Add `core/references.py` and `core/visualize.py` rather than a premature `cli/` / `ingest/` split. No web/mobile options.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
