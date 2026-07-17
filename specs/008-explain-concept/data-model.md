# Data Model: Explain Concept Subgraph

**Feature**: `008-explain-concept`  
**Schema version**: `6.0.0` (unchanged; additive optional graph-level fields on explain outputs)

## Entities

### Concept Query (runtime)

| Field | Type | Rules |
|-------|------|-------|
| `text` | string | User-supplied concept phrase; required; non-empty after strip |
| `hops` | int | `1` or `2`; default `2` |
| `top_n` | int | ≥ 1; default `3`; max primary matches included |
| `match_threshold` | float | ∈ [0.0, 1.0]; default `0.55` |
| `node_cap` | int | ≥ 1; default `500`; max nodes in output subgraph |
| `want_summary` | bool | default `true`; false when `--no-summary` |

### Match Candidate (runtime)

| Field | Type | Rules |
|-------|------|-------|
| `node_id` | string | Existing node `id` from the input graph |
| `fuzzy_score` | float | ∈ [0.0, 1.0] from text/fuzzy scoring |
| `embedding_score` | float \| null | Cosine similarity when vector path ran; else null |
| `final_score` | float | `max(fuzzy_score, embedding_score or 0)` (embedding ignored when null) |
| `node_type` | string | Copied from node for tie-break / display |

**Selection rules**:

1. Discard candidates with `final_score < match_threshold`.
2. Sort by `final_score` desc, then prefer `node_type == "concept"`, then shorter `node_id`.
3. Take first `top_n` as **primary matches**.
4. If zero primary matches → no-match failure (no output artifact).

### Explanation Subgraph (on disk)

A portable Graph Artifact (schema `6.0.0`) that is an induced neighborhood of the input:

| Aspect | Rules |
|--------|-------|
| Format | Same NetworkX node-link envelope as index/merge (`schema_version`, `directed`, `multigraph`, `graph`, `nodes`, `links`) |
| Nodes | Primary matches ∪ nodes within undirected hop radius `hops`, subject to `node_cap` |
| Links | All input links whose `source` and `target` are both in the node set; attrs preserved (`type`, `provenance`, optional `confidence`/`evidence`/…) |
| Validation | Must pass the same `validate_artifact` rules as any schema `6.0.0` graph |
| Encoding | UTF-8 JSON or gzip per existing write helpers when compression is used (explain CLI does not require `--compress` in v1; writers may still accept path `.gz` if shared helper appends—default plain JSON) |

Explain does **not** introduce new node or edge types. Copied nodes/edges retain original allow-listed types and provenance.

### Graph-level metadata (additive on explain outputs)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `project_root` | string | no | Copied from input when present |
| `generated_at` | string | yes | Fresh ISO-8601 UTC at explain write time |
| `explained_concept` | string | yes (explain outputs) | Original concept query text (stripped) |
| `explain_match_ids` | array of strings | yes (explain outputs) | Primary match node ids in rank order |
| `explain_hops` | int | yes (explain outputs) | `1` or `2` used for extraction |
| `explain_truncated` | bool | no | `true` when `node_cap` truncated the neighborhood |
| `explain_match_scores` | object | no | Optional map `node_id → final_score` for debugging/agents |

Prior index/merge-only fields (`merged`, `enrich_llm`, …) are omitted unless intentionally copied when identical and still meaningful; v1 may omit merge/enrich flags on explain outputs.

### Explanation Summary (runtime / stream)

| Field | Type | Rules |
|-------|------|-------|
| `text` | string | Natural-language summary grounded in the subgraph |
| `status` | enum | `ok` \| `skipped` \| `failed` |
| `detail` | string | Human-readable reason when not `ok` (model missing, timeout, …) |

Not persisted as the primary `--output` artifact. Emitted on the human-readable stream.

## Relationships

```text
Concept Query
    → scores → Match Candidate[]
    → selects → primary matches (≤ top_n)
    → extracts → Explanation Subgraph (seeds + undirected ≤ hops)
    → (optional) prompts local LLM → Explanation Summary
```

## Validation / state transitions

| State | Condition | Next |
|-------|-----------|------|
| Rejected | Empty concept or invalid hops/options | Error exit; no write |
| Load failed | Missing/invalid input graph | Error exit; no write |
| No match | No candidate ≥ threshold | Error exit; no write |
| Matched | ≥1 primary match | Build neighborhood |
| Truncated | Neighborhood > node_cap | Set `explain_truncated`; continue |
| Written | Validate + atomic write OK | Emit summary attempt |
| Complete | Write OK; summary ok/skipped/failed | Exit 0 |

## Out of scope

- New parsers or modality ingestion
- Persisted embedding indexes in the graph file
- Soft-writing empty subgraphs on no-match
- Slash-command / MCP surfaces
