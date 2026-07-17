# Research: Media Parsers

**Feature**: `005-media-parsers`  
**Date**: 2026-07-17

## R1. OCR library

**Decision**: Use **pytesseract** + **Pillow** for image OCR. Require a local **Tesseract OCR** system binary. Ship both Python packages under optional extra **`[media]`** (not required core deps). Prefer `pytesseract.image_to_string` with Pillow `Image.open` for PNG/JPEG/WebP/GIF.

**Rationale**: Spec allows EasyOCR or pytesseract. pytesseract is lighter, fully offline after Tesseract install, and matches constitution incremental simplicity. EasyOCR pulls heavy deep-learning stacks that bloat default/dev installs even as an optional path. Pillow is the standard image I/O companion.

**Alternatives considered**:
- **EasyOCR** — stronger out-of-box multilingual OCR, but large torch dependency; defer as future alternate backend behind the same parser interface.
- Required core OCR deps — rejected; media is opt-in via `--transcribe-media` and should not weigh down base `pip install`.
- Image metadata-only (no OCR) — insufficient for FR-001.

## R2. Transcription library

**Decision**: Use **faster-whisper** (`WhisperModel.transcribe`) as the local transcription engine under optional extra **`[media]`**. Default model size **`base`** on **CPU** (`device="cpu"`) for predictable offline runs. Use returned **segments** (`start`/`end`/`text`) as the primary chunking input. Document **ffmpeg** as a system dependency for decoding many audio/video containers (faster-whisper’s audio decode path).

**Rationale**: Spec allows faster-whisper or whisper.cpp. faster-whisper is Python-native, returns timed segments suitable for chunk nodes, and is widely used for local Whisper. whisper.cpp requires separate binary/bindings packaging and is harder to keep portable across macOS/Linux for a Typer CLI v1.

**Alternatives considered**:
- **whisper.cpp** — excellent performance; deferred due to packaging complexity.
- OpenAI cloud Whisper API — violates local-first constitution.
- Always-on transcription without extras — rejected (heavyweight; flag-gated).

## R3. Optional dependency and missing-tooling behavior

**Decision**:

- Add `[project.optional-dependencies] media = ["pytesseract", "Pillow", "faster-whisper"]` (pin ranges in implementation).
- When `--transcribe-media` is set and `pytesseract` / `faster-whisper` / `PIL` cannot be imported → **exit non-zero before writing a success graph**, with a message to `pip install 'grapheinstein[media]'` (and system Tesseract/ffmpeg notes).
- When imports succeed but Tesseract binary or ffmpeg is missing → **per-file warn-and-skip** for affected OCR/A-V files (do not abort whole index); increment `parse_skips`.
- Without `--transcribe-media`, do not import media libs (lazy import) so base installs stay fast.

**Rationale**: Spec forbids silent “success” that pretends media was processed. Fail-fast on missing Python extras when the user explicitly opted in; tolerate missing system binaries on individual files so mixed projects still produce a graph.

**Alternatives considered**:
- Soft-skip entire media pass with warning when extras missing — weaker agent signal; rejected for the flag-on path.
- Bundle Tesseract/ffmpeg wheels — out of scope for v1.

## R4. Schema version bump

**Decision**: Bump `schema_version` to **`5.0.0`**. Widen allow-lists for node types `media_text` and `transcript_chunk`, and edge type `related_to`. Loaders **reject** `4.0.0` and older with a clear re-index message (fail-closed). No silent migration.

**Rationale**: Constitution: schema changes are breaking; consumers must detect new media nodes/edges and first-class `inferred` media links.

**Alternatives considered**:
- Stay on `4.0.0` and widen types — rejected (no capability signal).
- Reuse only `heading` for OCR/transcript — rejected; different modality semantics and metadata (time ranges vs lines/pages).

## R5. Node types and identity

**Decision**:

| Kind | `type` | `id` pattern | Required metadata |
|------|--------|--------------|-------------------|
| OCR text | `media_text` | `{file}::media_text::{ordinal}` | `file`, `text`, `source` (`ocr`), optional `engine` |
| Transcript chunk | `transcript_chunk` | `{file}::transcript_chunk::{ordinal}` | `file`, `text`, `source` (`whisper`), `start_sec`, `end_sec` (floats), optional `ordinal` |

