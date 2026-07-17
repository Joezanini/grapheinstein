# Feature Specification: Directed File Graph Index & Visualize

**Feature Branch**: `002-digraph-index-visualize`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "Extend the grapheinstein CLI. Add NetworkX DiGraph. Nodes: {\"id\": path, \"type\": \"file|dir\", \"metadata\": {...}}. Edges: contains (dir->file), references (basic filename mentions). Implement `grapheinstein index <path> --output graph.json` that builds and saves node_link_data JSON. Add `grapheinstein visualize --input graph.json` (simple console summary or export dot)."

## Clarifications

### Session 2026-07-16

- Q: How should `references` edges detect a basic filename mention of another indexed file’s basename? → A: Whole-token match (basename bounded by non-identifier characters)
- Q: Should visualize accept older inventory graphs that used `kind: file|directory`? → A: New-shape only; reject old-shape graphs with a clear error; users re-index
- Q: When DOT export is requested from visualize, how should output behave? → A: Write DOT to a file path; still print the console summary
- Q: How should indexing treat symbolic links under the project path? → A: Do not follow; include the symlink itself as a `file` node; do not traverse into the target
- Q: If index `--output` or visualize DOT file path already exists, what should happen? → A: Overwrite the existing file without prompting

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Index a Project into a Directed Graph (Priority: P1)

A developer points Grapheinstein at a local project folder and receives a portable directed graph file. The graph includes every discovered file and directory as a node, parent-to-child containment links, and simple cross-file reference links when one file's contents mention another indexed file by name. The developer chooses where the graph file is written.

**Why this priority**: A directed graph with containment and basic references is the core artifact this increment delivers; without it, visualization and later agent queries have nothing useful to consume.

**Independent Test**: Run index against a small fixture project with nested folders and at least one text file that mentions another file's basename; confirm the output graph lists file/dir nodes, contains edges for the hierarchy, and at least one references edge for the mention.

**Acceptance Scenarios**:

1. **Given** Grapheinstein is installed and a readable project path exists, **When** the user runs `grapheinstein index <path> --output graph.json`, **Then** a graph file is written at the chosen output path containing nodes for discovered files and directories.
2. **Given** a project with nested directories, **When** indexing completes, **Then** each directory-to-child relationship appears as a directed `contains` edge from the parent directory to the child file or directory.
3. **Given** a text file in the project whose contents mention another indexed file's basename as a whole token (not merely as a substring inside a longer identifier), **When** indexing completes, **Then** a directed `references` edge exists from the mentioning file to the mentioned file.
4. **Given** a project with ignore rules (e.g., `.gitignore`), **When** the user indexes the project, **Then** ignored paths do not appear as nodes or endpoints of edges.

---

### User Story 2 - Inspect a Graph from the Console (Priority: P1)

After indexing, a developer (or agent operator) opens an existing graph file and sees a concise console summary: how many files and directories, how many containment and reference links, and a short sample of notable nodes or edges—enough to confirm the index looks right without opening a GUI.

**Why this priority**: Immediate human-readable feedback closes the index → verify loop and is the default visualize experience.

**Independent Test**: Produce a graph file, run visualize with that file as input, and confirm the summary counts match the graph contents and the command exits successfully.

**Acceptance Scenarios**:

1. **Given** a valid graph file from a prior index, **When** the user runs `grapheinstein visualize --input graph.json`, **Then** the tool prints a human-readable summary including node counts by type and edge counts by relationship type.
2. **Given** a missing or unreadable input path, **When** the user runs visualize, **Then** the tool exits with a non-zero status and a clear error message (and does not crash).
3. **Given** a graph file written in the prior inventory shape (`kind` / `directory` without the required `type` / `dir` / `metadata` fields), **When** the user runs visualize, **Then** the tool fails with a clear validation error indicating the graph format is unsupported and that re-indexing is required.

---

### User Story 3 - Export a DOT View of the Graph (Priority: P2)

A developer wants to open the same graph in an external diagram tool. They ask visualize to write a DOT representation to a file path while still seeing the usual console summary.

**Why this priority**: DOT export supports deeper inspection and sharing but is secondary to console verification for day-to-day use.

