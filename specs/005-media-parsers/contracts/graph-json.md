# Contract: graph.json (schema_version 5.0.0)

**Feature**: `005-media-parsers`  
**Format**: JSON document compatible with NetworkX node-link data, plus required envelope fields  
**Breaks**: schema `4.0.0` (docs/PDF without media types) — readers MUST reject older artifacts; users re-index

## Top-level object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Must be `"5.0.0"` for this feature |
| `directed` | boolean | yes | Must be `true` |
| `multigraph` | boolean | yes | Must be `false` |
| `graph` | object | yes | Graph-level metadata |
| `nodes` | array | yes | Node list |
| `links` | array | yes | Edge list |

### `graph` metadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_root` | string | yes | Absolute path that was indexed |
| `generated_at` | string | yes | ISO-8601 UTC timestamp |
| `languages` | array of strings | no | Enabled code language ids for this run |
| `include_docs` | boolean | no | Whether docs structure enrichment ran |
| `include_pdfs` | boolean | no | Whether PDF structure enrichment ran |
| `transcribe_media` | boolean | no | Whether media OCR/transcription/linking ran |
| `parse_skips` | integer | no | Count of per-file structure/media skips |

## Nodes

### File / directory / code entity / heading

Unchanged from schema 4.0.0 allow-lists and id conventions.

### media_text

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | `{file}::media_text::{ordinal}` |
| `type` | string | yes | `"media_text"` |
| `metadata` | object | yes | Must include `file`, `text`, `source` (`ocr`) |

Example:

```json
{
  "id": "assets/login.png::media_text::1",
  "type": "media_text",
  "metadata": {
    "file": "assets/login.png",
    "text": "Sign in with SSO",
    "source": "ocr",
    "engine": "tesseract",
    "ordinal": 1
  }
}
```

### transcript_chunk

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | `{file}::transcript_chunk::{ordinal}` |
| `type` | string | yes | `"transcript_chunk"` |
| `metadata` | object | yes | Must include `file`, `text`, `source` (`whisper`), `start_sec`, `end_sec` |

Example:

```json
{
  "id": "demos/setup.mp4::transcript_chunk::1",
  "type": "transcript_chunk",
  "metadata": {
    "file": "demos/setup.mp4",
    "text": "First install the package with pip.",
    "source": "whisper",
    "start_sec": 0.0,
    "end_sec": 4.2,
    "ordinal": 1
  }
}
```

## Links (edges)

Each element MUST include:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | yes | Source node `id` |
| `target` | string | yes | Target node `id` |
| `type` | string | yes | One of: `contains`, `references`, `defines`, `imports`, `calls`, `section_of`, `mentions`, `related_to` |
| `provenance` | string | yes | `"extracted"` or `"inferred"` |

### `section_of` (media containment)

```json
{
  "source": "assets/login.png::media_text::1",
  "target": "assets/login.png",
  "type": "section_of",
  "provenance": "extracted"
}
```

```json
{
  "source": "demos/setup.mp4::transcript_chunk::1",
  "target": "demos/setup.mp4",
  "type": "section_of",
  "provenance": "extracted"
}
```

### `related_to` (inferred media linking)

```json
{
  "source": "assets/login.png",
  "target": "src/login.py",
  "type": "related_to",
  "provenance": "inferred"
}
```

Optional implementation attribute (MAY be present):

```json
{
  "source": "demos/setup.mp4::transcript_chunk::1",
  "target": "docs/install.md::heading::pip-install::12",
  "type": "related_to",
  "provenance": "inferred",
  "reason": "content"
}
```

**Rules**:
- `related_to` MUST use `provenance: "inferred"`
- OCR/transcript `section_of` MUST use `provenance: "extracted"`
- Ambiguous targets MUST NOT produce a `related_to` edge

## Allow-lists (schema 5.0.0)

**Node types**: `file`, `dir`, `function`, `class`, `method`, `heading`, `media_text`, `transcript_chunk`

**Edge types**: `contains`, `references`, `defines`, `imports`, `calls`, `section_of`, `mentions`, `related_to`

## Compatibility

| Reader action | schema ≤ 4.0.0 | schema 5.0.0 |
|---------------|----------------|--------------|
| `visualize` / `status` / load | Reject with re-index message | Accept |
| Agents filtering provenance | N/A | Filter `related_to` as `inferred`; media structure as `extracted` |

## Minimal valid empty-ish graph

A valid schema 5 graph may contain only inventory nodes/edges (no media nodes) when `--transcribe-media` was off or no media files existed. `schema_version` MUST still be `"5.0.0"`.
