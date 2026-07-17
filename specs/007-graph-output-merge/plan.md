# Implementation Plan: Valid Graph Output, Compression, Versioning & Merge

**Branch**: `007-graph-output-merge` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-graph-output-merge/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Harden graph persistence so every successful `grapheinstein index` writes a complete, validated NetworkX node-link `graph.json` (all node `metadata`, edge attrs, and graph-level fields) via atomic write. Add optional **gzip compression** (`--compress` → `.json.gz`), optional **file versioning** (`--versioned` → `graph_vN.json` snapshots beside the primary latest path), and a new **`grapheinstein merge`** subcommand that unions compatible graphs with hard-fail on conflicting node ids. Remain on **schema_version `6.0.0`** with additive optional merge metadata on the `graph` object. Stdlib only for gzip/atomic I/O; no new required dependencies.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing — Typer, NetworkX, pathspec, Rich, Loguru, PyYAML, tree-sitter (+ grammars), pymupdf; optional `[media]`. New I/O uses **stdlib** `gzip`, `tempfile`/`os.replace` only (no new packages).

**Storage**: Local filesystem — portable graph artifacts (`.json` / `.json.gz`); numbered snapshots `graph_vN.json[.gz]`; config may gain optional defaults for `compress` / `versioned` (CLI flags primary)

**Testing**: pytest; Typer `CliRunner`; unit tests for atomic write, gzip round-trip, version numbering, merge union/conflict; contract tests for CLI + artifact I/O; integration on small fixtures

**Target Platform**: macOS / Linux developer workstations (Windows best-effort via pathlib)

**Project Type**: Installable CLI package (extension of existing `cli.py` + `core/` layout)

**Performance Goals**: Merge ≤10k combined nodes in under 30 seconds on a typical developer machine (SC-004); compression/decompression negligible vs index time

**Constraints**: Offline-only; no cloud; overwrite primary `--output` without prompt; never overwrite existing `graph_vN` snapshots; no corrupt success artifact on failure; reject incompatible schema versions on merge; preserve provenance on all edges through write/merge

**Scale/Scope**: Persistence + CLI I/O only — no new parsers, node types, or query commands; modalities already in input graphs are preserved as opaque validated payloads

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Filesystem I/O only; gzip stdlib; no cloud |
| CLI-first parity | PASS | Extend `index`; add `merge` subcommand; shared `core/` helpers |
| Provenance graph | PASS | Write/merge preserve edge `type` + `provenance`; no unlabeled edges |
| Multi-modal scope | PASS | No new modalities; preserves whatever nodes/edges inputs already have |
| Incremental simplicity | PASS | NetworkX + local files; no graph DB |
| Schema/contract | PASS | Stay on `6.0.0`; additive optional `graph` merge fields; CLI contract + tests |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R1–R5; quickstart offline |
| CLI-first parity | PASS | [contracts/cli.md](./contracts/cli.md) documents `--compress`, `--versioned`, `merge` |
| Provenance graph | PASS | [data-model.md](./data-model.md) merge rules preserve edge attrs |
| Multi-modal scope | PASS | I/O-only; no parser changes |
| Incremental simplicity | PASS | No Complexity Tracking violations |
| Schema/contract | PASS | `6.0.0` retained; optional merge metadata documented in [graph-json.md](./contracts/graph-json.md) |

## Project Structure

### Documentation (this feature)

```text
specs/007-graph-output-merge/
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
├── cli.py                 # index: --compress, --versioned; new merge command
├── utils.py               # optional config keys compress / versioned
└── core/
    ├── graph.py           # atomic save; gzip load/save; validate before/after write
    ├── merge.py           # union graphs; conflict detection; merge graph metadata
    ├── index.py           # call unified write helper (compress + versioned)
    ├── visualize.py       # preferably load via gzip-aware loader (nice-to-have)
    └── parsers/           # unchanged

tests/
├── fixtures/
│   └── merge_project/     # small A/B graphs + conflict fixture (or synthetic JSON)
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Keep existing `cli.py` + `core/` layout. Add `core/merge.py` for pure merge logic; extend `core/graph.py` for atomic/gzip I/O and versioned path helpers. No web/mobile options.

## Complexity Tracking

> No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
