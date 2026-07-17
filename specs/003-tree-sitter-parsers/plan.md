# Implementation Plan: Tree-sitter Code Parsers

**Branch**: `003-tree-sitter-parsers` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-tree-sitter-parsers/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Extend `grapheinstein index` so that, after the existing file/dir inventory and basename `references`, it runs **Tree-sitter AST extraction** for configurable languages (Python, JavaScript, TypeScript, Java, Go, Rust, C++, SQL). Emit `function` / `class` / `method` nodes (with start line) and `defines` / `imports` / `calls` edges, all with provenance `extracted`. Persist portable node-link `graph.json` at **schema_version `3.0.0`** (breaking vs `2.0.0`). Languages default to all eight; override via config and `--languages`. Partial parse failures skip structure for that file without aborting the index.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing — Typer, NetworkX, pathspec, Rich, Loguru, PyYAML. New — `tree-sitter` plus per-language grammar packages (`tree-sitter-python`, `tree-sitter-javascript`, `tree-sitter-typescript`, `tree-sitter-java`, `tree-sitter-go`, `tree-sitter-rust`, `tree-sitter-cpp`, and a SQL grammar wheel); see [research.md](./research.md) R1.

**Storage**: Local filesystem — `graph.json` (NetworkX node-link envelope v3); optional `~/.grapheinstein/config.yaml` (`languages` key)

**Testing**: pytest; Typer `CliRunner`; multi-language fixture project under `tests/fixtures/`; unit tests for extractors/resolution; contract tests for schema 3.0.0

**Target Platform**: macOS / Linux developer workstations (Windows best-effort via pathlib)

**Project Type**: Installable CLI package (extension of existing layout)

**Performance Goals**: Index ≥200 non-ignored source files across ≥2 languages in under 3 minutes offline (SC-005); one Parser instance per language per run

**Constraints**: Offline-only after install (no grammar downloads at index time); respect `.gitignore`; overwrite outputs without prompt; reject schema 2.x graphs; unknown language config fails closed; prefer omitting ambiguous import/call edges over wrong links

**Scale/Scope**: Structure extraction for eight languages; file/dir inventory retained; no LLM inferred edges; no query commands (`explain`/`path`/`ask`); docs/PDF/media out of scope

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Tree-sitter grammars as install deps; no cloud; ignore rules retained |
| CLI-first parity | PASS | Enrich `index`; config/`--languages`; shared `core/` for future slash/MCP |
| Provenance graph | PASS | New edges typed + `provenance: extracted` only |
| Multi-modal scope | PASS | Code (+ SQL as structured language) in; docs/PDF/image/media out |
| Incremental simplicity | PASS | NetworkX + local JSON; no graph DB; rule-based AST extract |
| Schema/contract | PASS | Breaking bump to `3.0.0`; contracts + tests required |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R1/R10; quickstart offline scenarios |
| CLI-first parity | PASS | [contracts/cli.md](./contracts/cli.md) documents `--languages` + config |
| Provenance graph | PASS | [data-model.md](./data-model.md) + [graph-json.md](./contracts/graph-json.md) |
| Multi-modal scope | PASS | Eight languages; SQL mapping conservative (R8) |
| Incremental simplicity | PASS | No Complexity Tracking violations; per-language packages not a platform |
| Schema/contract | PASS | `2.0.0` → `3.0.0` break documented; load rejects old artifacts |

## Project Structure

### Documentation (this feature)

```text
specs/003-tree-sitter-parsers/
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
├── cli.py                 # index gains --languages; summaries include code stats
├── utils.py               # AppConfig.languages; config validation
└── core/
    ├── graph.py           # schema 3.0.0; node/edge allow-lists; helpers
    ├── index.py           # after inventory+references → code extract merge
    ├── references.py      # unchanged behavior
    ├── visualize.py       # summary counts for new types
    └── parsers/
        ├── __init__.py    # public extract entrypoint
        ├── registry.py    # language ids, extensions, Language/Parser load
        ├── extract.py     # per-file parse + query → entities/facts
        ├── resolve.py     # import/call resolution → edges
        └── queries/       # tree-sitter .scm (or embedded) per language

tests/
├── fixtures/
│   └── code_project/      # multi-language defs/imports/calls + broken file
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Keep the existing `cli.py` + `core/` layout. Expand the existing `core/parsers/` stub into a small plugin-style package (registry + extract + resolve + queries) rather than introducing a top-level `ingest/` split. No web/mobile options.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
