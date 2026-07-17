# Feature Specification: Tree-sitter Code Parsers

**Feature Branch**: `003-tree-sitter-parsers`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "Add Tree-sitter support to grapheinstein parsers. Support Python, JavaScript, TypeScript, Java, Go, Rust, C++, SQL. For each source file: Parse AST; Extract: functions, classes, methods, imports, calls; Create nodes for each entity with location (line); Edges: imports, calls, defines, etc. Label every edge as \"extracted\". Update index command to process code files. Configurable languages."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Index Code Structure into the Project Graph (Priority: P1)

A developer indexes a local project that contains source files in one or more supported languages. In addition to the existing file and directory inventory, the resulting graph includes nodes for code entities found in those files (functions, classes, methods, and related extractable symbols) with source location (at least starting line), and typed relationships among them and their containing files (such as defines, imports, and calls). Every new relationship is labeled as directly extracted from source structure.

**Why this priority**: Structure-aware code entities and relationships are the core value of this increment; without them, later agent queries cannot reason about call/import structure beyond filenames.

**Independent Test**: Index a small multi-file fixture with known functions, a class/method, an import, and a call; confirm the graph contains the expected entity nodes (with line locations) and defines/imports/calls edges, each with provenance `extracted`.

**Acceptance Scenarios**:

1. **Given** a project with at least one supported-language source file defining a function, **When** the user runs index, **Then** the output graph includes a node for that function with a location that includes the starting line number in its source file.
2. **Given** a source file that defines a class with a method, **When** indexing completes, **Then** the graph includes nodes for the class and method and a `defines` (or equivalent containment-of-definition) relationship from the owning file or class to each defined entity.
3. **Given** a source file that imports another module or symbol resolvable within the indexed project (or representable as an import target), **When** indexing completes, **Then** the graph includes an `imports` edge from the importing file (or importing entity) to the import target, with provenance `extracted`.
4. **Given** a function or method that calls another function or method resolvable within the indexed project, **When** indexing completes, **Then** the graph includes a `calls` edge from caller to callee with provenance `extracted`.
5. **Given** ignore rules that exclude some source files, **When** the user indexes the project, **Then** ignored source files do not contribute code-entity nodes or code edges.

---

### User Story 2 - Configure Which Languages Are Parsed (Priority: P1)

A developer (or agent operator) controls which languages participate in code-structure extraction—either all supported languages by default, a subset via local configuration, or an override for a single index run—so large or mixed projects can skip languages they do not care about.

**Why this priority**: Configurable language scope is an explicit product requirement and keeps indexing practical on large multi-language trees.

**Independent Test**: Index the same fixture twice—once with only one language enabled and once with all default languages—and confirm only matching file types gain code-entity nodes in the restricted run, while file/dir inventory behavior remains intact.

**Acceptance Scenarios**:

1. **Given** no language configuration is supplied, **When** the user indexes a project, **Then** code-structure extraction runs for all supported languages present in the project (Python, JavaScript, TypeScript, Java, Go, Rust, C++, SQL).
2. **Given** the user configures a subset of languages (via local config and/or an index-run override), **When** indexing completes, **Then** only source files for the enabled languages receive code-entity extraction; other files still appear as file nodes if discovery includes them.
3. **Given** an unknown or unsupported language name in the language configuration, **When** the user runs index, **Then** the tool fails with a clear validation error naming the invalid language and does not write a success graph for that run.

---

### User Story 3 - Surviving Partial Parse Failures (Priority: P2)

A developer indexes a messy real-world tree that includes unsupported extensions, syntax-broken files, or files that cannot be parsed. Indexing still completes with a usable graph: successful files contribute code structure; failed files remain as file nodes (from the inventory) without aborting the whole run, and the developer can see that some files were skipped for structure extraction.

**Why this priority**: Real projects are imperfect; a brittle all-or-nothing parse would block adoption of code indexing.

**Independent Test**: Index a fixture that mixes valid supported files with one intentionally invalid supported-language file and one unsupported extension; confirm the run succeeds, valid entities appear, and the invalid/unsupported files do not crash the command.

**Acceptance Scenarios**:

