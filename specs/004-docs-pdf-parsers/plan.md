# Implementation Plan: Docs and PDF Parsers

**Branch**: `004-docs-pdf-parsers` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-docs-pdf-parsers/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Extend `grapheinstein index` with opt-in documentation and PDF structure enrichment: `--include-docs` parses Markdown / TXT / RST for section headings and links; `--include-pdfs` extracts text via PyMuPDF and chunks by sections. Emit `heading` nodes plus `section_of` and `mentions` edges (all `extracted`). Persist portable node-link `graph.json` at **schema_version `4.0.0`** (breaking vs `3.0.0`). Default index (flags off) keeps schema 4 envelope but does not run doc/PDF structure parsers. Per-file parse failures warn and continue.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing — Typer, NetworkX, pathspec, Rich, Loguru, PyYAML, tree-sitter (+ grammar wheels). New — `pymupdf` (PyMuPDF) for PDF text/TOC. Docs parsers: stdlib + light regex/line scanners (no Markdown/RST framework required for v1; see research R3).

**Storage**: Local filesystem — `graph.json` (NetworkX node-link envelope v4); optional `~/.grapheinstein/config.yaml` (may later mirror flags; CLI flags are the v1 contract)

**Testing**: pytest; Typer `CliRunner`; fixture project under `tests/fixtures/docs_pdf_project/`; unit tests for MD/TXT/RST/PDF extractors and link resolution; contract tests for schema 4.0.0

**Target Platform**: macOS / Linux developer workstations (Windows best-effort via pathlib)

**Project Type**: Installable CLI package (extension of existing layout)

**Performance Goals**: Index a mixed fixture (dozens of docs + a few multi-section PDFs) offline in under 2 minutes with both flags; stream PDF pages without loading entire corpora into memory beyond one document at a time

**Constraints**: Offline-only after install; respect `.gitignore`; overwrite outputs without prompt; reject schema 3.x (and older) graphs on load; omit ambiguous `mentions`; no OCR for image-only PDFs; no LLM-inferred concepts

**Scale/Scope**: Docs (`.md`/`.markdown`, `.txt`, `.rst`/`.rest`) + PDF section structure; retain inventory + code extract; no query commands; no image/audio/video

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | PyMuPDF + local file parsers; no cloud; ignore rules retained |
| CLI-first parity | PASS | Enrich `index` with `--include-docs` / `--include-pdfs`; shared `core/` |
| Provenance graph | PASS | New edges typed + `provenance: extracted` only |
| Multi-modal scope | PASS | Docs + PDF in; image/media out; code retained from prior feature |
| Incremental simplicity | PASS | NetworkX + local JSON; rule-based extract; no graph DB |
| Schema/contract | PASS | Breaking bump to `4.0.0`; contracts + tests required |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R1/R5; quickstart offline scenarios |
| CLI-first parity | PASS | [contracts/cli.md](./contracts/cli.md) documents both flags |
| Provenance graph | PASS | [data-model.md](./data-model.md) + [graph-json.md](./contracts/graph-json.md) |
| Multi-modal scope | PASS | Docs + PDF; OCR/media deferred (R6) |
| Incremental simplicity | PASS | No Complexity Tracking violations; pymupdf is constitution-aligned PDF lib |
| Schema/contract | PASS | `3.0.0` → `4.0.0` break documented; load rejects old artifacts |

## Project Structure

### Documentation (this feature)

```text
specs/004-docs-pdf-parsers/
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
├── cli.py                 # index gains --include-docs / --include-pdfs; summary counts
├── utils.py               # optional config keys later; flag wiring via index API
└── core/
    ├── graph.py           # schema 4.0.0; heading nodes; section_of / mentions
    ├── index.py           # after code extract → optional docs/PDF merge
    ├── references.py      # unchanged basename references
    ├── visualize.py       # summary counts for heading + new edge types
    └── parsers/
        ├── ...            # existing Tree-sitter code path unchanged
        ├── docs.py        # Markdown / TXT / RST heading + link extract
        ├── pdf.py         # PyMuPDF extract + section chunk
        └── resolve_docs.py  # link/heading target resolution → mentions

tests/
├── fixtures/
│   └── docs_pdf_project/  # nested MD/RST/TXT, sample PDF, corrupt PDF, ignored/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Keep `cli.py` + `core/` layout. Add docs/PDF modules beside the existing Tree-sitter package under `core/parsers/` (plugin-style siblings, not a new top-level `ingest/`). No web/mobile options.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
