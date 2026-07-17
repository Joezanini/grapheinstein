# Research: Docs and PDF Parsers

**Feature**: `004-docs-pdf-parsers`  
**Date**: 2026-07-16

## R1. PDF extraction library

**Decision**: Use **PyMuPDF** (`pymupdf` on PyPI; `import fitz`) as a **required** install dependency. Extract text with page iteration; prefer `Document.get_toc()` for section boundaries when TOC entries exist; otherwise detect heading-like lines (font-size / bold heuristics via text dict blocks when available) and fall back to **one section per page** with titles `Page N`.

**Rationale**: Spec and constitution call for a dedicated local PDF library; user input names PyMuPDF. Required dependency keeps `--include-pdfs` working after a normal `pip install` without optional-extra footguns. Offline after install.

**Alternatives considered**:
- `pypdf` / `pdfminer.six` — weaker TOC/font structure for section chunking.
- Optional extra `[pdf]` — rejected for v1; flags imply the capability should be present.
- OCR (Tesseract) for image-only PDFs — out of scope; treat as non-fatal extract failure.

## R2. Schema version bump

**Decision**: Bump `schema_version` to **`4.0.0`**. Widen allow-lists for node type `heading` and edge types `section_of`, `mentions`. Loaders **reject** `3.0.0` and older with a clear re-index message (fail-closed, same as 3←2). No silent migration.

**Rationale**: Constitution: schema changes are breaking; consumers must detect new modality nodes/edges.

**Alternatives considered**:
- Stay on `3.0.0` and widen types — rejected (no capability signal).
- Dual-read 3.x + 4.x — deferred.

## R3. Documentation parsers (Markdown, TXT, RST)

**Decision**: Implement **lightweight line/regex scanners** in `core/parsers/docs.py` (no new Markdown/RST framework dependency for v1):

| Format | Extensions | Headings | Links |
|--------|------------|----------|-------|
| Markdown | `.md`, `.markdown` | ATX ATX `#`…`######`; optional Setext `===` / `---` underlines | `[text](target)`, bare `<path>` angle links when path-like |
| TXT | `.txt` | Setext-style underline (`===`/`---`); lines that are entirely title-case/short ALL-CAPS followed by blank line (conservative) | Explicit `http(s)://` and relative path tokens matching indexed files (same unambiguous resolve as mentions) — prefer Markdown-style `[text](target)` if present |
| RST | `.rst`, `.rest` | Overline/underline adornment lines (`===`, `---`, `~~~`, etc.) with title line | `` `text <target>`_ `` and simple `doc:` / path-like references when resolvable |

Build a heading stack by level to emit `section_of` edges (child → parent heading, or child → file for top-level).

**Rationale**: Spec needs headers + links, not full AST rendering. Avoiding mistune/docutils keeps the dependency surface small and offline-simple; fixtures can use conventional markup.

**Alternatives considered**:
- `markdown-it-py` / `docutils` — richer but heavier; revisit if scanners prove insufficient.
- Tree-sitter markdown grammar — unnecessary for heading/link extract only.

## R4. Heading / concept node identity

**Decision**:

- Node `type`: **`heading`** (covers “concepts/headings” for this increment; no separate LLM concept type).
- Node `id`: `{file}::heading::{slug}::{locator}` where:
  - `slug` is a stable slugify of heading text (lowercase, non-alnum → `-`, collapse dashes; empty → `untitled`)
  - `locator` is 1-based **start_line** for text docs, or **`p{page}`** (1-based page) for PDFs when line is unavailable; if both page and block index exist, prefer `p{page}-b{block}` only when needed to disambiguate collisions within the same file
- Required `metadata`: `name` (heading text), `file` (file node id), `source` (`markdown`|`txt`|`rst`|`pdf`), plus `start_line` **or** `page` (at least one location field). Optional: `level` (int), `end_line`, `end_page`.

**Rationale**: Mirrors code-entity id style (`file::kind::name::locator`) for agent-friendly keys and uniqueness.

**Alternatives considered**:
- Type `concept` only — vaguer for structural sections.
- UUID ids — poor diffs/agent UX.

## R5. Edge semantics: `section_of` and `mentions`

**Decision**:

- **`section_of`**: `source` = child heading id, `target` = parent heading id **or** containing file id; `provenance: extracted`. Exactly one parent per heading (stack discipline).
- **`mentions`**: `source` = heading id (preferred when link appears under that section) or file id if outside any section; `target` = resolved file or heading id; `provenance: extracted`. Create only when resolution is **unambiguous** within the indexed graph. Do **not** rename or remove existing basename `references` edges.
- Link targets: resolve relative paths against the document’s directory; fragment `#anchor` matches a heading slug in the same file (or linked file) when unique; skip unresolved/ambiguous.

**Rationale**: Matches spec wording (“section_of linking sections to their parent”) and prior unambiguous-resolution policy for `references`/`imports`/`calls`.

**Alternatives considered**:
- Parent → child `contains`-style for sections — rejected; reserve `contains` for filesystem; use `section_of` as specified.
- Merge `mentions` into `references` — rejected; spec requires distinct `mentions` for explicit links.

## R6. CLI flags and pipeline order

**Decision**:

- Add boolean flags `--include-docs` / `--include-pdfs` (default **false**). Combinable.
- Wire into `index_project` / `build_inventory_graph` after inventory + references + code structure.
- Record on graph metadata: `include_docs`, `include_pdfs` (booleans) for the run.
- Default-path rewriter: treat both as **flag options without values** (not in `_OPTS_WITH_VALUE`).
- Config YAML keys optional in v1; CLI flags are the required contract. If config keys are added later, CLI flags still win when set.

Pipeline:

1. Discover + inventory (`contains`)
2. Basename `references`
3. Code Tree-sitter merge (existing)
4. If `--include-docs`: docs extract + resolve `mentions`
5. If `--include-pdfs`: PDF extract + `section_of` (PDF `mentions` only if explicit URL/path text is reliably detected — **v1: section structure only for PDF**, no fragile free-text link mining unless TOC destinations map cleanly)

**Rationale**: Spec opt-in; keeps default index fast. PDF free-text “links” are unreliable; TOC-based internal destinations may emit `mentions` only when they resolve to another heading/file uniquely (optional enhancement; not required for SC-002).

**Alternatives considered**:
- Always-on docs/PDF — rejected (explicit flags).
- Config-only toggles — flags are user-required.

## R7. Failure handling and stats

**Decision**: Per-file try/except around docs/PDF parse: log warning (Loguru), increment `parse_skips` (shared counter or separate `doc_parse_skips` / `pdf_parse_skips` rolled into summary). Never abort the whole index for one bad file. Encrypted/empty/image-only PDFs count as skips. Empty docs with no headings: success, zero heading nodes.

**Rationale**: Spec FR-008 and constitution multi-modal resilience.

## R8. Visualize / status

**Decision**: Extend `GraphStats` and console summaries with `heading_count`, `section_of_count`, `mentions_count`. Status/visualize load **only** schema `4.0.0`.

## R1–R8 resolution summary

All Technical Context unknowns resolved: pymupdf required; schema 4.0.0; regex/line docs parsers; `heading` nodes; `section_of`/`mentions`; opt-in flags; non-fatal skips; no OCR.
