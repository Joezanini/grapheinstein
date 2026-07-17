# Implementation Plan: CLI Project Index Skeleton

**Branch**: `001-cli-project-index` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-cli-project-index/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Deliver an installable local `grapheinstein` CLI that indexes a project folder into a portable `graph.json` containing file and directory nodes (plus `contains` edges labeled `extracted`), respects `.gitignore`, supports `index` / `status` and default path invocation, and loads optional YAML config from `~/.grapheinstein/config.yaml` or `--config`. Stack: Python 3.11+, Typer, NetworkX, pathspec, Rich, Loguru, PyYAML — offline-only, no cloud.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Typer, NetworkX, pathspec, Rich, Loguru, PyYAML; packaging via hatchling or setuptools in `pyproject.toml`

**Storage**: Local filesystem only — `graph.json` (NetworkX node-link envelope); optional user config at `~/.grapheinstein/config.yaml`

**Testing**: pytest; Typer `CliRunner` for CLI; fixture projects under `tests/fixtures/`

**Target Platform**: macOS / Linux developer workstations (Windows best-effort via pathlib)

**Project Type**: Installable CLI library/package

**Performance Goals**: Index ≥50 non-ignored files in under 2 minutes on a typical laptop (SC-001); no network required

**Constraints**: Offline-capable; respect `.gitignore`; human output must not corrupt graph file; non-zero exit on errors; no multi-modal parsers or query commands in this increment

**Scale/Scope**: Single-project local trees (thousands of files acceptable); Phase-1 inventory only (files/dirs + containment)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | No cloud deps; pathspec + local FS; config under `~/.grapheinstein/` |
| CLI-first parity | PASS | Single Typer app; core functions reusable by future slash/MCP |
| Provenance graph | PASS | `contains` edges with `provenance: extracted`; schema_version on artifact |
| Multi-modal scope | PASS | This feature: filesystem inventory only; code/docs/SQL/shell/PDF/image/media **out of scope** |
| Incremental simplicity | PASS | NetworkX + JSON files; no Neo4j/vector DB/HTTP server |
| Schema/contract | PASS | `contracts/graph-json.md` + `contracts/cli.md`; tests required |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R2/R4 and quickstart offline scenario |
| CLI-first parity | PASS | CLI contract documents default/`index`/`status`; library entrypoints in `core/` |
| Provenance graph | PASS | data-model + graph-json contract require provenance on every edge |
| Multi-modal scope | PASS | `core/parsers/` is a stub package only |
| Incremental simplicity | PASS | No Complexity Tracking violations |
| Schema/contract | PASS | Contracts and quickstart validation scenarios defined |

## Project Structure

### Documentation (this feature)

```text
specs/001-cli-project-index/
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
├── __main__.py          # python -m grapheinstein
├── cli.py               # Typer app: default index, index, status
├── utils.py             # path helpers, console/logging setup
└── core/
    ├── __init__.py
    ├── graph.py         # NetworkX build + load/save graph.json
    ├── index.py         # discovery + ignore + inventory orchestration
    └── parsers/
        └── __init__.py  # stub for later modalities

tests/
├── fixtures/
│   └── sample_project/  # includes .gitignore, nested files
├── contract/
├── integration/
└── unit/

pyproject.toml
README.md                # minimal install/run (optional in this feature; quickstart covers validation)
```

**Structure Decision**: Use `src/grapheinstein/` with the user-requested module names (`cli.py`, `core/graph.py`, `core/index.py`, `core/parsers/`, `utils.py`, `__main__.py`). Defer the fuller `cli/` / `ingest/` / `query/` split until those features land. Single package, no web/mobile options.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
