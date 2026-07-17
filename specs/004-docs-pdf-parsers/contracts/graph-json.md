# Contract: graph.json (schema_version 4.0.0)

**Feature**: `004-docs-pdf-parsers`  
**Format**: JSON document compatible with NetworkX node-link data, plus required envelope fields  
**Breaks**: schema `3.0.0` (code entities without heading/docs-PDF edges) — readers MUST reject older artifacts; users re-index

## Top-level object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Must be `"4.0.0"` for this feature |
| `directed` | boolean | yes | Must be `true` |
| `multigraph` | boolean | yes | Must be `false` |
| `graph` | object | yes | Graph-level metadata |
| `nodes` | array | yes | Node list |
| `links` | array | yes | Edge list |

### `graph` metadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_root` | string | yes | Absolute path that was indexed |
| `generated_at` | string | yes | ISO-8601 UTC timestamp |
| `languages` | array of strings | no | Enabled code language ids for this run |
| `include_docs` | boolean | no | Whether docs structure enrichment ran |
| `include_pdfs` | boolean | no | Whether PDF structure enrichment ran |
| `parse_skips` | integer | no | Count of per-file structure skips |

## Nodes

### File / directory

Unchanged: `id`, `type` ∈ {`file`, `dir`}, `metadata`.

### Code entity

Unchanged: `type` ∈ {`function`, `class`, `method`}; `id` = `{file}::{kind}::{name}::{start_line}`; metadata includes `name`, `language`, `file`, `start_line`.

### Heading

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | `{file}::heading::{slug}::{locator}` |
| `type` | string | yes | `"heading"` |
| `metadata` | object | yes | Must include `name`, `file`, `source`; plus `start_line` and/or `page` |

Example:

```json
{
  "id": "docs/guide.md::heading::installation::3",
  "type": "heading",
  "metadata": {
    "name": "Installation",
    "file": "docs/guide.md",
    "source": "markdown",
    "start_line": 3,
    "level": 2
  }
}
```

PDF example locator:

```json
{
  "id": "manual.pdf::heading::introduction::p1",
  "type": "heading",
  "metadata": {
    "name": "Introduction",
    "file": "manual.pdf",
    "source": "pdf",
    "page": 1,
    "level": 1
  }
}
```

## Links (edges)

Each element MUST include:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | yes | Source node `id` |
| `target` | string | yes | Target node `id` |
| `type` | string | yes | One of: `contains`, `references`, `defines`, `imports`, `calls`, `section_of`, `mentions` |
| `provenance` | string | yes | `"extracted"` or `"inferred"` (this feature writes `"extracted"` for new doc/PDF edges) |

### `section_of`

```json
{
  "source": "docs/guide.md::heading::install-steps::10",
  "target": "docs/guide.md::heading::installation::3",
  "type": "section_of",
  "provenance": "extracted"
}
```

Top-level section → file:

```json
{
  "source": "docs/guide.md::heading::installation::3",
  "target": "docs/guide.md",
  "type": "section_of",
  "provenance": "extracted"
}
```

### `mentions`

```json
{
  "source": "docs/guide.md::heading::installation::3",
  "target": "README.md",
  "type": "mentions",
  "provenance": "extracted"
}
```

### Retained edge types

`contains`, `references`, `defines`, `imports`, `calls` retain schema 3 semantics and examples.

## Minimal valid envelope (illustrative)

```json
{
  "schema_version": "4.0.0",
  "directed": true,
  "multigraph": false,
  "graph": {
    "project_root": "/tmp/project",
    "generated_at": "2026-07-16T12:00:00Z",
    "include_docs": true,
    "include_pdfs": false
  },
  "nodes": [
    {"id": ".", "type": "dir", "metadata": {}},
    {"id": "docs/guide.md", "type": "file", "metadata": {}},
    {
      "id": "docs/guide.md::heading::installation::3",
      "type": "heading",
      "metadata": {
        "name": "Installation",
        "file": "docs/guide.md",
        "source": "markdown",
        "start_line": 3,
        "level": 2
      }
    }
  ],
  "links": [
    {
      "source": "docs/guide.md::heading::installation::3",
      "target": "docs/guide.md",
      "type": "section_of",
      "provenance": "extracted"
    }
  ]
}
```

## Load rejection

Readers MUST reject the artifact when:

- `schema_version` is missing or not `"4.0.0"` (including `"3.0.0"`)
- Required top-level fields are missing
- A node or link violates the allow-lists above

## Migration notes

- Users with `3.0.0` graphs must **re-index** to obtain `4.0.0`
- Re-index without `--include-docs` / `--include-pdfs` still produces `4.0.0` inventory + code structure (no heading enrichment)
- Downstream agents should accept `heading` nodes and `section_of` / `mentions` edges when present
