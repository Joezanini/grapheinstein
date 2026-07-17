# Implementation Plan: Explain Concept Subgraph

**Branch**: `008-explain-concept` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-explain-concept/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Add `grapheinstein explain <concept> --input <graph> --output <subgraph>`: load a portable schema `6.0.0` graph, fuzzy-match (and optionally locally embed) nodes to the concept phrase, extract a 1–2 hop undirected neighborhood (default 2, top-N matches merged), write a validated subgraph via existing atomic I/O, and print a natural-language summary on stderr using local Ollama when available. Matching and subgraph export succeed without the LLM; vector matching is best-effort and skipped when embeddings are unavailable.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing — Typer, NetworkX, Rich, Loguru, PyYAML; Ollama via stdlib `urllib` (reuse/extend `core/parsers/llm_ollama.py`). Matching uses **stdlib** (`difflib`, string normalization). Optional vector scores via Ollama `/api/embeddings` (no new required package). No sentence-transformers in the required install for v1.

**Storage**: Local filesystem — read/write portable `.json` / `.json.gz` graph artifacts; config under `~/.grapheinstein/config.yaml` and `--config`

**Testing**: pytest; Typer `CliRunner`; unit tests for match scoring, hop extraction, truncation, summary prompt; contract tests for CLI help/flags + subgraph schema; integration on fixture graphs with injectable fake LLM/embeddings

**Target Platform**: macOS / Linux developer workstations (Windows best-effort via pathlib)

**Project Type**: Installable CLI package (extend existing `cli.py` + `core/` layout)

**Performance Goals**: Fixture explain with warm local model ≤30s (≤60s cold start) per SC-001; fuzzy match on ≤10k nodes interactive; neighborhood extract dominated by graph size, not I/O

**Constraints**: Offline-capable; no cloud APIs; hops ∈ {1,2}; no-match → non-zero exit and no success subgraph; LLM-down → still write subgraph + clear skip message; preserve edge `type` + `provenance`; stay on schema `6.0.0` with additive optional explain metadata

**Scale/Scope**: Query command only — no new parsers or node/edge type allow-lists; modalities already in the input graph are explainable as nodes; slash/MCP out of scope

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Local graph files + local Ollama; embeddings optional via same local runner; no cloud |
| CLI-first parity | PASS | New `explain` subcommand; library helpers in `core/` for later MCP reuse |
| Provenance graph | PASS | Subgraph copies existing edges with `type` + `provenance`; summary is narrative, not unlabeled mutation |
| Multi-modal scope | PASS | Query-only; any existing node types (code, docs, PDF, media, concepts, …) matchable |
| Incremental simplicity | PASS | NetworkX + local files; stdlib fuzzy; no vector DB |
| Schema/contract | PASS | Remain `6.0.0`; additive optional `graph` explain fields; CLI contract + tests |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R1–R5; quickstart offline paths |
| CLI-first parity | PASS | [contracts/cli.md](./contracts/cli.md) documents `explain` surface |
| Provenance graph | PASS | [data-model.md](./data-model.md) / [graph-json.md](./contracts/graph-json.md) preserve edge attrs |
| Multi-modal scope | PASS | No parser changes; matching uses node id/type/metadata text |
| Incremental simplicity | PASS | No Complexity Tracking violations; Ollama embeddings optional, not required |
| Schema/contract | PASS | `6.0.0` retained; explain metadata optional and documented |

## Project Structure

### Documentation (this feature)

```text
specs/008-explain-concept/
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
├── cli.py                      # new `explain` command; _KNOWN_COMMANDS
├── utils.py                    # explain_* / match config keys + CLI overrides
└── core/
    ├── graph.py                # reuse load_artifact / write_artifact_dict; optional artifact→DiGraph helper
    ├── explain.py              # orchestrate: match → neighborhood → write → summarize
    ├── match.py                # fuzzy scoring + optional embedding rank merge
    └── parsers/
        └── llm_ollama.py       # add free-text chat + optional embeddings helpers

tests/
├── fixtures/
│   └── explain_graphs/         # small graphs with known concepts + neighborhoods
├── contract/
│   ├── test_cli_help.py        # extend: explain listed
│   └── test_cli_explain.py
├── integration/
│   └── test_cli_explain_cmd.py
└── unit/
    ├── test_match.py
    ├── test_explain_neighborhood.py
    └── test_explain_summary.py
```

**Structure Decision**: Keep the existing single-package `cli.py` + `core/` layout. Add `core/match.py` and `core/explain.py` for pure query logic; extend `llm_ollama.py` for plain-text generation and optional embeddings. No web/mobile options.

## Complexity Tracking

> No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
