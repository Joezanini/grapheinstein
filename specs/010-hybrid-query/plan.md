# Implementation Plan: Hybrid Natural-Language Query

**Branch**: `010-hybrid-query` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-hybrid-query/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Add `grapheinstein query "<question>" --input <graph> --output <subgraph> [--k 20]`: load a portable schema `6.0.0` graph, retrieve up to `--k` primary chunk/node hits via local fuzzy + optional Ollama embeddings over chunk-capable text, expand with undirected graph traversal, write a supporting subgraph (atomic validated write), emit a textual visualization summary, and generate a local-LLM answer with citations restricted to subgraph nodes/edges. Offline-capable; retrieval + subgraph succeed when the answer model is down; no cloud APIs; no new required packages.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing — Typer, NetworkX, Rich, Loguru, PyYAML; reuse `core/match.py` (`score_nodes` / `select_matches`), `core/explain.py` (`undirected_neighborhood`, artifact write patterns), `core/parsers/llm_ollama.py` (`embed_texts`, `chat_text`, `check_ready`). No sentence-transformers, FAISS, or vector DB for v1.

**Storage**: Local filesystem — read/write portable `.json` / `.json.gz` graph artifacts; config under `~/.grapheinstein/config.yaml` and `--config`

**Testing**: pytest; Typer `CliRunner`; unit tests for chunk corpus, hybrid expand, citation filter, viz summary; contract tests for CLI help/flags + subgraph metadata + answer JSON shape; integration on fixture graphs with injectable fake embed/chat

**Target Platform**: macOS / Linux developer workstations (Windows best-effort via pathlib)

**Project Type**: Installable CLI package (extend existing `cli.py` + `core/` layout)

**Performance Goals**: Fixture query with warm local model ≤60s (≤120s cold) per SC-001; primary scoring interactive on ≤10k chunk candidates; neighborhood dominated by graph size + `--k`

**Constraints**: Offline-capable; no cloud APIs; `--k` ≥ 1 with documented max; no-evidence → non-zero exit and no success subgraph; LLM-down → still write subgraph + viz summary + clear skip; preserve edge `type` + `provenance`; stay on schema `6.0.0` with additive optional query metadata; citations must reference only subgraph entities

**Scale/Scope**: Query command only — no new parsers or node/edge type allow-lists; modalities already in the input graph participate as chunk/node text; slash/MCP out of scope

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Local graph files + local Ollama; embeddings optional via same runner; no cloud |
| CLI-first parity | PASS | New `query` subcommand; library helpers in `core/` for later MCP reuse |
| Provenance graph | PASS | Subgraph copies existing edges with `type` + `provenance`; answer/citations are narrative, not unlabeled mutation |
| Multi-modal scope | PASS | Query-only; chunk text from existing node metadata (media/transcript/`text` fields + composed search text for other nodes) |
| Incremental simplicity | PASS | NetworkX + local files; reuse match/explain/llm_ollama; no vector DB |
| Schema/contract | PASS | Remain `6.0.0`; additive optional `graph` query fields; CLI + answer JSON contracts + tests |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R1–R7; quickstart offline paths |
| CLI-first parity | PASS | [contracts/cli.md](./contracts/cli.md) documents `query` surface |
| Provenance graph | PASS | [data-model.md](./data-model.md) / [graph-json.md](./contracts/graph-json.md) preserve edge attrs |
| Multi-modal scope | PASS | No parser changes; chunk corpus defined over existing node text |
| Incremental simplicity | PASS | No Complexity Tracking violations; no new required packages |
| Schema/contract | PASS | `6.0.0` retained; query metadata optional; answer JSON versioned separately |

## Project Structure

### Documentation (this feature)

```text
specs/010-hybrid-query/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── graph-json.md
│   └── query-answer-json.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/grapheinstein/
├── cli.py                      # new `query` command; _KNOWN_COMMANDS
├── utils.py                    # query_* / match config keys + CLI overrides
└── core/
    ├── graph.py                # reuse load_artifact / write_artifact_dict
    ├── match.py                # reuse score_nodes / select_matches (chunk corpus subset)
    ├── explain.py              # reuse undirected_neighborhood (+ patterns)
    ├── query.py                # hybrid retrieve → expand → subgraph → answer + viz
    └── parsers/
        └── llm_ollama.py       # reuse chat_text + embed_texts

tests/
├── fixtures/
│   └── query_graphs/           # chunk-rich graphs + known answerable questions
├── contract/
│   ├── test_cli_help.py        # extend: query listed
│   └── test_cli_query.py
├── integration/
│   └── test_cli_query_cmd.py
└── unit/
    ├── test_query_chunks.py
    ├── test_query_hybrid.py
    ├── test_query_citations.py
    └── test_query_viz.py
```

**Structure Decision**: Keep the existing single-package `cli.py` + `core/` layout. Add `core/query.py` for hybrid orchestration; reuse `match.py`, `undirected_neighborhood`, and Ollama helpers. No web/mobile options.

## Complexity Tracking

> No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
