# Query Answer JSON Contract

**Feature**: `010-hybrid-query`  
**Answer contract version**: `1.0.0`  
**Emitted on**: stdout (success only)

## Envelope

```json
{
  "schema_version": "1.0.0",
  "question": "How does authentication work?",
  "output": "/path/to/subgraph.json",
  "k": 20,
  "hops": 1,
  "hit_ids": ["node-a", "node-b"],
  "truncated": false,
  "embed_note": null,
  "visualization": {
    "node_count": 12,
    "edge_count": 15,
    "node_type_counts": {"function": 4, "concept": 2},
    "sample_hit_ids": ["node-a", "node-b"],
    "truncated": false,
    "output_path": "/path/to/subgraph.json"
  },
  "answer": {
    "status": "ok",
    "text": "Authentication is handled by … [node:node-a].",
    "detail": null,
    "citations": [
      {"kind": "node", "node_id": "node-a"},
      {
        "kind": "edge",
        "source": "node-a",
        "target": "node-b",
        "edge_type": "calls"
      }
    ]
  }
}
```

## Fields

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `schema_version` | string | yes | `"1.0.0"` for this contract |
| `question` | string | yes | Stripped question |
| `output` | string | yes | Path written for supporting subgraph |
| `k` | int | yes | Primary hit budget used |
| `hops` | int | yes | Expansion hops used |
| `hit_ids` | string[] | yes | Primary hits, best-first |
| `truncated` | bool | yes | Whether neighborhood was capped |
| `embed_note` | string \| null | yes | Soft-skip note when embeddings unavailable; else null |
| `visualization` | object | yes | See below |
| `answer` | object | yes | See below |

### `visualization`

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `node_count` | int | yes | ≥ 0 |
| `edge_count` | int | yes | ≥ 0 |
| `node_type_counts` | object | yes | Map of type → count (may omit zero types) |
| `sample_hit_ids` | string[] | yes | Subset/prefix of `hit_ids` for display |
| `truncated` | bool | yes | Same as top-level `truncated` |
| `output_path` | string | yes | Same as top-level `output` |

### `answer`

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `status` | string | yes | `ok` \| `skipped` \| `failed` |
| `text` | string \| null | yes | Answer body when `ok`; may be null when skipped/failed |
| `detail` | string \| null | yes | Reason when not `ok` |
| `citations` | array | yes | Possibly empty only when `status != ok`; when `ok`, MUST be non-empty after validation/fallback |

### Citation object

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `kind` | string | yes | `node` or `edge` |
| `node_id` | string | if `kind=node` | Must exist in the written subgraph |
| `source` | string | if `kind=edge` | Edge source id in subgraph |
| `target` | string | if `kind=edge` | Edge target id in subgraph |
| `edge_type` | string | if `kind=edge` | Edge `type` matching a link in subgraph |

## Emission rules

- Print **only** this JSON document on stdout on success (pretty or compact; stable key order preferred for tests).
- Do not print progress or Rich tables on stdout.
- On failure (non-zero exit), stdout SHOULD be empty of a success-looking answer envelope.

## Compatibility

- Separate from graph schema `6.0.0`; agents parse stdout independently of the subgraph file.
- Human-readable duplicates of answer/viz on stderr are allowed and expected for interactive use.
