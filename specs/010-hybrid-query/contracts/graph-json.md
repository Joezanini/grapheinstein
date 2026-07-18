# Graph JSON Contract: Query Supporting Subgraphs

**Feature**: `010-hybrid-query`  
**Schema version**: `6.0.0` (unchanged)

## Envelope

Supporting subgraphs use the same NetworkX node-link portable envelope as index/merge/explain:

| Field | Type | Rules |
|-------|------|-------|
| `schema_version` | string | Must be `"6.0.0"` |
| `directed` | bool | `true` |
| `multigraph` | bool | `false` |
| `graph` | object | Graph-level metadata (see below) |
| `nodes` | array | Node objects with `id`, `type`, `metadata` |
| `links` | array | Edge objects with `source`, `target`, `type`, `provenance` (+ optional enrichment attrs) |

Loaders and writers are the shared gzip-aware `load_artifact` / `write_artifact_dict` path. Invalid query outputs MUST fail validation the same way as any other artifact.

## Node and edge rules

- **No new** node types or edge types for this feature.
- Every node/edge copied from the input MUST retain original `type`, `provenance`, and optional attrs (`confidence`, `evidence`, …).
- Query MUST NOT add unlabeled structural edges. Narrative answers/citations are not graph mutation.
- Allow-lists and per-type metadata requirements remain those of schema `6.0.0`.

## Graph-level metadata for query outputs

In addition to fields allowed by prior contracts, query writes:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `generated_at` | string | yes | ISO-8601 UTC at query time |
| `query_question` | string | yes | Stripped question text |
| `query_hit_ids` | string[] | yes | Primary hit ids, best-first (length ≤ `query_k`) |
| `query_k` | int | yes | Primary retrieval budget used |
| `query_hops` | int | yes | `1` or `2` |
| `query_truncated` | bool | no | Present/`true` when node cap truncated expansion |
| `query_hit_scores` | object | no | Optional `id → score` map |
| `project_root` | string | no | Copied from input when present |

`merged` / `merged_from` / explain-only keys are **not** required on query outputs.

## Completeness

- Subgraph MUST include all primary hit nodes (`query_hit_ids`).
- Subgraph MUST include every node within undirected distance ≤ `query_hops` of any primary hit, except when truncated by the documented node cap (then `query_truncated` is true and a human warning was emitted).
- Subgraph MUST include every input link with both endpoints in the subgraph node set.

## Compatibility

- Consumers that ignore unknown `graph` keys continue to work.
- Older tools that only understand schema `6.0.0` node/link shapes can load supporting subgraphs without repair (SC-007).
- The written file MAY be passed to `grapheinstein visualize` for a separate structural view.
