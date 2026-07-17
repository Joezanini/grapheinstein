# Implementation Plan: Local LLM Entity & Relation Extraction

**Branch**: `006-ollama-llm-extraction` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-ollama-llm-extraction/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Extend `grapheinstein index` with opt-in local LLM enrichment via `--enrich-llm`: for each eligible file/chunk, call a local **Ollama** model to extract domain **concept** entities (keeping AST functions from Tree-sitter) and infer typed relations (`implements`, `depends_on`, enrichment `mentions`). Every enrichment edge carries `provenance` (`extracted`|`inferred`), `confidence`, and grounded `evidence`. Configurable `--llm-model` (default `qwen3.5-2b-mlx:fp16-8gbGPU`) and `--llm-base-url`. Persist portable node-link `graph.json` at **schema_version `6.0.0`** (breaking vs `5.0.0`). Missing Ollama/model skips enrichment with a clear warning and still writes the structural graph.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing — Typer, NetworkX, pathspec, Rich, Loguru, PyYAML, tree-sitter (+ grammar wheels), pymupdf; optional `[media]`. New — Ollama local HTTP API via stdlib `urllib` (no new required Python package). External: Ollama daemon + pulled model tag.

**Storage**: Local filesystem — `graph.json` (NetworkX node-link envelope v6); `~/.grapheinstein/config.yaml` extended with `llm_model`, `llm_base_url`, `llm_confidence_threshold`

**Testing**: pytest; Typer `CliRunner`; fixture under `tests/fixtures/llm_project/`; unit tests with injectable fake LLM responses; contract tests for schema 6.0.0; integration tests skip or stub when Ollama unavailable

**Target Platform**: macOS / Linux developer workstations (Windows best-effort via pathlib); Ollama typically on `localhost:11434`

**Project Type**: Installable CLI package (extension of existing layout)

**Performance Goals**: Small fixture (few short files) completes offline enrichment in under 10 minutes on a local small model after Ollama is warm; sequential per-file/chunk calls; progress logged periodically

**Constraints**: Offline after Ollama + model present; respect `.gitignore`; overwrite outputs without prompt; reject schema 5.x (and older) on load; no cloud LLM default; confidence ≥ 0.5 (configurable); evidence must be grounded in chunk text

**Scale/Scope**: Concept extraction + relation inference stage after existing parsers; retain inventory + code + docs + PDF + media; no new query commands in this increment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Ollama localhost only; no cloud required; ignore rules retained |
| CLI-first parity | PASS | Enrich `index` with `--enrich-llm` / model flags; shared `core/` |
| Provenance graph | PASS | Enrichment edges labeled `extracted`/`inferred` + confidence + evidence |
| Multi-modal scope | PASS | Operates on text from code/docs/PDF/media chunks; does not add new modalities |
| Incremental simplicity | PASS | NetworkX + local JSON; stdlib HTTP; no graph DB |
| Schema/contract | PASS | Breaking bump to `6.0.0`; contracts + tests required |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R1–R3; quickstart offline scenarios |
| CLI-first parity | PASS | [contracts/cli.md](./contracts/cli.md) documents `--enrich-llm` and model options |
| Provenance graph | PASS | [data-model.md](./data-model.md) + [graph-json.md](./contracts/graph-json.md) |
| Multi-modal scope | PASS | Enrichment consumes prior modalities’ text; SQL/shell unchanged |
| Incremental simplicity | PASS | No Complexity Tracking violations; Ollama is external local service |
| Schema/contract | PASS | `5.0.0` → `6.0.0` break documented; load rejects old artifacts |

## Project Structure

### Documentation (this feature)

```text
specs/006-ollama-llm-extraction/
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
├── cli.py                 # index gains --enrich-llm, --llm-model, --llm-base-url
├── utils.py               # AppConfig: llm_model, llm_base_url, llm_confidence_threshold
└── core/
    ├── graph.py           # schema 6.0.0; concept nodes; implements/depends_on; confidence/evidence
    ├── index.py           # after media → optional LLM enrichment merge
    ├── references.py      # unchanged
    ├── visualize.py       # summary counts for concept / implements / depends_on
    └── parsers/
        ├── ...            # existing code/docs/pdf/media paths unchanged
        ├── llm_ollama.py  # Ollama HTTP client, tags check, chat+format
        └── llm_enrich.py  # chunk build, prompt/parse, merge concepts + edges

tests/
├── fixtures/
│   └── llm_project/       # code + doc concept fixture; ignored/; stub responses in unit tests
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Keep `cli.py` + `core/` layout. Add LLM modules under `core/parsers/` (same plugin-style pattern as media). No web/mobile options. No separate top-level `extract/` package.

## Complexity Tracking

> No constitution violations. Ollama is an external local process (like Tesseract), not a required cloud backend.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
