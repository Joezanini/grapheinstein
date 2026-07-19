# Data Model: Large Repo Guards

**Feature**: `014-large-repo-guards`  
**Date**: 2026-07-19  
**Graph schema**: unchanged `6.0.0`

This feature adds **policy and eligibility entities** used during indexing. It does not introduce new graph node/edge types.

## Entities

### Inventory Scope

| Field | Type | Description |
|-------|------|-------------|
| `project_root` | path | Root being indexed |
| `gitignore_rules` | patterns | From project `.gitignore` |
| `config_ignored_patterns` | list[str] | User/config `ignored_patterns` |
| `code_only_default_ignores` | list[str] | Built-in patterns when `code_only` and not `include_generated_docs` |
| `effective_ignores` | patterns | Union applied by discovery |

**Rules**:
- Paths matching effective ignores are absent from file/dir inventory nodes and edges.
- `include_generated_docs=true` omits `code_only_default_ignores` from the union.

### Scan Eligibility

Per inventoried file node, whether contents may be read for reference linking.

| Field | Type | Description |
|-------|------|-------------|
| `node_id` | string | Relative posix path |
| `eligible` | bool | May be scanned |
| `skip_reason` | enum \| null | `oversize` \| `symlink` \| `non_code` \| `non_utf8` \| `unreadable` \| null |

**Rules**:
- `oversize`: `metadata.skipped == "oversize"` → never eligible.
- `symlink`: never eligible (unchanged).
- `non_code`: when `code_only`, suffix not in code `EXTENSION_MAP` → not eligible.
- Eligible files still subject to `max_reference_scan_bytes` prefix cap.

### Scan Cost Estimate

Computed after discovery / inventory construction, before heavy reference work.

| Field | Type | Description |
|-------|------|-------------|
| `eligible_scan_files` | int | Count of files that would be scanned |
| `unique_basenames` | int | Unambiguous basename target count |
| `estimated_scan_ops` | int | `eligible_scan_files * unique_basenames` |
| `non_code_share` | float | Non-code file bytes / total file bytes in inventory ∈ [0, 1] |
| `total_bytes` | int | Sum of inventoried regular file sizes |
| `file_count` | int | Inventoried regular file count |
| `tripped_gates` | list[str] | Names of thresholds exceeded |

### Large-Repo Policy Decision

| Field | Type | Description |
|-------|------|-------------|
| `policy` | enum | `reject` (default) \| `allow` (override) |
| `outcome` | enum | `proceed` \| `reject` |
| `message` | string | Human-readable reason + remediation |

**State transitions**:

```text
[discovery complete]
        │
        ▼
[compute Scan Cost Estimate]
        │
        ├─ any hard/advisory gate exceeded AND policy=reject → outcome=reject (fail fast)
        └─ else → outcome=proceed → references (bounded) → structure → …
```

### Index Phase Marker

| Field | Type | Description |
|-------|------|-------------|
| `phase` | enum | `discovery` \| `inventory` \| `preflight` \| `references` \| `code_structure` \| `optional_enrichment` \| `persist` |
| `status` | enum | `started` \| `completed` |

Used for timeout error messages (last completed / in-progress).

### References Edge (unchanged)

| Field | Type | Description |
|-------|------|-------------|
| `type` | `references` | Relationship |
| `provenance` | `extracted` | Unchanged for basename mentions |
| endpoints | file → file | Only created from **eligible** scanned sources; targets remain unique basename map |

## Config entities (additive keys)

See [contracts/cli.md](./contracts/cli.md) for types/defaults. Logical grouping:

| Key | Role |
|-----|------|
| `code_only` | Enable code-only ignores + code-only scan eligibility |
| `include_generated_docs` | Disable code-only default ignores |
| `max_reference_scan_bytes` | Per-file text cap for reference linking |
| `max_reference_scan_ops` | Preflight ops threshold |
| `max_non_code_share` | Preflight share threshold (enforced when `code_only`) |
| `max_total_bytes` | Inventory byte cap |
| `max_file_count` | Inventory file-count cap |
| `timeout_seconds` | Optional cooperative timeout (`0` = off) |
| `large_repo_policy` | `reject` \| `allow` |

## Validation summary

- Threshold integers MUST be ≥ 1 when set (except `timeout_seconds` ≥ 0).
- `non_code_share` threshold MUST be in (0, 1].
- `large_repo_policy: allow` does not bypass per-file `max_file_size` or `max_reference_scan_bytes`.
- Rejected/timed-out runs MUST NOT persist a successful complete graph artifact.