1. **Given** a supported-language file with unparseable content, **When** indexing runs, **Then** the overall index succeeds, that file remains represented as a file node when discovery includes it, and no fabricated code-entity edges are invented for the failed parse.
2. **Given** files with extensions outside the enabled language set, **When** indexing runs, **Then** those files are not required to produce code-entity nodes; indexing completes successfully.
3. **Given** at least one parse skip or failure occurred, **When** indexing finishes, **Then** the user can tell from progress, logs, or summary that some files were not fully structure-extracted (without needing to inspect the graph by hand).

---

### Edge Cases

- Project with only non-code files: index succeeds; graph retains file/dir inventory behavior; zero code-entity nodes is acceptable.
- Empty or whitespace-only source file for an enabled language: no code-entity nodes required; file node still present.
- Duplicate symbol names in different files: each entity is distinct (identity includes file and location or equivalent disambiguation); edges connect the correct instances.
- Ambiguous call or import targets (multiple possible callees/modules): create an edge only when the target can be resolved confidently within the indexed project; otherwise omit the edge or attach only to a clearly documented unresolved-import representation—do not invent false links between unrelated symbols.
- Nested functions / local helpers: extract when the language structure exposes them as named definitions; anonymous or ephemeral constructs may be omitted.
- Generated or vendored code not ignored by `.gitignore`: parsed like any other enabled-language file unless the user excludes the language or path via ignore/config.
- Very large files or repositories: indexing remains local/offline; long runs stay usable via progress or logging; partial failure of one file must not abort the whole index.
- Language enabled but no files of that type present: succeed with no error.
- Re-index overwrite of an existing graph file: same overwrite behavior as the current index command (overwrite without prompting when the path is writable).

## Requirements *(mandatory)*

<!--
  Grapheinstein constitution constraints in scope for this feature:
  - Local-first / offline-capable defaults; no required cloud APIs
  - CLI index subcommand enrichment; portable graph.json for agent reuse
  - Typed edges with provenance: extracted | inferred (this increment: extracted only for code-structure edges)
  - Modalities: multi-language code (+ SQL as a structured language); docs/PDF/image/media out of scope
  - Structure-aware parsing per architecture guidance (Tree-sitter or equivalent)
-->

### Functional Requirements

- **FR-001**: The existing `grapheinstein index` command MUST process enabled-language source files for code-structure extraction in addition to the current file/directory inventory and existing inventory relationships.
- **FR-002**: Structure extraction MUST support these languages when enabled: Python, JavaScript, TypeScript, Java, Go, Rust, C++, and SQL.
- **FR-003**: For each successfully parsed source file in an enabled language, the system MUST extract definitions for functions, classes, and methods when those constructs exist in the language and file.
- **FR-004**: For each successfully parsed source file, the system MUST extract import relationships and call relationships when those constructs exist in the language and file.
- **FR-005**: The graph MUST include a node for each extracted code entity (at minimum: function, class, and method definitions). Each such node MUST include identity suitable for later queries, a type/kind, association to its source file, and a location that includes at least the starting line number.
- **FR-006**: The graph MUST include typed directed edges for code relationships, including at least: `defines` (file or owning type → defined entity), `imports` (importer → import target), and `calls` (caller → callee). Additional clearly named extracted relationship types MAY be added when useful (e.g., `contains` for class→method) provided they remain typed and labeled.
- **FR-007**: Every edge created by code-structure extraction in this feature MUST carry provenance exactly `extracted` (not `inferred`).
- **FR-008**: Users MUST be able to configure which of the supported languages are enabled for structure extraction via local configuration, with a documented way to override the set for a single index run.
- **FR-009**: When no language configuration is provided, all eight supported languages MUST be enabled by default.
- **FR-010**: Indexing MUST continue when individual files fail to parse or are skipped; the overall command MUST still produce a valid graph whenever the project root is readable and the output path is writable.
- **FR-011**: Code-structure indexing MUST run entirely locally with no required network or cloud services.
- **FR-012**: Discovery and ignore behavior from the existing index flow MUST continue to apply: ignored paths MUST NOT contribute code-entity nodes or code edges.
- **FR-013**: Existing file and directory nodes and inventory edges (e.g., `contains`, basename `references`) MUST remain available; this feature extends the graph rather than replacing the inventory model.
- **FR-014**: On invalid language configuration (including unknown language names), unreadable project root, or unwritable output, the CLI MUST exit non-zero with a clear error message and MUST NOT write a success graph for that failed run.
- **FR-015**: Human-readable progress, warnings, and errors MUST go to the interactive console stream; the graph file MUST remain valid machine-readable JSON without interleaved log text.
- **FR-016**: Visualize (and other existing consumers of the graph file) MUST remain usable on graphs that include the new node and edge kinds—at minimum by summarizing counts that include the new types without crashing.

