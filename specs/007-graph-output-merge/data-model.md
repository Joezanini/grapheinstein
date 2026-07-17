# Data Model: Valid Graph Output, Compression, Versioning & Merge

**Feature**: `007-graph-output-merge`  
**Schema version**: `6.0.0` (unchanged; additive optional graph-level fields)

## Entities

### Graph Artifact (on disk)

| Field / aspect | Rules |
|----------------|-------|
| Format | NetworkX node-link JSON envelope (`schema_version`, `directed`, `multigraph`, `graph`, `nodes`, `links`) |
| Encoding | UTF-8 JSON, or gzip of that UTF-8 JSON when compressed |
| Plain path | Typically `*.json` |
| Compressed path | Typically `*.json.gz` |
| Completeness | Every node has `id`, `type`, `metadata` (object, may be `{}`); every link has `source`, `target`, `type`, `provenance`; conditional attrs retained when present |
| Write integrity | Artifact is only published to the final path after in-memory validation; write is atomic (temp + replace) |

Node and edge allow-lists, provenance rules, and per-type metadata requirements are unchanged from schema `6.0.0` (see prior feature contracts). This feature does **not** introduce new node or edge types.

### Graph-level metadata (additive)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `project_root` | string | yes* | Absolute path for single-project index runs. *On merge: required when all inputs share one root; **omitted** when roots diverge (use `project_roots` instead). |
| `generated_at` | string | yes | ISO-8601 UTC; refreshed on every successful index or merge write |
| `languages` | array | no | Retained when identical across merge inputs; else dropped |
| `include_docs` / `include_pdfs` / `transcribe_media` / `enrich_llm` | bool | no | Retained only when identical across merge inputs |
| `llm_model` | string | no | Retained only when identical across merge inputs |
| `parse_skips` | int | no | Index-only; on merge omit unless identical |
| `merged` | bool | no | `true` on artifacts produced by `merge` |
| `merged_from` | array of strings | conditional | Required when `merged` is true; ordered list of resolved input paths |
| `project_roots` | array of strings | conditional | Present when merge inputs disagree on `project_root`; unique roots in stable order |

### Versioned Snapshot

| Field | Type | Rules |
|-------|------|-------|
| Filename | string | `graph_v{N}.json` or `graph_v{N}.json.gz` |
| `N` | positive integer | Next unused number in the primary output’s parent directory |
| Content | Graph Artifact | Byte-identical payload to the primary write for that run (same validation rules) |
| Lifetime | — | Never overwritten by later versioned writes |

### Primary (“latest”) output

| Field | Type | Rules |
|-------|------|-------|
| Path | user `--output` (with `.gz` suffix rule when compressing) | Overwritten on each successful index when that path is the destination |
| Relationship to snapshots | — | When `--versioned`, both latest and a new `graph_vN` are written for the same successful run |

### Merge Operation (runtime)

| Field | Type | Rules |
|-------|------|-------|
| Inputs | ≥ 2 Graph Artifacts | Each validated; same `schema_version` as tool |
| Output | 1 Graph Artifact | Union of nodes/links; merge graph metadata as above |
| Node conflict | — | Same `id` with unequal `type` or unequal `metadata` → fail |
| Edge conflict | — | Same identity key with unequal optional attrs → fail |
| Dedup | — | Equivalent nodes/edges collapse to one |

## Validation rules (write path)

1. In-memory artifact MUST pass the same `validate_artifact` rules as load (schema `6.0.0`, node/edge allow-lists, enrichment attrs where required).
2. Successful index/merge MUST NOT leave a truncated or invalid file at the final output path.
3. Failed merge/index MUST NOT replace a previous good artifact with a bad one (atomic replace only after full serialize).

## State transitions

```text
[index build] → validate dict → atomic write(primary)
                              ↘ if --versioned: atomic write(graph_vN)

[merge load inputs] → validate each → union / conflict check
                                    → validate result dict → atomic write(output)
```

## Out of scope for this model

- New entity types from parsers
- Soft/last-write-wins conflict resolution
- Content-addressed or hash-based snapshot names
- Changing `schema_version` away from `6.0.0`
