# Contract: graph.json (schema_version 6.0.0 — I/O extensions)

**Feature**: `007-graph-output-merge`  
**Format**: JSON document compatible with NetworkX node-link data, plus required envelope fields  
**Schema**: Remains **`6.0.0`** (no breaking node/edge changes). This document specifies **write completeness**, **gzip packaging**, and **additive merge metadata**.

Base shape (nodes, links, allow-lists, provenance, enrichment attrs) is defined by `006-ollama-llm-extraction` / schema `6.0.0`. Readers MUST continue to reject other `schema_version` values.

## Top-level object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Must be `"6.0.0"` |
| `directed` | boolean | yes | Must be `true` |
| `multigraph` | boolean | yes | Must be `false` |
| `graph` | object | yes | Graph-level metadata |
| `nodes` | array | yes | Node list |
| `links` | array | yes | Edge list |

## Completeness invariants (writers)

1. Every node object MUST include `id`, `type`, and `metadata` (object; may be `{}`). Writers MUST NOT drop collected metadata keys.
2. Every link object MUST include `source`, `target`, `type`, and `provenance` (`extracted` \| `inferred`). Writers MUST preserve conditional attrs (`confidence`, `evidence`, `reason`) when present on the in-memory edge.
3. Every `links[].source` and `links[].target` MUST exist in `nodes[].id`.
4. Successful writers MUST validate these invariants **before** publishing the final file path (atomic replace after serialize).

## On-disk encodings

| Encoding | Path convention | Notes |
|----------|-----------------|-------|
| Plain JSON | `*.json` | UTF-8 text; pretty-printed with trailing newline (existing style OK) |
| Gzip JSON | `*.json.gz` | gzip of the same UTF-8 JSON document |

Decompressed content MUST satisfy the same JSON contract as plain files.

## `graph` metadata

### Required on index writes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_root` | string | yes | Absolute path that was indexed |
| `generated_at` | string | yes | ISO-8601 UTC timestamp for this write |

Optional index fields from schema 6 (`languages`, `include_docs`, `include_pdfs`, `transcribe_media`, `enrich_llm`, `llm_model`, `parse_skips`) remain as previously documented.

### Additive fields for merge writes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `merged` | boolean | yes (merge) | Must be `true` for `grapheinstein merge` outputs |
| `merged_from` | array of strings | yes (merge) | Resolved input paths in CLI order |
| `generated_at` | string | yes | Fresh merge-time UTC timestamp |
| `project_root` | string | conditional | Present when all inputs share the same root |
| `project_roots` | array of strings | conditional | Present when input roots diverge; unique roots |

When `project_roots` is present, writers SHOULD omit `project_root` (do not invent a single false root).

## Versioned snapshot files

Not a schema change. Filesystem naming only:

- `graph_v1.json`, `graph_v2.json`, …
- Compressed: `graph_v1.json.gz`, …

Each snapshot MUST be a full valid artifact identical in content to the primary write for that run.

## Merge result example (excerpt)

```json
{
  "schema_version": "6.0.0",
  "directed": true,
  "multigraph": false,
  "graph": {
    "generated_at": "2026-07-17T16:00:00Z",
    "merged": true,
    "merged_from": [
      "/tmp/a.json",
      "/tmp/b.json.gz"
    ],
    "project_roots": [
      "/projects/alpha",
      "/projects/beta"
    ]
  },
  "nodes": [],
  "links": []
}
```

## Non-goals

- New node or edge types
- Soft conflict resolution encoded in the file
- Changing `schema_version` to a new major for this feature alone
