# Quickstart Validation: Docs and PDF Parsers

**Feature**: `004-docs-pdf-parsers`  
**Date**: 2026-07-16

Use this guide after implementation to prove the feature end-to-end. Contracts: [cli.md](./contracts/cli.md), [graph-json.md](./contracts/graph-json.md). Data model: [data-model.md](./data-model.md).

## Prerequisites

- Python 3.11+
- Repo checkout with this feature implemented
- No network required after dependencies (including `pymupdf`) are installed

## Setup

```bash
cd /path/to/grapheinstein
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Fixture project

Create/use `tests/fixtures/docs_pdf_project/` (illustrative layout):

```text
docs_pdf_project/
├── .gitignore                 # e.g. ignored_docs/
├── README.md                  # link target
├── docs/
│   ├── guide.md               # nested ## headings + link to ../README.md
│   ├── notes.txt              # underlined / simple headings
│   └── overview.rst           # RST adornment headings
├── manuals/
│   ├── sample.pdf             # multi-section PDF (TOC or clear headings)
│   └── corrupt.pdf            # truncated/invalid bytes
└── ignored_docs/
    └── secret.md
```

Document expected heading ids (slug + line/page) in fixture README or test constants. Generate `sample.pdf` in test setup or commit a tiny fixture PDF.

## Scenario A — Flags off (no doc/PDF structure)

```bash
grapheinstein index tests/fixtures/docs_pdf_project --output /tmp/grapheinstein-v4-default.json
echo $?
```

**Expected**:
- Exit code `0`
- `schema_version` is `"4.0.0"`
- File nodes for docs/PDFs may exist from inventory
- **No** `heading` nodes from docs/PDF parsers
- No `section_of` / `mentions` from this feature
- Code extract still runs for any source files present

## Scenario B — `--include-docs` only

```bash
grapheinstein index tests/fixtures/docs_pdf_project \
  --include-docs \
  --output /tmp/grapheinstein-v4-docs.json
```

**Expected**:
- Heading nodes for `guide.md` / `notes.txt` / `overview.rst` with `section_of` hierarchy
- At least one `mentions` edge from the Markdown link to `README.md` (or resolvable heading) with `provenance` `"extracted"`
- Ignored `secret.md` contributes no headings
- PDF files do **not** gain section headings from the PDF parser
- `graph.include_docs` is `true`; `include_pdfs` is false/absent

## Scenario C — `--include-pdfs` only

```bash
grapheinstein index tests/fixtures/docs_pdf_project \
  --include-pdfs \
  --output /tmp/grapheinstein-v4-pdfs.json
```

**Expected**:
- Heading nodes + `section_of` for `sample.pdf`
- `corrupt.pdf` does not abort the run (warning / parse skip); graph still written
- Documentation files do **not** gain heading enrichment from the docs parser
- Exit code `0`

## Scenario D — Both flags

```bash
grapheinstein index tests/fixtures/docs_pdf_project \
  --include-docs --include-pdfs \
  --output /tmp/grapheinstein-v4-both.json
```

**Expected**:
- Combined docs + PDF structure in one artifact
- Summary shows heading and `section_of` / `mentions` counts

## Scenario E — Visualize / status / old schema

```bash
grapheinstein visualize --input /tmp/grapheinstein-v4-both.json
grapheinstein status --output /tmp/grapheinstein-v4-both.json
# Expect failure on a retained 3.0.0 fixture:
grapheinstein visualize --input tests/fixtures/old_schema_v3_graph.json; echo $?
```

**Expected**:
- Summary includes heading / `section_of` / `mentions` counts
- Schema `3.0.0` input exits non-zero with re-index guidance

## Scenario F — Default-path alias with flags

```bash
grapheinstein tests/fixtures/docs_pdf_project --include-docs -o /tmp/grapheinstein-v4-alias.json
```

**Expected**: Same as index with `--include-docs`; flags must not steal the project path token.

## Offline check

With network disabled after install, Scenarios B–D still succeed using only local files and `pymupdf`.
