# Contract: graph.json (schema_version 6.0.0)

**Feature**: `006-ollama-llm-extraction`  
**Format**: JSON document compatible with NetworkX node-link data, plus required envelope fields  
**Breaks**: schema `5.0.0` and older — readers MUST reject old artifacts; users re-index

## Top-level object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Must be `"6.0.0"` for this feature |
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
| `languages` | array | no | Enabled code languages for the run |
| `include_docs` | boolean | no | Whether docs enrichment ran |
| `include_pdfs` | boolean | no | Whether PDF enrichment ran |
| `transcribe_media` | boolean | no | Whether media enrichment ran |
| `enrich_llm` | boolean | no | Whether LLM enrichment was requested |
| `llm_model` | string | no | Model tag used or attempted when enrichment requested |

## Nodes

Each element MUST include:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Stable node id |
| `type` | string | yes | See allow-list below |
| `metadata` | object | yes | Extensible map; may be `{}` for file/dir |

### `concept` (new)

```json
{
  "id": "concept::auth-middleware",
  "type": "concept",
  "metadata": {
    "name": "Auth Middleware",
    "kind": "domain_term"
  }
}
```

**Rules**:
- `id` MUST match `concept::{slug}`
- `metadata.name` MUST be a non-empty string
- Optional `metadata.kind`: `domain_term` | `library` | `other`

Prior node types (`file`, `dir`, `function`, `class`, `method`, `heading`, `media_text`, `transcript_chunk`) retain schema 5 shapes.

## Links (edges)

Each element MUST include:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | yes | Source node `id` |
| `target` | string | yes | Target node `id` |
| `type` | string | yes | See allow-list below |
| `provenance` | string | yes | `"extracted"` or `"inferred"` |

Optional / conditional attributes:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `confidence` | number | conditional | Float in `[0.0, 1.0]`; **required** on enrichment edges below |
| `evidence` | string | conditional | Non-empty grounded snippet; **required** on enrichment edges below |
| `reason` | string | no | Retained for media `related_to` |

### Enrichment edges requiring confidence + evidence

#### `mentions` → concept (extracted term attachment)

```json
{
  "source": "docs/auth.md",
  "target": "concept::auth-middleware",
  "type": "mentions",
  "provenance": "extracted",
  "confidence": 0.92,
  "evidence": "Auth Middleware validates JWT on each request"
}
```

#### `implements` (inferred)

```json
{
  "source": "src/auth.py::function::validate_token",
  "target": "concept::auth-middleware",
  "type": "implements",
  "provenance": "inferred",
  "confidence": 0.81,
  "evidence": "validate_token implements the Auth Middleware checks described above"
}
```

#### `depends_on` (inferred)

```json
{
  "source": "src/auth.py",
  "target": "concept::pyjwt",
  "type": "depends_on",
  "provenance": "inferred",
  "confidence": 0.88,
  "evidence": "import jwt  # PyJWT"
}
```

**Rules**:
- `implements` and `depends_on` MUST use `provenance: "inferred"` and MUST include `confidence` + `evidence`
- Enrichment `mentions` to concepts MUST use `provenance: "extracted"` and MUST include `confidence` + `evidence`
- Legacy doc `mentions` without these fields remain valid when not produced by LLM enrichment
- `confidence` below the run threshold MUST NOT appear in the written graph (filtered at merge time)
- `evidence` MUST be grounded in the source chunk; ungrounded suggestions MUST be dropped

### Prior edge examples (unchanged semantics)

Inventory/code/docs/media edges keep schema 5 shapes; they MAY omit `confidence`/`evidence`.

## Allow-lists (schema 6.0.0)

**Node types**: `file`, `dir`, `function`, `class`, `method`, `heading`, `media_text`, `transcript_chunk`, `concept`

**Edge types**: `contains`, `references`, `defines`, `imports`, `calls`, `section_of`, `mentions`, `related_to`, `implements`, `depends_on`

## Compatibility

| Reader action | schema ≤ 5.0.0 | schema 6.0.0 |
|---------------|----------------|--------------|
| `visualize` / `status` / load | Reject with re-index message | Accept |
| Agents filtering provenance | N/A | Filter `implements`/`depends_on` as `inferred`; enrichment `mentions` as `extracted` with confidence/evidence |

## Minimal valid empty-ish graph

A valid schema 6 graph may contain only inventory/code nodes/edges (no concepts) when `--enrich-llm` was off or enrichment was skipped. `schema_version` MUST still be `"6.0.0"`.
