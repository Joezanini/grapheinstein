# Implementation Plan: Path Between Concepts

**Branch**: `009-path-query` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-path-query/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Add `grapheinstein path <start> <end> --input <graph>`: load a portable schema `6.0.0` graph, resolve each endpoint with the same fuzzy (+ optional local embedding) matcher as `explain`, compute a preferred directed route via NetworkX weighted `shortest_path` (edge cost from relation type, confidence, and provenance), emit a structured path answer (JSON on stdout and/or `--output`) with per-step `type` + `provenance`, and print a path-grounded explanation on stderr (deterministic always; optional local-LLM polish). Offline-capable; no cloud APIs.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing — Typer, NetworkX, Rich, Loguru, PyYAML; reuse `core/match.py` and optional Ollama via `core/parsers/llm_ollama.py`. Path finding uses NetworkX `shortest_path` with a custom weight callable. No new required packages.

**Storage**: Local filesystem — read portable `.json` / `.json.gz` graphs; write optional path-answer JSON via `--output`; config under `~/.grapheinstein/config.yaml` and `--config`

**Testing**: pytest; Typer `CliRunner`; unit tests for edge-cost function, weighted path selection, trivial/same-node, no-path; contract tests for CLI help/flags + path-answer JSON shape; integration on fixture graphs with competing routes

**Target Platform**: macOS / Linux developer workstations (Windows best-effort via pathlib)

**Project Type**: Installable CLI package (extend existing `cli.py` + `core/` layout)

**Performance Goals**: Fixture path on graphs up to a few thousand nodes/edges ≤15s (SC-001); typically milliseconds for NetworkX shortest_path once the DiGraph is loaded; matching cost similar to explain

**Constraints**: Offline-capable; no cloud APIs; directed paths; preserve edge `type` + `provenance`; fail clearly on unresolved endpoints / no route; stay on schema `6.0.0` for input graphs; path answer is a separate JSON contract (not a full graph artifact)

**Scale/Scope**: Query command only — no new parsers or node/edge type allow-lists; modalities already in the input graph are path-queryable as nodes; slash/MCP out of scope

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Local graph files; optional local Ollama for match/explanation polish; no cloud |
| CLI-first parity | PASS | New `path` subcommand; library helpers in `core/` for later MCP reuse |
| Provenance graph | PASS | Path steps surface existing `type` + `provenance`; no unlabeled structural mutation |
| Multi-modal scope | PASS | Query-only; any existing node types matchable as endpoints |
| Incremental simplicity | PASS | NetworkX shortest_path + local files; reuse match.py; no graph DB |
| Schema/contract | PASS | Input remains `6.0.0`; new path-answer JSON contract + CLI tests |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R1–R6; quickstart offline paths |
| CLI-first parity | PASS | [contracts/cli.md](./contracts/cli.md) documents `path` surface |
| Provenance graph | PASS | [data-model.md](./data-model.md) / [path-json.md](./contracts/path-json.md) require per-step provenance |
| Multi-modal scope | PASS | No parser changes; matching uses node id/type/metadata text |
| Incremental simplicity | PASS | No Complexity Tracking violations |
| Schema/contract | PASS | Input `6.0.0` unchanged; path-answer contract versioned separately |

## Project Structure

### Documentation (this feature)

```text
specs/009-path-query/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   └── path-json.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/grapheinstein/
├── cli.py                      # new `path` command; _KNOWN_COMMANDS
├── utils.py                    # path_* / match config keys + CLI overrides
└── core/
    ├── graph.py                # reuse load_artifact; artifact→DiGraph helper if needed
    ├── match.py                # reuse fuzzy + optional embedding match (top-1 per endpoint)
    ├── path.py                 # edge costs, shortest_path, path answer + explanation
    └── parsers/
        └── llm_ollama.py       # optional chat_text for explanation polish (reuse explain)

tests/
├── fixtures/
│   └── path_graphs/            # competing routes, disconnected pair, same-node
├── contract/
│   ├── test_cli_help.py        # extend: path listed
│   └── test_cli_path.py
├── integration/
│   └── test_cli_path_cmd.py
└── unit/
    ├── test_path_weights.py
    ├── test_path_find.py
    └── test_path_explain.py
```

**Structure Decision**: Keep the existing single-package `cli.py` + `core/` layout. Add `core/path.py` for weighted path finding and answer formatting; reuse `core/match.py` for endpoint resolution. No web/mobile options.

## Complexity Tracking

> No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
