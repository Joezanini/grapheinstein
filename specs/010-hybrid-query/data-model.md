# Data Model: Hybrid Natural-Language Query

**Feature**: `010-hybrid-query`  
**Schema version**: `6.0.0` (unchanged; additive optional graph-level fields on query outputs)

## Entities

### Question (runtime)

| Field | Type | Rules |
|-------|------|-------|
| `text` | string | User-supplied question; required; non-empty after strip |
| `k` | int | ≥ 1 and ≤ 200; default `20`; max primary retrieval hits |
| `hops` | int | `1` or `2`; default `1` |
| `match_threshold` | float | ∈ [0.0, 1.0]; default `0.40` |
| `node_cap` | int | ≥ 1; default `500`; max nodes in supporting subgraph |
| `want_answer` | bool | default `true`; false when `--no-answer` |

### Chunk Candidate (runtime)

| Field | Type | Rules |
|-------|------|-------|
| `node_id` | string | Existing node `id` from the input graph |
| `chunk_text` | string | Non-empty searchable text (`metadata.text` or composed search text) |
| `node_type` | string | Copied from node |
| `source` | enum | `metadata_text` \| `composed` |

**Corpus rules**:

1. Prefer nodes with non-empty `metadata.text` (`source=metadata_text`).
2. Include other nodes with non-empty composed search text (`source=composed`).
3. One candidate per `node_id`. Empty corpus → load/retrieve failure.

### Chunk Hit (runtime)

| Field | Type | Rules |
|-------|------|-------|
| `node_id` | string | Candidate node id |
| `fuzzy_score` | float | ∈ [0.0, 1.0] |
| `embedding_score` | float \| null | Cosine similarity when vector path ran |
| `final_score` | float | `max(fuzzy_score, embedding_score or 0)` |
| `node_type` | string | For display / tie-break |
| `source` | enum | Inherited from candidate |

**Selection rules**:

1. Discard hits with `final_score < match_threshold`.
2. Sort by `final_score` desc, then prefer `source == metadata_text`, then `node_type == "concept"`, then shorter `node_id`.
3. Take first `k` as **primary hits** (seeds).
4. If zero primary hits → no-evidence failure (no output artifact).

### Hybrid Evidence (runtime)

| Field | Type | Rules |
|-------|------|-------|
| `primary_hit_ids` | string[] | Seeds, rank order, length ≤ `k` |
| `node_ids` | set of strings | Seeds ∪ undirected neighborhood within `hops`, subject to `node_cap` |
| `truncated` | bool | `true` when node cap truncated expansion |

### Supporting Subgraph (on disk)

A portable Graph Artifact (schema `6.0.0`) that is an induced hybrid neighborhood of the input:

| Aspect | Rules |
|--------|-------|
| Format | Same NetworkX node-link envelope as index/merge/explain |
| Nodes | Hybrid evidence node set |
| Links | All input links whose `source` and `target` are both in the node set; attrs preserved |
| Validation | Must pass the same `validate_artifact` rules as any schema `6.0.0` graph |

Query does **not** introduce new node or edge types.

### Graph-level metadata (additive on query outputs)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `project_root` | string | no | Copied from input when present |
| `generated_at` | string | yes | Fresh ISO-8601 UTC at query write time |
| `query_question` | string | yes (query outputs) | Original question text (stripped) |
| `query_hit_ids` | array of strings | yes (query outputs) | Primary hit node ids in rank order |
| `query_k` | int | yes (query outputs) | `--k` used for primary retrieval |
| `query_hops` | int | yes (query outputs) | `1` or `2` used for expansion |
| `query_truncated` | bool | no | `true` when `node_cap` truncated expansion |
| `query_hit_scores` | object | no | Optional map `node_id → final_score` |

### Citation (runtime)

| Field | Type | Rules |
|-------|------|-------|
| `kind` | enum | `node` \| `edge` |
| `node_id` | string | Required when `kind=node`; must exist in supporting subgraph |
| `source` / `target` / `edge_type` | string | Required when `kind=edge`; must match a link in supporting subgraph |

Invalid model-proposed citations are dropped; if none remain valid, a deterministic Sources list is built from primary hits (and optional sample edges).

### Cited Answer (runtime / stream + stdout JSON)

| Field | Type | Rules |
|-------|------|-------|
| `text` | string | Natural-language answer grounded in evidence |
| `citations` | Citation[] | Only subgraph-valid references |
| `status` | enum | `ok` \| `skipped` \| `failed` |
| `detail` | string | Human-readable reason when not `ok` |

### Visualization Summary (runtime / stream + stdout JSON)

| Field | Type | Rules |
|-------|------|-------|
| `node_count` | int | Nodes in supporting subgraph |
| `edge_count` | int | Links in supporting subgraph |
| `node_type_counts` | object | Map type → count (may be truncated to top types for display) |
| `sample_hit_ids` | string[] | Primary hits shown in the overview (≤ documented sample size) |
| `truncated` | bool | Mirrors `query_truncated` |
| `output_path` | string | Path written for the subgraph |

## Relationships

```text
Question
    → builds → Chunk Candidate[]
    → scores → Chunk Hit[]
    → selects → primary hits (≤ k)
    → expands → Hybrid Evidence (undirected ≤ hops, node_cap)
    → writes → Supporting Subgraph
    → emits → Visualization Summary
    → (optional) local LLM → Cited Answer (citations ⊆ subgraph)
```

## Validation / state transitions

| State | Condition | Next |
|-------|-----------|------|
| Rejected | Empty question or invalid k/hops/options | Error exit; no write |
| Load failed | Missing/invalid input graph | Error exit; no write |
| Empty corpus | No chunk-capable text | Error exit; no write |
| No evidence | No hit ≥ threshold | Error exit; no write |
| Retrieved | ≥1 primary hit | Expand neighborhood |
| Truncated | Neighborhood > node_cap | Set `query_truncated`; continue |
| Written | Validate + atomic write OK | Emit viz; attempt answer |
| Complete | Write OK; answer ok/skipped/failed | Exit 0; stdout query-answer JSON |

## Out of scope

- New parsers or modality ingestion
- Persisted embedding indexes in the graph file
- Soft-writing empty subgraphs on no-evidence
- Interactive/GUI visualization or automatic DOT/PNG
- Slash-command / MCP surfaces
