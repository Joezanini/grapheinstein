# Feature Specification: Docs and PDF Parsers

**Feature Branch**: `004-docs-pdf-parsers`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "Extend parsers in grapheinstein: Markdown, TXT, RST: section headers, links; PDF: extract text with PyMuPDF, chunk by sections; Create nodes for concepts/headings, edges mentions, section_of; Add grapheinstein index --include-docs --include-pdfs"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Index Documentation Structure (Priority: P1)

A developer indexes a local project with documentation files (Markdown, plain text, and reStructuredText). With documentation inclusion enabled, the resulting graph adds nodes for section headings (treated as concepts/headings) and typed relationships: `section_of` linking sections to their parent section or containing document, and `mentions` linking a document or section to linked or referenced targets. Existing file/directory inventory and any prior code-structure enrichment remain intact. Every new relationship from this parsing is labeled as directly extracted from the document structure.

**Why this priority**: Structured doc headings and links are the primary value of this increment for agents answering install, ops, and “where is this explained?” questions.

**Independent Test**: Index a fixture with a Markdown (or RST/TXT) file that has nested headings and at least one link; confirm heading/concept nodes, `section_of` edges for hierarchy, and `mentions` edges for links, each with provenance `extracted`.

**Acceptance Scenarios**:

1. **Given** a project with a Markdown file containing at least two nested section headings, **When** the user runs index with documentation inclusion enabled, **Then** the output graph includes a node for each heading/concept and `section_of` edges that reflect the nesting (child section to parent section or document).
2. **Given** a documentation file with an explicit link (e.g., Markdown link or RST hyperlink) to another indexed path or heading, **When** indexing with documentation inclusion completes, **Then** the graph includes a `mentions` edge from the linking document or section to the resolved target, with provenance `extracted`.
3. **Given** documentation files in Markdown, plain text, and reStructuredText with recognizable section headers, **When** indexing with documentation inclusion enabled, **Then** each format contributes heading/concept nodes and `section_of` relationships consistently with that format’s heading conventions.
4. **Given** ignore rules that exclude some documentation files, **When** the user indexes with documentation inclusion enabled, **Then** ignored files do not contribute heading nodes or doc edges.

---

### User Story 2 - Index PDF Documents by Section (Priority: P1)

A developer indexes a project that includes PDF files. With PDF inclusion enabled, the tool extracts readable text from each PDF offline, chunks that text into sections (using detected headings or equivalent section boundaries), and adds section/concept nodes plus `section_of` relationships into the same project graph. Failed or unreadable PDFs are recorded without aborting the entire index when other files succeed.

**Why this priority**: PDFs are a first-class modality in the product constitution; section-aware chunks make long manuals queryable alongside code and docs.

**Independent Test**: Index a fixture containing a multi-section PDF (and optionally a corrupt PDF); confirm section nodes and `section_of` edges for the valid PDF, and that a bad PDF does not fail the whole index.

**Acceptance Scenarios**:

1. **Given** a project with a PDF that contains multiple detectable sections or headings, **When** the user runs index with PDF inclusion enabled, **Then** the graph includes nodes for those sections/concepts and `section_of` edges tying them to the PDF file (and to parent sections when nesting is detectable).
2. **Given** a PDF whose text can be extracted locally without network access, **When** indexing with PDF inclusion completes, **Then** section content used for graph nodes is derived from that extracted text (not from a remote service).
3. **Given** a PDF that cannot be opened or yields no usable text, **When** indexing with PDF inclusion runs, **Then** the tool records the failure for that file (e.g., warning or failed-file metadata), continues indexing other files, and still writes a valid graph for successful inputs.
4. **Given** ignore rules that exclude a PDF, **When** the user indexes with PDF inclusion enabled, **Then** that PDF does not contribute section nodes or PDF-related edges.

---

### User Story 3 - Opt Into Docs and PDFs via Index Flags (Priority: P1)

A developer (or agent) controls whether documentation and PDF parsing run for a given index by passing explicit flags: `--include-docs` and `--include-pdfs`. Without those flags, index behavior matches the prior increment for docs/PDF structure extraction (no new heading/section graph enrichment from those modalities), while file/directory inventory of those paths may still appear as before.

**Why this priority**: Explicit opt-in keeps large projects fast by default and matches the requested CLI contract.

**Independent Test**: Index the same fixture three ways—default flags, `--include-docs` only, and `--include-pdfs` only—and confirm heading/section enrichment appears only for the modalities enabled by the flags.

**Acceptance Scenarios**:

1. **Given** a project with both Markdown docs and PDFs that have sections, **When** the user runs index without `--include-docs` and without `--include-pdfs`, **Then** the graph does not gain new heading/concept or PDF-section nodes from those parsers (existing inventory/code behavior unchanged).
2. **Given** the same project, **When** the user runs `grapheinstein index` with `--include-docs`, **Then** documentation heading/concept nodes and doc `section_of`/`mentions` edges appear, and PDF section enrichment does not (unless `--include-pdfs` is also set).
3. **Given** the same project, **When** the user runs index with `--include-pdfs`, **Then** PDF section/concept nodes and related `section_of` edges appear, and documentation structure enrichment does not (unless `--include-docs` is also set).
4. **Given** both `--include-docs` and `--include-pdfs`, **When** indexing completes, **Then** both documentation and PDF structure enrichments are present in one graph output.

---

### Edge Cases