**Independent Test**: Run visualize against a known graph with a DOT export option; confirm the output is valid DOT that includes the same nodes and edges present in the input graph.

**Acceptance Scenarios**:

1. **Given** a valid graph file, **When** the user runs visualize with DOT export requested to a file path, **Then** that file contains a DOT document representing the graph's nodes and edges.
2. **Given** DOT export is requested to a file path, **When** the command succeeds, **Then** the console summary is still printed (same counts/sample expectations as visualize without DOT export).

---

### Edge Cases

- Project path does not exist or is not a directory: fail with a clear error and non-zero exit status; do not write a success graph.
- Output path is not writable: fail with a clear error and non-zero exit status.
- Output path (graph JSON or DOT file) already exists and is writable: overwrite without prompting.
- Empty project (no files, or only ignored files): succeed with a valid graph that may contain only the project root directory node and zero or more edges as appropriate.
- Ambiguous filename mentions (same basename in multiple directories): create references only when the mention can be resolved unambiguously to a single indexed file; skip or omit ambiguous matches rather than guessing incorrectly.
- Basename appears only as a substring inside a longer identifier (e.g., `main` inside `domain`): do not create a `references` edge; matching requires a whole token.
- Binary or non-text files: still appear as nodes and participate in `contains` edges; they are not scanned for filename mentions.
- Very large trees: indexing and visualize complete locally without network access; long runs remain usable via progress or logging.
- Graph file missing required structure for visualize: fail with a clear validation error naming what is wrong.
- Graph file uses the prior inventory node shape (`kind` / `directory`) instead of `type` / `dir` / `metadata`: fail with a clear unsupported-format error; do not silently reinterpret fields.
- Filename mention of the file's own basename: do not create a self-`references` edge.
- Symbolic link under the project: include it as a `file` node (with a `contains` edge from its parent directory) but do not follow/traverse the target; do not index the target's tree via the link.

## Requirements *(mandatory)*

<!--
  Grapheinstein constitution constraints in scope for this feature:
  - Local-first / offline-capable defaults; no required cloud APIs
  - CLI subcommands; portable graph.json for agent reuse
  - Typed edges with provenance: extracted | inferred
  - Modalities for this increment: filesystem inventory + basic text filename mentions (code/docs as text); SQL/PDF/image/media parsers out of scope
-->

### Functional Requirements

- **FR-001**: Users MUST be able to run `grapheinstein index <path> --output <file>` to build a directed project graph and write it to the specified output path.
- **FR-002**: The written graph MUST be a portable JSON document in node-link form suitable for later loading by Grapheinstein and external consumers (directed graph of project entities).
- **FR-003**: Every node MUST include: `id` (project-relative path), `type` of exactly `file` or `dir`, and a `metadata` object (may be empty) for extensible attributes.
- **FR-004**: The graph MUST include directed `contains` edges from each directory to its immediate child files and directories discovered during indexing.
- **FR-005**: The graph MUST include directed `references` edges from a file to another indexed file when the source file's text content contains a whole-token mention of the target file's basename (filename without directory path), where the basename is bounded by non-identifier characters (not a bare substring inside a longer token).
- **FR-006**: Every edge MUST carry a relationship type (`contains` or `references`) and a provenance label of exactly `extracted` or `inferred`. Containment and basename-mention references MUST be labeled `extracted` for this increment.
- **FR-007**: Discovery MUST respect project ignore rules (at minimum `.gitignore`) so ignored paths are excluded from nodes and edges.
- **FR-008**: Users MUST be able to run `grapheinstein visualize --input <graph-file>` to load a previously written graph and print a console summary (node counts by type, edge counts by relationship type, and a brief sample of entries).
- **FR-009**: Users MUST be able to request DOT export from visualize by supplying an output file path; the tool MUST write the DOT document to that path and MUST still print the console summary on success.
- **FR-010**: Index and visualize MUST run entirely locally with no required network or cloud services.
- **FR-011**: Human-readable messages MUST go to the interactive console stream; the graph JSON file contents MUST remain valid machine-readable JSON without interleaved log text.
- **FR-012**: On invalid paths, unreadable input, unwritable output, or malformed graph input, the CLI MUST exit non-zero with a clear error message.
- **FR-013**: Indexing MUST continue past individual unreadable files when possible, recording omission via warning/log rather than aborting the entire run, unless the project root itself is unreadable.
- **FR-014**: Graph load paths (including visualize) MUST accept only the node shape defined in FR-003 (`id`, `type` as `file`|`dir`, `metadata`). Graphs that use the prior inventory fields (`kind` / `directory`) MUST be rejected with a clear unsupported-format error; silent field mapping or on-load migration MUST NOT occur.
- **FR-015**: Indexing MUST NOT follow symbolic links. A symlink MUST be represented as a `file` node at its path under the project; its target MUST NOT be traversed for discovery.
- **FR-016**: When writing the index graph file or a visualize DOT file to a path that already exists, the tool MUST overwrite that file without interactive confirmation (provided the path is writable).

