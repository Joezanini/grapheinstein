# Data Model: Path Between Concepts

**Feature**: `009-path-query`  
**Input graph schema**: `6.0.0` (unchanged)  
**Path answer contract**: see [contracts/path-json.md](./contracts/path-json.md)

## Entities

### Path Query (runtime)

| Field | Type | Rules |
|-------|------|-------|
| `start_text` | string | User-supplied start phrase; required; non-empty after strip |
| `end_text` | string | User-supplied end phrase; required; non-empty after strip |
| `match_threshold` | float | ∈ [0.0, 1.0]; default `0.55` |
| `max_hops` | int | ≥ 0; default `32`; max edges in accepted path (`0` = only trivial same-node) |
| `want_llm_explain` | bool | default `true`; false when `--no-llm-explain` |

### Endpoint Match (runtime)

| Field | Type | Rules |
|-------|------|-------|
| `role` | enum | `start` \| `end` |
| `query_text` | string | Stripped phrase for this endpoint |
| `node_id` | string | Selected node id from input graph |
| `fuzzy_score` | float | ∈ [0.0, 1.0] |
| `embedding_score` | float \| null | When vector path ran; else null |
| `final_score` | float | `max(fuzzy_score, embedding_score or 0)` |
| `node_type` | string | From matched node |

**Selection rules**:

1. Score all nodes with shared match helpers.
2. Discard candidates with `final_score < match_threshold`.
3. Sort by match tie-break (score desc, prefer `concept`, shorter id).
4. Take the single best candidate per role.
5. If either role has no candidate → resolution failure (identify role(s)).

### Edge Cost (runtime)

| Field | Type | Rules |
|-------|------|-------|
| `source` | string | Edge source id |
| `target` | string | Edge target id |
| `type` | string | Relationship type from input |
| `provenance` | enum | `extracted` \| `inferred` |
| `confidence` | float \| null | From edge when present ∈ [0.0, 1.0] |
| `cost` | float | Positive weight used by shortest_path; see research R4 |

**Cost formula** (defaults):

```text
conf = confidence if present else 0.5
conf = max(conf, ε) with ε = 0.35
cost = type_base[type] * provenance_factor[provenance] / conf
```

### Path Step (runtime / answer)

| Field | Type | Rules |
|-------|------|-------|
| `source` | string | Node id |
| `target` | string | Node id |
| `type` | string | Copied from chosen edge |
| `provenance` | enum | Copied; must be `extracted` or `inferred` |
| `confidence` | float \| null | Copied when present |
| `cost` | float | Cost contribution of this step |

### Weighted Path (runtime / answer)

| Field | Type | Rules |
|-------|------|-------|
| `nodes` | string[] | Ordered node ids from start to end (length ≥ 1) |
| `steps` | Path Step[] | Length `len(nodes) - 1`; empty when start == end |
| `total_cost` | float | Sum of step costs (`0` for trivial path) |
| `hop_count` | int | `len(steps)`; must be ≤ `max_hops` |

### Path Explanation (runtime / answer)

| Field | Type | Rules |
|-------|------|-------|
| `text` | string | Human-readable description grounded in steps |
| `mode` | enum | `deterministic` \| `llm` |
| `status` | enum | `ok` \| `skipped` \| `failed` |
| `detail` | string | Reason when not using LLM polish / on failure |

Deterministic text is always producible when a path exists. LLM polish is optional and must not invent edges.

### Path Answer (on disk / stdout)

Machine-consumable JSON document (not a graph.json envelope). Required fields documented in [path-json.md](./contracts/path-json.md).

## Relationships

```text
Path Query
    → resolves → Endpoint Match (start) + Endpoint Match (end)
    → weights edges → Edge Cost per directed link
    → shortest_path → Weighted Path (nodes + Path Steps)
    → narrates → Path Explanation
    → serializes → Path Answer (stdout / optional --output)
```

## Validation / state transitions

| State | Condition | Next |
|-------|-----------|------|
| Rejected | Empty start/end or invalid options | Error exit; no answer |
| Load failed | Missing/invalid input graph | Error exit; no answer |
| Unresolved | Start and/or end below threshold | Error exit; no answer |
| Disconnected | `NetworkXNoPath` | Error exit; no answer |
| Too long | `hop_count > max_hops` | Error exit; no answer |
| Found | Path within hop limit | Build answer + explanation |
| Complete | Answer emitted (stdout; file if `--output`) | Exit 0 |

## Out of scope

- New parsers or modality ingestion
- Persisting preferred paths back into the project graph
- Returning multiple alternate paths (k-shortest)
- Undirected path finding
- Schema bump of input `graph.json`