- `ordinal` is 1-based within the file.
- Empty/whitespace OCR or empty transcript → **no** content nodes (file node remains).
- Multiple OCR blocks: v1 may emit a **single** `media_text` node with full concatenated text (ordinal `1`); splitting by OCR bounding boxes is optional later.

**Rationale**: Distinct types keep visualize/status counts clear and avoid overloading `heading`. Timed chunks match faster-whisper segments.

**Alternatives considered**:
- Type `heading` with `source: ocr|whisper` — conflates doc structure with media.
- UUID ids — poor agent UX / diffs.

## R6. Edges: containment and media linking

**Decision**:

- **Containment**: Reuse **`section_of`** with `provenance: extracted` — `source` = `media_text` or `transcript_chunk` id, `target` = containing media **file** id (always file for v1; no nested media sections).
- **Media → code/docs links**: New edge type **`related_to`** with `provenance: inferred`:
  - **Filename similarity**: media file stem (basename without extension) matches an indexed **code or doc/PDF file** stem or basename **uniquely** (same unambiguous policy as `references`). Link media file → target file.
  - **Content overlap**: distinctive token/n-gram overlap between media-derived text (OCR or chunk) and indexed file/heading/code-entity text; create edge from media_text/chunk (preferred) or media file → unique target only when score clears a conservative threshold and the target is unique.
- Do **not** emit `related_to` when ambiguous. Do **not** reuse `references`/`mentions` for these heuristic links (those remain `extracted`).

**Rationale**: Spec requires inferred provenance for similarity/content links; a dedicated `related_to` type keeps trust filtering clean. `section_of` already means “part of parent structure” for docs/PDF.

**Alternatives considered**:
- Overload `references` with `inferred` — confuses inventory basename-mention semantics.
- Embeddings/cosine only — deferred; lexical overlap is enough for fixtures and stays local without requiring sentence-transformers in this increment.

## R7. CLI flag, long-file warnings, pipeline order

**Decision**:

- Add boolean flag **`--transcribe-media`** (default **false**) to `index` (and default-path rewriter).
- Persist `graph.transcribe_media: true/false` on the artifact.
- **Long-file warn**: before processing each A/V (and optionally large images), if **size > 100 MB** OR (when duration is obtainable) **duration > 600 seconds**, log a warning naming the relative path; continue processing (warn-and-continue). Duration via faster-whisper `info` / ffprobe-best-effort; if duration unknown, size-only check still applies.
- Pipeline after docs/PDF:

  1. Inventory + references + code + optional docs + optional PDFs (existing)
  2. If `--transcribe-media`: OCR images → transcript A/V → chunk → `section_of`
  3. If `--transcribe-media`: build `related_to` inferred links
  4. Write schema `5.0.0`

**Rationale**: Matches FR-003/FR-004 and prior flag patterns (`--include-docs` / `--include-pdfs`).

**Alternatives considered**:
- Separate `--ocr-images` / `--transcribe-av` — out of scope; single flag per spec.
- Abort on long files — rejected (warn-and-continue).

## R8. Transcript chunking policy

**Decision**: Prefer **faster-whisper segments** as chunk boundaries. If a segment is empty, drop it. If many tiny segments, **merge consecutive segments** until combined text length ≥ **400 characters** or combined duration ≥ **30 seconds**, then emit a chunk (flush remainder at end). Short overall transcripts may yield a single chunk.

**Rationale**: Satisfies FR-011 without arbitrary mid-sentence splits; timed metadata preserved via merged `start_sec`/`end_sec`.

## R9. Supported extensions

**Decision**:

| Modality | Extensions (case-insensitive) |
|----------|-------------------------------|
| Images | `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.tif`, `.tiff`, `.bmp` |
| Audio | `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.aac` |
| Video | `.mp4`, `.mov`, `.mkv`, `.webm` |

Unsupported extension under media pass: skip silently (not a parse_skip). Unreadable/corrupt/supported-but-failing: warn + `parse_skips++`.

## R10. Visualize / status

**Decision**: Extend `GraphStats` and console summaries with `media_text_count`, `transcript_chunk_count`, `related_to_count`. Status/visualize load **only** schema `5.0.0`.

## R1–R10 resolution summary

All Technical Context unknowns resolved: pytesseract+Pillow OCR; faster-whisper transcription; optional `[media]` extras with fail-fast on missing Python deps when flagged; schema `5.0.0`; `media_text` / `transcript_chunk` / `related_to`; `section_of` containment; long-file warn thresholds; segment-based chunk merge.
