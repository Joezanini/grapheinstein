# Implementation Plan: Contribution Documentation

**Branch**: `013-contribution-docs` | **Date**: 2026-07-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-contribution-docs/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Add standard open-source contribution documentation (`CONTRIBUTING.md`) covering setup → validate → propose, welcome contribution types, and project-principle norms. Link it from a short **Contributing** section in the root README (same discovery pattern as Agent integration → `docs/agent-integration.md`). Documentation-only; no CLI, graph schema, or runtime API changes. Guard with a small contract test that the README link resolves and required guide sections exist.

## Technical Context

**Language/Version**: Markdown documentation (project remains Python 3.11+; unchanged by this feature)

**Primary Dependencies**: None new — reuses existing Install / Validation guidance already in `README.md`; principles live in `.specify/memory/constitution.md`

**Storage**: N/A (static docs in the git repository)

**Testing**: pytest contract test(s) asserting README Contributing link target exists and `CONTRIBUTING.md` contains required section markers (mirrors `tests/contract/test_agent_docs.py`)

**Target Platform**: Git hosting README + local clone (GitHub and equivalents)

**Project Type**: Documentation for an installable CLI / library package

**Performance Goals**: N/A for runtime; discovery goal is human-scale (README section + one working link in under 30 seconds per SC-001)

**Constraints**: Docs-only; must not require cloud services to contribute; distinguish core `pip install -e ".[dev]"` + `pytest` from optional `[serve]` extras; no new Code of Conduct or security-reporting channel unless already defined (none today)

**Scale/Scope**: One top-level contribution guide + one README section + contract test; no CLA, governance body, or contributor portal

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Contribution path is local clone + local tests; no cloud APIs required to contribute |
| CLI-first parity | PASS | No new CLI/API surface; docs point contributors at existing CLI-first workflow |
| Provenance graph | PASS | No graph/edge changes |
| Multi-modal scope | PASS | No parser/ingestion changes |
| Incremental simplicity | PASS | Markdown + README link + small contract test; no new runtime deps |
| Schema/contract | PASS | Graph schema unchanged; additive docs contract only |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R1–R4; quickstart offline |
| CLI-first parity | PASS | Guide references existing CLI/dev workflow; no divergent agent APIs |
| Provenance graph | PASS | [data-model.md](./data-model.md) is documentation entities only |
| Multi-modal scope | PASS | Out of scope for this feature |
| Incremental simplicity | PASS | Top-level `CONTRIBUTING.md` chosen over multi-file portal |
| Schema/contract | PASS | [contracts/docs.md](./contracts/docs.md); graph `6.0.0` retained |

## Project Structure

### Documentation (this feature)

```text
specs/013-contribution-docs/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── docs.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
CONTRIBUTING.md                      # NEW: community contribution guide
README.md                            # ADD: ## Contributing section + link
.specify/memory/constitution.md      # referenced (not modified) for principles

tests/
└── contract/
    └── test_contributing_docs.py    # NEW: existence + required sections + README link
```

**Structure Decision**: Keep a single-package repo layout. Place the contribution guide at repository root as `CONTRIBUTING.md` (GitHub and common hosts auto-surface it). Keep a short README entry point that links to that file—parallel to the existing Agent integration → `docs/agent-integration.md` pattern, but using the conventional top-level name for contribution discovery. No changes under `src/grapheinstein/`.

## Complexity Tracking

> No constitution violations. Table left empty intentionally.
