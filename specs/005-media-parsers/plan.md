# Implementation Plan: Media Parsers

**Branch**: `005-media-parsers` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-media-parsers/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Extend `grapheinstein index` with opt-in media enrichment via `--transcribe-media`: offline image OCR (pytesseract + Pillow + system Tesseract) produces `media_text` nodes; local audio/video transcription (faster-whisper) produces `transcript_chunk` nodes. Attach content to media files with `section_of` (`extracted`). Link media to related code/docs via unambiguous filename similarity or content overlap using `related_to` (`inferred`). Warn (and continue) on long media files (>10 min or >100 MB). Persist portable node-link `graph.json` at **schema_version `5.0.0`** (breaking vs `4.0.0`). Media Python deps live in optional extra `[media]`; missing extras with the flag set fail closed before a success write.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing — Typer, NetworkX, pathspec, Rich, Loguru, PyYAML, tree-sitter (+ grammar wheels), pymupdf. New (optional `[media]`) — `pytesseract`, `Pillow`, `faster-whisper`. System: Tesseract OCR binary; ffmpeg for many A/V containers.

**Storage**: Local filesystem — `graph.json` (NetworkX node-link envelope v5); optional `~/.grapheinstein/config.yaml` (CLI flag is the v1 contract)

**Testing**: pytest; Typer `CliRunner`; fixture project under `tests/fixtures/media_project/`; unit tests for OCR/transcript merge, long-file warn, `related_to` resolution; contract tests for schema 5.0.0 (mock/stub engines where full Whisper/Tesseract is unavailable in CI)

**Target Platform**: macOS / Linux developer workstations (Windows best-effort via pathlib)

**Project Type**: Installable CLI package (extension of existing layout)

**Performance Goals**: Short-fixture media index (few small images + one short speech clip) completes offline in under 5 minutes on CPU with `base` Whisper after first model download/cache; stream/process one media file at a time

**Constraints**: Offline after install + first local model cache; respect `.gitignore`; overwrite outputs without prompt; reject schema 4.x (and older) on load; warn-and-continue on long files; no cloud OCR/ASR; unambiguous `related_to` only

**Scale/Scope**: Image OCR + A/V transcription + inferred media links; retain inventory + code + docs + PDF; no query-command changes beyond schema load

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Local Tesseract + faster-whisper; no cloud; ignore rules retained |
| CLI-first parity | PASS | Enrich `index` with `--transcribe-media`; shared `core/` |
| Provenance graph | PASS | `section_of` extracted; `related_to` inferred; typed edges |
| Multi-modal scope | PASS | Image + audio/video in; code/docs/PDF retained |
| Incremental simplicity | PASS | NetworkX + local JSON; optional `[media]` extras; no graph DB |
| Schema/contract | PASS | Breaking bump to `5.0.0`; contracts + tests required |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R1–R3; quickstart offline scenarios |
| CLI-first parity | PASS | [contracts/cli.md](./contracts/cli.md) documents `--transcribe-media` |
| Provenance graph | PASS | [data-model.md](./data-model.md) + [graph-json.md](./contracts/graph-json.md) |
| Multi-modal scope | PASS | Image OCR + A/V transcription; SQL/shell unchanged |
| Incremental simplicity | PASS | Optional extras justified; no Complexity Tracking violations beyond noted optional weight |
| Schema/contract | PASS | `4.0.0` → `5.0.0` break documented; load rejects old artifacts |

## Project Structure

### Documentation (this feature)

```text
specs/005-media-parsers/
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
├── cli.py                 # index gains --transcribe-media; summary counts
├── utils.py               # flag wiring / optional config later
└── core/
    ├── graph.py           # schema 5.0.0; media_text; transcript_chunk; related_to
    ├── index.py           # after docs/PDF → optional media merge + linking
    ├── references.py      # unchanged basename references
    ├── visualize.py       # summary counts for new node/edge types
    └── parsers/
        ├── ...            # existing code/docs/pdf paths unchanged
        ├── media_ocr.py   # image OCR → media_text + section_of
        ├── media_av.py    # faster-whisper → transcript_chunk + section_of
        └── media_link.py  # related_to inferred filename/content links

tests/
├── fixtures/
│   └── media_project/     # images with text, short audio, large stub, corrupt, ignored/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Keep `cli.py` + `core/` layout. Add media modules as plugin-style siblings under `core/parsers/` (same pattern as docs/PDF). No web/mobile options.

## Complexity Tracking

> Optional `[media]` extras add heavyweight native/ML deps only when users opt in. Not a constitution violation; recorded for transparency.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
