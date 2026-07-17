# Data Model: Local LLM Entity & Relation Extraction

**Feature**: `006-ollama-llm-extraction`  
**Schema version**: `6.0.0` (breaking vs `5.0.0`)

## Entities

### Project Root

Unchanged: absolute path supplied to `index`; node ids are POSIX-relative to this root (concepts use a global `concept::` namespace).

### Index Run Options

| Field | Type | Rules |
|-------|------|-------|
| `include_docs` | bool | Retained from schema 5 |
| `include_pdfs` | bool | Retained from schema 5 |
| `transcribe_media` | bool | Retained from schema 5 |
| `enrich_llm` | bool | Default `false`; when true, run local LLM concept/relation enrichment |
| `llm_model` | string | Model tag used or attempted; default `qwen3.5-2b-mlx:fp16-8gbGPU` |
| `llm_base_url` | string | Ollama base URL; default `http://localhost:11434` |
| `llm_confidence_threshold` | float | Default `0.5`; inclusive keep rule (`confidence >= threshold`) |

Persisted on artifact when relevant: `graph.enrich_llm`, `graph.llm_model` (and retained prior flags).

### Graph Node (file / dir / code / heading / media)

Unchanged from schema 5.x. Enrichment **must not** invent new `function`/`class`/`method` nodes; it may only link to existing ones.

### Graph Node (concept) — new

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `id` | string | yes | `concept::{slug}` — deterministic slug of normalized name |
| `type` | string | yes | Exactly `concept` |
| `metadata` | object | yes | Must include `name` (non-empty display string). Optional: `kind` (`domain_term` \| `library` \| `other`), `aliases` (string list) |

**Rules**:
- Same slug → reuse existing concept node (first `name` wins for casing)
- Empty/whitespace names are invalid and MUST NOT create nodes
- Emitted only when `--enrich-llm` ran and at least one accepted entity produced the concept

### Enrichment unit (runtime, not persisted as a node type)

| Field | Type | Rules |
|-------|------|-------|
| `file_id` | string | Existing `file` node id |
| `text` | string | Chunk text sent to the model (may be truncated) |
| `truncated` | bool | True when source text exceeded max char budget |

## Edges

### Prior edge types

`contains`, `references`, `defines`, `imports`, `calls`, `section_of`, `related_to`, and non-enrichment `mentions` retain schema 5 semantics. They **MAY omit** `confidence` and `evidence`.

### Mentions (extended for enrichment)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `source` | string | yes | `file`, code entity, `heading`, `media_text`, or `transcript_chunk` id |
| `target` | string | yes | `concept` id (for enrichment-produced mentions) |
| `type` | string | yes | Exactly `mentions` |
| `provenance` | string | yes | `extracted` when the term is grounded in chunk text via enrichment |
| `confidence` | number | yes* | Required when this edge is produced by LLM enrichment |
| `evidence` | string | yes* | Required when produced by LLM enrichment; non-empty; grounded in chunk |

\* Doc-parser `mentions` edges from schema 4/5 without enrichment attrs remain valid without `confidence`/`evidence`.

### Implements (new)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `source` | string | yes | Code entity id (`function` \| `class` \| `method`) |
| `target` | string | yes | `concept` id |
| `type` | string | yes | Exactly `implements` |
| `provenance` | string | yes | Exactly `inferred` |
| `confidence` | number | yes | Float in `[0.0, 1.0]`; must be `>=` threshold to keep |
| `evidence` | string | yes | Non-empty; grounded in chunk |

### Depends-on (new)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `source` | string | yes | `file` or code entity id |
| `target` | string | yes | `concept` id (typically `kind: library`) |
| `type` | string | yes | Exactly `depends_on` |
| `provenance` | string | yes | Exactly `inferred` |
| `confidence` | number | yes | Float in `[0.0, 1.0]`; must be `>=` threshold to keep |
| `evidence` | string | yes | Non-empty; grounded in chunk |

### Enrichment Failure / Skip (runtime)

Not a graph node. Logged/counted similarly to `parse_skips`: per-chunk model failures, ungrounded evidence drops, unresolved endpoints, and whole-run skip when Ollama/model unavailable.

## Validation Rules

1. `provenance` MUST be exactly `extracted` or `inferred`.
2. Enrichment-required edges (`implements`, `depends_on`, enrichment `mentions` with confidence/evidence) MUST include `confidence` ∈ `[0.0, 1.0]` and non-empty `evidence`.
3. Drop relations with `confidence < llm_confidence_threshold` (default 0.5 inclusive keep: `>=`).
4. Drop suggestions whose `evidence` is not grounded in the chunk text.
5. Do not create edges to missing endpoints; resolve or drop.
6. No self-loops; `multigraph` remains `false` — one edge per `(source, target)` pair; skip if pair already occupied.
7. Loaders reject `schema_version` ≠ `6.0.0`.

## State / Pipeline

```text
discover → inventory → references → code → [docs] → [pdfs] → [media] → [llm enrich] → save graph.json (6.0.0)
```

When `enrich_llm` is false: skip LLM stage entirely (zero HTTP calls).  
When Ollama/model unavailable with flag on: skip LLM stage after warning; still save structural graph.