### Key Entities

- **Graph Node**: A file or directory in the project. Attributes: `id` (relative path), `type` (`file` | `dir`), `metadata` (extensible key/value details such as size or extension when available).
- **Contains Edge**: Directed relationship from a directory to an immediate child file or directory; provenance `extracted`.
- **References Edge**: Directed relationship from one file to another indexed file based on a whole-token basename mention in the source file's text; provenance `extracted`.
- **Graph Artifact**: Portable JSON graph file (typically `graph.json`) in node-link form, consumed by visualize and later agent features.
- **Project Root**: The folder path supplied to `index`; boundary for discovery and relative path identities.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can index a sample project of at least 50 non-ignored files and receive a graph file with matching file/dir node counts in under 2 minutes on a typical developer laptop (excluding package install time).
- **SC-002**: For a fixture with a known directory tree, 100% of parent–child relationships among indexed paths appear as `contains` edges, and no `contains` edge points outside the indexed node set.
- **SC-003**: For a fixture where file A’s text contains a whole-token mention of the unique basename of file B, indexing produces a `references` edge from A to B in 100% of such controlled cases; substring-only occurrences inside longer identifiers do not create edges.
- **SC-004**: After a successful index, visualize’s console summary reports node and edge counts that match the graph file contents.
- **SC-005**: When DOT export is requested for a valid graph, 100% of nodes and edges from the input appear in the DOT file (by identity/label), the console summary still prints accurate counts, and the command completes without requiring network access.
- **SC-006**: Failed runs (missing project path, missing input graph, unwritable output, or unsupported prior graph shape) always return a non-zero exit status and name the problem in plain language.
- **SC-007**: First-time users complete the index → visualize console-summary loop using only documented CLI flags, with no config file required.

## Assumptions

- This feature extends the existing installable `grapheinstein` CLI (from the prior project-index increment); install packaging itself is already available and not re-specified here.
- Node shape for this increment uses `type` values `file` and `dir` plus a `metadata` object, as requested; this supersedes the earlier inventory field names (`kind` / `directory`) for new graph writes. Older inventory graphs are not readable; users must re-index. Schema versioning/documentation of the break belongs in planning.
- “Basic filename mentions” means case-sensitive whole-token basename matches in UTF-8 text files against other indexed file basenames (bounded by non-identifier characters); no language-aware import/AST resolution in this increment.
- Ambiguous basename matches (multiple indexed files sharing a name) do not create a `references` edge.
- Binary files are included as nodes and in `contains` edges but are skipped for mention scanning.
- Symlinks are treated as `file` nodes and are not followed; mention scanning may skip them if they are not readable as UTF-8 text (same as other non-text files).
- Default visualize behavior is the console summary; DOT export is opt-in by providing a DOT output file path, and does not replace the console summary.
- Default output filename remains `graph.json` when the user relies on documented defaults; `--output` explicitly sets the write path for index.
- Existing writable output files are overwritten without prompts, supporting non-interactive/scripted use.
- Directory-to-directory containment is included (not only dir→file) so the full tree is represented.
- `status` and user config from the prior increment remain available if already implemented; this feature does not remove them.
- Code/docs AST parsing, SQL/PDF/media ingestion, inferred edges, and query commands (`explain`, `path`, `ask`) remain out of scope.
- Slash-command and MCP hosting remain out of scope.
