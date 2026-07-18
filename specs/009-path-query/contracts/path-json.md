# Path Answer JSON Contract

**Feature**: `009-path-query`  
**Path answer version**: `1.0.0`  
**Input graph schema**: `6.0.0` (unchanged)

## Purpose

Machine-consumable result of `grapheinstein path`. This is **not** a NetworkX node-link `graph.json` envelope. Agents parse this object from stdout (or `--output`).

## Top-level object

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `kind` | string | yes | Must be `"path_answer"` |
| `version` | string | yes | Must be `"1.0.0"` |
| `input_schema_version` | string | yes | Schema of the loaded graph; `"6.0.0"` |
| `start` | object | yes | Endpoint resolution (see below) |
| `end` | object | yes | Endpoint resolution (see below) |
| `nodes` | string[] | yes | Ordered node ids from start to end; length ≥ 1 |
| `steps` | array | yes | Ordered path steps; length `len(nodes) - 1` |
| `hop_count` | int | yes | `len(steps)` |
| `total_cost` | number | yes | Sum of step costs; `0` when `hop_count == 0` |
| `explanation` | string | yes | Path-grounded human-readable explanation |
| `explanation_mode` | string | yes | `"deterministic"` or `"llm"` |
| `generated_at` | string | yes | ISO-8601 UTC |

### Endpoint object (`start` / `end`)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `query` | string | yes | Stripped user phrase |
| `node_id` | string | yes | Resolved node id |
| `score` | number | yes | Final match score ∈ [0.0, 1.0] |
| `node_type` | string | no | Resolved node type when known |

### Step object (`steps[]`)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `source` | string | yes | Must equal previous target / prior node in `nodes` |
| `target` | string | yes | Next node id |
| `type` | string | yes | Relationship type from input edge |
| `provenance` | string | yes | `"extracted"` or `"inferred"` |
| `confidence` | number \| null | no | Present when input edge had confidence; ∈ [0.0, 1.0] |
| `cost` | number | yes | Positive weight contribution of this step |

## Consistency rules

1. `nodes[0] == start.node_id` and `nodes[-1] == end.node_id`.
2. For each `i`, `steps[i].source == nodes[i]` and `steps[i].target == nodes[i+1]`.
3. Trivial path (same endpoint): `nodes` length 1, `steps` empty, `hop_count` 0, `total_cost` 0.
4. Explanation MUST NOT claim relationships absent from `steps`.
5. Provenance/type MUST be copied from the chosen input edges (no silent relabel).

## Encoding

- UTF-8 JSON object.
- Pretty-print optional; parsers must accept compact JSON.
- Default file write is uncompressed `.json`.

## Example (illustrative)

```json
{
  "kind": "path_answer",
  "version": "1.0.0",
  "input_schema_version": "6.0.0",
  "start": {"query": "auth", "node_id": "concept:auth", "score": 0.92, "node_type": "concept"},
  "end": {"query": "login", "node_id": "func:login", "score": 0.88, "node_type": "function"},
  "nodes": ["concept:auth", "file:auth.py", "func:login"],
  "steps": [
    {
      "source": "concept:auth",
      "target": "file:auth.py",
      "type": "mentions",
      "provenance": "extracted",
      "confidence": 0.9,
      "cost": 1.39
    },
    {
      "source": "file:auth.py",
      "target": "func:login",
      "type": "defines",
      "provenance": "extracted",
      "confidence": null,
      "cost": 2.5
    }
  ],
  "hop_count": 2,
  "total_cost": 3.89,
  "explanation": "auth connects to login via mentions (extracted) then defines (extracted).",
  "explanation_mode": "deterministic",
  "generated_at": "2026-07-17T18:00:00Z"
}
```

## Compatibility

- Independent of `graph.json` loaders; do not pass path answers to `load_artifact` / `validate_artifact`.
- Future versions bump `version` and document migrations; unknown extra fields SHOULD be ignored by consumers.
