# Python API Contract: Large Repo Guards

**Feature**: `014-large-repo-guards`  
**API surface**: `grapheinstein.api.index` (and serve `POST /index` body fields mirroring these kwargs)  
**Graph schema**: `6.0.0` (unchanged)

## `index(...)` additive parameters

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `code_only` | `bool` | `False` | Same semantics as CLI `--code-only` |
| `include_generated_docs` | `bool` | `False` | Same as `--include-generated-docs` |
| `allow_large_repo` | `bool` | `False` | Sets policy allow for this call |
| `max_reference_scan_bytes` | `int \| None` | `None` | Override config when set |
| `max_reference_scan_ops` | `int \| None` | `None` | Override config when set |
| `max_non_code_share` | `float \| None` | `None` | Override config when set |
| `max_total_bytes` | `int \| None` | `None` | Override config when set |
| `max_file_count` | `int \| None` | `None` | Override config when set |
| `timeout_seconds` | `int \| None` | `None` | Override config when set |

Existing parameters (`project_path`, `output`, `config`, modality flags, etc.) unchanged.

## Return / errors

- **Success**: `IndexResult` with path to complete graph (unchanged shape).
- **Preflight reject**: raise a dedicated error type (e.g. `LargeRepoError`) subclassing an existing domain error; message includes tripped gates and remediation. MUST NOT return success with missing graph.
- **Timeout**: raise dedicated `IndexTimeoutError` (or equivalent) including phase name; MUST NOT return success.
- Serve layer maps these to HTTP 4xx with JSON `detail` (reject) and 504 or 408 for timeout — exact status documented in serve help/tests when implemented; must not return 200 with empty graph.

## Library reuse

Slash-command / MCP / OpenClaw wrappers MUST call `api.index` (or equivalent) with the same kwargs rather than reimplementing ignore/cost logic.