- Documentation file with no headings: file node remains; no heading nodes required; index still succeeds.
- Empty or whitespace-only documentation or PDF: succeed without inventing fake sections; optionally record empty extraction.
- Broken Markdown/RST link targets that cannot be resolved to an indexed file or heading: omit the `mentions` edge or attach only when resolvable; do not invent targets.
- Ambiguous link or heading targets: prefer unambiguous resolution; skip ambiguous `mentions` rather than guessing incorrectly.
- Nested vs flat PDF section detection: if only page/block boundaries are available, treat top-level chunks as sections of the PDF file via `section_of`.
- Very large documentation trees or multi-hundred-page PDFs: indexing completes offline; progress/logging remains usable; individual file failures do not abort the run.
- Encrypted or image-only PDFs with no extractable text: treat as extraction failure for that file; do not require OCR in this increment.
- Concurrent or repeated index with flags changed: later run’s graph reflects the flags used for that run (no silent merge of prior doc/PDF enrichment unless the product already defines merge semantics—default is replace output graph for that index invocation).

## Requirements *(mandatory)*

<!--
  Grapheinstein constitution constraints in scope for this feature:
  - Local-first / offline-capable defaults; no required cloud APIs
  - CLI subcommands; portable graph.json for agent reuse
  - Typed edges with provenance: extracted | inferred
  - Modalities covered: documentation (Markdown, TXT, RST) and PDF; code inventory from prior features retained
-->

### Functional Requirements

- **FR-001**: System MUST support documentation structure extraction for Markdown, plain text (TXT), and reStructuredText (RST) files when documentation inclusion is enabled.
- **FR-002**: For included documentation files, system MUST create graph nodes for section headings (concepts/headings), including enough identity metadata to locate them in the source (at least file path and heading text; line or offset when available).
- **FR-003**: For included documentation files, system MUST create `section_of` edges from each section/heading node to its parent section or containing document file, with provenance `extracted`.
- **FR-004**: For included documentation files, system MUST create `mentions` edges for explicit links (and equivalent cross-references) when the target resolves to an indexed file, heading, or other graph entity, with provenance `extracted`.
- **FR-005**: System MUST support PDF text extraction and section chunking when PDF inclusion is enabled, producing section/concept nodes and `section_of` edges with provenance `extracted`, entirely offline.
- **FR-006**: Users MUST be able to enable documentation parsing via `grapheinstein index --include-docs` and PDF parsing via `grapheinstein index --include-pdfs` (combinable); without each flag, the corresponding structure enrichment MUST NOT run.
- **FR-007**: System MUST continue to respect `.gitignore` (and configured ignore rules) so ignored docs and PDFs do not contribute structure nodes or edges.
- **FR-008**: System MUST NOT abort the entire index solely because one documentation or PDF file fails to parse; failures MUST be reported and successful files MUST still contribute to the output graph.
- **FR-009**: New edges from this feature MUST use provenance `extracted` (not `inferred`); this increment MUST NOT require cloud APIs or remote models.
- **FR-010**: Output MUST remain a portable project graph suitable for agent reuse (same documented graph persistence path/format as existing index), including prior file/dir (and code, when present) nodes alongside new doc/PDF structure.
- **FR-011**: Plain-text (TXT) section detection MUST recognize common heading conventions sufficient for fixtures (e.g., underlined headings and/or lines that match simple heading patterns); files without detectable headings MUST still index successfully as files only.

### Key Entities

- **Heading / Concept Node**: A section heading or concept derived from a documentation or PDF section; attributes include stable id, type (heading/concept), source path, heading/title text, and location (line/offset/page when available).
- **Document / PDF File Node**: Existing or retained file node for the source path; docs/PDF structure attaches via edges rather than replacing inventory.
- **`section_of` Edge**: Relates a section/heading node to its parent section or containing file; provenance `extracted`.
- **`mentions` Edge**: Relates a document or section to a linked/referenced target entity; provenance `extracted`.
- **Parse Failure Record**: Non-fatal record (warning and/or metadata) that a specific doc/PDF could not be structured, without failing the whole index.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a fixture with nested Markdown (or RST) headings and at least one resolvable link, enabling documentation inclusion produces heading/concept nodes and correct `section_of` / `mentions` relationships with `extracted` provenance in a single index run.
- **SC-002**: On a fixture with a multi-section PDF, enabling PDF inclusion produces section/concept nodes and `section_of` edges from extracted text without any network dependency.
- **SC-003**: Default index (no `--include-docs` / `--include-pdfs`) on a mixed docs+PDF fixture does not add doc/PDF structure nodes; enabling each flag independently adds only that modality’s structure.
- **SC-004**: At least 95% of well-formed documentation files in a fixture set yield expected heading nodes when `--include-docs` is set; at least one intentionally broken PDF does not prevent a successful graph write when other files succeed.
- **SC-005**: A developer or agent can enable docs and/or PDFs using only the documented index flags and obtain an updated portable graph without changing unrelated index behavior (ignore rules, output path, existing modalities).

## Assumptions

- `--include-docs` and `--include-pdfs` are opt-in; omitting them preserves prior index behavior regarding doc/PDF *structure* enrichment (file nodes for those paths may still appear from inventory).
- “Concepts/headings” in this increment means section heading nodes derived from document/PDF structure, not LLM-inferred topic entities.
- Documentation extensions in scope: `.md` / `.markdown`, `.txt`, `.rst` (and `.rest` if already treated as RST elsewhere); other markup formats are out of scope.
- PDF text extraction uses a local PDF library path (PyMuPDF as the intended extractor per product direction); image-only OCR is out of scope for this increment.
- Link resolution for `mentions` follows the same unambiguous-target preference as existing basename/`references` behavior: skip ambiguous targets.
- Existing `references` (filename mention) edges from prior features remain; this feature adds typed `mentions` for explicit doc links/cross-references and does not rename historical `references` edges in this increment.
- Code Tree-sitter parsing and query commands (`explain`, `path`, `ask`) are unchanged except that the enriched graph must remain consumable by existing visualize/status flows.
- Schema versioning: if new node/edge types require a documented schema bump, that bump is part of delivering this feature’s portable graph contract.
