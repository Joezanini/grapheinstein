# Data Model: Media Parsers

**Feature**: `005-media-parsers`  
**Schema version**: `5.0.0` (breaking vs `4.0.0`)

## Entities

### Project Root

Unchanged: absolute path supplied to `index`; node ids are POSIX-relative to this root.

### Index Run Options

| Field | Type | Rules |
|-------|------|-------|
| `include_docs` | bool | Retained from schema 4 |
| `include_pdfs` | bool | Retained from schema 4 |
| `transcribe_media` | bool | Default `false`; when true, run OCR + A/V transcription + media linking |

Persisted on artifact `graph.transcribe_media` (and retained docs/PDF flags) for the run that produced the file.

### Graph Node (file / dir / code / heading)

Unchanged from schema 4.x, except media file paths may receive attached content nodes when transcription is enabled.

### Graph Node (media_text)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `id` | string | yes | `{file}::media_text::{ordinal}` (ordinal 1-based int as decimal string) |
| `type` | string | yes | Exactly `media_text` |
| `metadata` | object | yes | Must include `file` (file node id), `text` (non-empty string), `source` (`ocr`). Optional: `engine` (e.g. `tesseract`), `ordinal` |

**Rules**:
- `metadata.file` MUST equal an existing `type: file` node `id`
- Do not create nodes for empty/whitespace-only OCR results
- Emitted only when `transcribe_media` ran successfully for that image

### Graph Node (transcript_chunk)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `id` | string | yes | `{file}::transcript_chunk::{ordinal}` |
| `type` | string | yes | Exactly `transcript_chunk` |
| `metadata` | object | yes | Must include `file`, `text` (non-empty), `source` (`whisper`), `start_sec` (number ≥ 0), `end_sec` (number ≥ `start_sec`). Optional: `ordinal` |

**Rules**:
- Chunks follow research R8 merge policy (segment-based)
- No chunks when transcription yields no speech text
- Emitted only when `transcribe_media` ran for that A/V file

### Contains / References / Defines / Imports / Calls / Mentions

Unchanged from schema 4.x semantics and provenance (`extracted` for produced edges).

### Section-of Edge (extended)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `source` | string | yes | Child `heading`, `media_text`, or `transcript_chunk` id |
| `target` | string | yes | Parent `heading` id or containing `file` id |
| `type` | string | yes | Exactly `section_of` |
| `provenance` | string | yes | Exactly `extracted` |

**Media rules**:
- Every `media_text` / `transcript_chunk` has exactly one `section_of` edge to its media **file**
- No self-loops; both endpoints must exist

### Related-to Edge (new)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `source` | string | yes | Media `file`, `media_text`, or `transcript_chunk` id |
| `target` | string | yes | Related `file`, `heading`, or code entity id |
| `type` | string | yes | Exactly `related_to` |
| `provenance` | string | yes | Exactly `inferred` |
| `reason` | string | no | Optional edge attr: `filename` or `content` (implementation MAY store on edge data) |

**Rules**:
- Create only when filename similarity or content overlap resolves **unambiguously**
- Skip ambiguous multi-match cases (no invented targets)
- At most one `related_to` edge per ordered pair (DiGraph single edge)
- Not emitted when `transcribe_media` is off

### Long-File Warning (runtime, not a graph entity)

Emitted to human-readable progress/error stream when a media file exceeds **100 MB** or **600 seconds** duration (when known). Does not create a graph node; does not by itself fail the index.

### Parse Skip Accounting

| Field | Location | Rules |
|-------|----------|-------|
| `parse_skips` | graph metadata and/or stats | Non-negative int; includes code + docs + PDF + media per-file failures for the run |

### Graph Artifact

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `schema_version` | string | yes | `"5.0.0"` |
| `directed` | boolean | yes | `true` |
| `multigraph` | boolean | yes | `false` |
| `graph` | object | yes | `project_root`, `generated_at`; MAY include `languages`, `include_docs`, `include_pdfs`, `transcribe_media`, `parse_skips` |
| `nodes` | array | yes | Prior types + `media_text` + `transcript_chunk` |
| `links` | array | yes | Prior edge types + `related_to` with `type` + `provenance` |

## Validation Rules (load-time)

1. Reject artifacts whose `schema_version` ≠ `5.0.0`
2. Reject unknown node/edge types outside the schema 5 allow-list
3. Reject edges missing `provenance` or with values outside `{extracted, inferred}`
4. Reject `related_to` edges whose provenance is not `inferred`
5. Reject `media_text` / `transcript_chunk` missing required metadata fields
6. Reject `section_of` from media content nodes whose target is not the declared `metadata.file` when that field is present (soft check recommended in tests)

## State / Lifecycle

```text
index (flags) → discover inventory → references → code → [docs] → [pdfs]
  → [if transcribe_media: check [media] imports]
  → [OCR images] → [transcribe A/V + chunk] → [related_to linking]
  → write graph.json (5.0.0) → overwrite previous artifact
```

No incremental merge across runs: each successful index replaces the output graph for that path.
