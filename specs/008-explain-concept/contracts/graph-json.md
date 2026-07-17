# Graph JSON Contract: Explanation Subgraphs

**Feature**: `008-explain-concept`  
**Schema version**: `6.0.0` (unchanged)

## Envelope

Explanation subgraphs use the same NetworkX node-link portable envelope as index/merge:

| Field | Type | Rules |
|-------|------|-------|
| `schema_version` | string | Must be `"6.0.0"` |
| `directed` | bool | `true` |
| `multigraph` | bool | `false` |
| `graph` | object | Graph-level metadata (see below) |
| `nodes` | array | Node objects with `id`, `type`, `metadata` |
| `links` | array | Edge objects with `source`, `target`, `type`, `provenance` (+ optional enrichment attrs) |

Loaders and writers are the shared gzip-aware `load_artifact` / `write_artifact_dict` path. Invalid explanation outputs MUST fail validation the same way as any other artifact.

## Node and edge rules

- **No new** node types or edge types for this feature.
- Every node/edge copied from the input MUST retain original `type`, `provenance`, and optional attrs (`confidence`, `evidence`, …).
- Explain MUST NOT add unlabeled structural edges. Narrative summary is not graph mutation.
- Allow-lists and per-type metadata requirements remain those of schema `6.0.0`.

## Graph-level metadata for explain outputs

In addition to fields allowed by prior contracts, explain writes:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `generated_at` | string | yes | ISO-8601 UTC at explain time |
| `explained_concept` | string | yes | Stripped concept query |
| `explain_match_ids` | string[] | yes | Primary match ids, best-first |
| `explain_hops` | int | yes | `1` or `2` |
| `explain_truncated` | bool | no | Present/`true` when node cap truncated the neighborhood |
| `explain_match_scores` | object | no | Optional `id → score` map |
| `project_root` | string | no | Copied from input when present |

`merged` / `merged_from` are **not** required on explain outputs (explain is not merge).

## Completeness

- Subgraph MUST include all primary match nodes.
- Subgraph MUST include every node within undirected distance ≤ `explain_hops` of any primary match, except when truncated by the documented node cap (then `explain_truncated` is true and a human warning was emitted).
- Subgraph MUST include every input link with both endpoints in the subgraph node set.

## Compatibility

- Consumers that ignore unknown `graph` keys continue to work.
- Older tools that only understand schema `6.0.0` node/link shapes can load explanation subgraphs without repair (SC-007).