### Key Entities

- **Code Entity Node**: A structured symbol extracted from source (function, class, or method at minimum). Attributes include stable identity, kind/type, source file path, name (when available), and location (at least start line).
- **Defines Edge**: Directed relationship from a file (or owning class/type) to a code entity defined there; provenance `extracted`.
- **Imports Edge**: Directed relationship from an importing file or entity to an imported module/symbol target; provenance `extracted`.
- **Calls Edge**: Directed relationship from a calling function/method (or file-level caller when appropriate) to a callee; provenance `extracted`.
- **Language Configuration**: The set of enabled languages for structure extraction (default: all supported languages), supplied via local config and/or per-run override.
- **Graph Artifact**: Portable JSON graph file produced by index, now enriched with code-entity nodes and code relationship edges alongside file/dir inventory.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a fixture project containing known definitions in each of at least three supported languages, indexing produces code-entity nodes for 100% of those intentionally planted named functions/classes/methods, each with a correct starting line (±0 lines from the fixture’s documented line).
- **SC-002**: For a fixture with a known import and a known call between indexed symbols, indexing produces the corresponding `imports` and `calls` edges in 100% of those controlled cases, each with provenance `extracted`.
- **SC-003**: When indexing is restricted to a single enabled language, 100% of code-entity nodes come from files of that language; disabling a language removes structure extraction for that language without removing ordinary file nodes for those paths.
- **SC-004**: A mixed fixture with one deliberately broken source file and several valid ones completes indexing successfully; valid files still contribute their expected entities, and the broken file does not abort the run.
- **SC-005**: A developer can index a sample project of at least 200 non-ignored source files across two or more enabled languages and receive a graph file in under 3 minutes on a typical developer laptop (excluding package install time), entirely offline.
- **SC-006**: After a successful code-enriched index, visualize (or equivalent summary) reports totals that account for the new node/edge kinds without failure, and counts match the graph file contents.
- **SC-007**: First-time users can enable a language subset using only documented configuration or CLI flags, with no network setup required.

## Assumptions

- This feature builds on the existing directed file/directory index (file|dir nodes, `contains`, basename `references`) and does not remove those capabilities.
- “Tree-sitter support” in the product sense means structure-aware AST-based extraction consistent with the project constitution’s parsing guidance; planning may choose the concrete parser stack.
- Supported languages for this increment are exactly: Python, JavaScript, TypeScript, Java, Go, Rust, C++, and SQL. Other languages are out of scope unless later configured as extensions.
- File-to-language mapping uses conventional extensions and common filename patterns (e.g., `.py`, `.js`/`.mjs`/`.cjs`, `.ts`/`.tsx`, `.java`, `.go`, `.rs`, `.cpp`/`.cc`/`.cxx`/`.hpp`/`.h` as appropriate for C++, `.sql`). Ambiguous headers may be treated conservatively (skip or parse only when confidently C++).
- For SQL, “functions/classes/methods” map to the closest natural constructs (e.g., functions/procedures and, when clearly present, typed objects); `imports`/`calls` apply only when the dialect constructs make them meaningful (e.g., references to other routines); absence of class-like constructs in a file is not an error.
- Import and call edges are best-effort within the indexed project: unresolved external packages need not create edges to non-existent nodes; fabricating incorrect cross-links is worse than omission.
- Import and call *sites* are primarily modeled as edges; dedicated nodes for every import/call expression are optional unless needed for location fidelity—definition entities (function/class/method) are mandatory nodes.
- All code-structure edges in this increment are provenance `extracted`; LLM/heuristic `inferred` edges remain out of scope.
- Language configuration defaults to all eight languages; users may narrow via config and/or a per-run override (flag or equivalent).
- Docs-only, PDF, image, audio/video parsers, and query commands (`explain`, `path`, `ask`) remain out of scope except that existing visualize/status behavior must tolerate the enriched graph.
- Slash-command and MCP hosting remain out of scope.
- Offline operation includes using locally available parser grammars/resources bundled or installed with the tool; no runtime download requirement for default operation.
