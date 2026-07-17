# Data Model: Docs and PDF Parsers

**Feature**: `004-docs-pdf-parsers`  
**Schema version**: `4.0.0` (breaking vs `3.0.0`)

## Entities

### Project Root

Unchanged: absolute path supplied to `index`; node ids are POSIX-relative to this root.

### Index Run Options

| Field | Type | Rules |
|-------|------|-------|
| `include_docs` | bool | Default `false`; when true, run Markdown/TXT/RST structure extract |
| `include_pdfs` | bool | Default `false`; when true, run PDF extract + section chunking |

Persisted on artifact `graph.include_docs` / `graph.include_pdfs` for the run that produced the file.

### Graph Node (file / dir)

Unchanged from schema 3.x: `type` ∈ {`file`, `dir`}; `id` relative path; `metadata` object.

### Graph Node (code entity)

Unchanged from schema 3.x: `function` | `class` | `method` with metadata `name`, `language`, `file`, `start_line`.

### Graph Node (heading)

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `id` | string | yes | `{file}::heading::{slug}::{locator}` (see research R4) |
| `type` | string | yes | Exactly `heading` |
| `metadata` | object | yes | Must include `name` (string), `file` (file node id), `source` (`markdown`\|`txt`\|`rst`\|`pdf`). Must include `start_line` (positive int) **and/or** `page` (positive int). Optional: `level`, `end_line`, `end_page` |

**Rules**:
- `metadata.file` MUST equal an existing `type: file` node `id`
- Locator in `id` MUST match `start_line` or `p{page}` / disambiguated form used at creation
- Empty heading text → slug `untitled`; still allowed if a structural boundary was detected
- No heading nodes when docs/PDF inclusion is off, even if `.md`/`.pdf` file nodes exist

### Contains Edge

Unchanged: directory → immediate child; `provenance: extracted`.

### References Edge

Unchanged: basename mention file → file; `provenance: extracted`. Distinct from `mentions`.

### Defines / Imports / Calls Edges

Unchanged from schema 3.x; still `extracted` when produced by code parsers.

### Section-of Edge

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `source` | string | yes | Child `heading` node id |
| `target` | string | yes | Parent `heading` id or containing `file` id |
| `type` | string | yes | Exactly `section_of` |
| `provenance` | string | yes | Exactly `extracted` |

**Rules**:
- Every heading has exactly one `section_of` edge to its parent (heading or file)
- No self-loops; both endpoints must exist
- At most one `section_of` edge per heading source (dedupe)

### Mentions Edge

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `source` | string | yes | `heading` or `file` id (section containing the link, else file) |
| `target` | string | yes | Resolved `file` or `heading` id |
| `type` | string | yes | Exactly `mentions` |
| `provenance` | string | yes | Exactly `extracted` |

**Rules**:
- Create only when the link/cross-reference resolves **unambiguously** within the indexed project
- Skip broken or ambiguous targets (no invented nodes)
- At most one `mentions` edge per ordered pair
- Not emitted for PDF free-text unless an explicit resolvable target is detected (v1 docs-focused; PDF primarily contributes `section_of`)

### Parse Skip Accounting

| Field | Location | Rules |
|-------|----------|-------|
| `parse_skips` | graph metadata and/or stats | Non-negative int; includes code + docs + PDF per-file structure failures for the run |

### Graph Artifact

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `schema_version` | string | yes | `"4.0.0"` |
| `directed` | boolean | yes | `true` |
| `multigraph` | boolean | yes | `false` |
| `graph` | object | yes | `project_root`, `generated_at`; MAY include `languages`, `include_docs`, `include_pdfs`, `parse_skips` |
| `nodes` | array | yes | file/dir + code entities + headings |
| `links` | array | yes | All edge types with `type` + `provenance` |

## Validation rules (load)

| Condition | Behavior |
|-----------|----------|
| Missing `schema_version` / `nodes` / `links` / `graph` | Load error |
| `schema_version` ≠ `4.0.0` | Unsupported-format error (re-index) |
| Unknown node `type` | Load error |
| Unknown edge `type` | Load error |
| Edge `provenance` not `extracted`\|`inferred` | Load error |
| Heading missing required metadata | Load error |

## State / lifecycle

1. Discover non-ignored paths → file/dir nodes + `contains`
2. Basename `references`
3. Code structure (enabled languages)
4. Optional docs structure → headings + `section_of` + `mentions`
5. Optional PDF structure → headings + `section_of`
6. Serialize overwrite of `--output`

No merge with a previous on-disk graph: each successful index **replaces** the artifact.
