# Feature Specification: CLI Project Index Skeleton

**Feature Branch**: `001-cli-project-index`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "Create a Python CLI tool called grapheinstein with main command and index/status subcommands; respect .gitignore; config from home or --config; pretty output and logging; installable package; working CLI that creates a basic nodes list in graph.json."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install and Index a Project (Priority: P1)

A developer installs Grapheinstein on their machine, points it at a local project folder, and receives a portable graph file that lists the project's files and directories as nodes. Ignored paths (such as those covered by `.gitignore`) do not appear in the inventory. The developer can choose where the graph file is written.

**Why this priority**: Without a working install path and basic inventory output, no later parsing or query features can be used or validated.

**Independent Test**: Install the package in a clean environment, run the tool against a small fixture project that includes ignored and non-ignored paths, and confirm a graph file is written with file and directory nodes for non-ignored paths only.

**Acceptance Scenarios**:

1. **Given** Grapheinstein is installed, **When** the user runs the tool with a project path and an output path, **Then** a graph file is created at that output path containing nodes for discovered files and directories.
2. **Given** a project with a `.gitignore` that excludes a directory (e.g., `node_modules/` or `.venv/`), **When** the user indexes the project, **Then** ignored paths are omitted from the node inventory.
3. **Given** a valid project path, **When** the user runs the default project-path invocation (without naming a subcommand), **Then** indexing runs and produces the same kind of graph inventory as the explicit index command.
4. **Given** an output path that does not yet exist, **When** indexing completes successfully, **Then** the parent directories are created as needed and the graph file is written.

---

### User Story 2 - Check Index Status (Priority: P2)

After indexing (or when a graph file already exists), a developer runs a status command to see a concise summary of what was indexed—counts of files, directories, and other high-level stats—without re-reading every file manually.

**Why this priority**: Status gives quick confidence that indexing worked and helps agents/users decide whether to re-index.

**Independent Test**: Produce a graph file for a fixture project, run status against that project or graph, and verify the reported counts match the inventory.

**Acceptance Scenarios**:

1. **Given** a previously written graph file for a project, **When** the user runs status, **Then** the tool displays counts of file nodes, directory nodes, and total nodes in a human-readable summary.
2. **Given** no graph file exists yet for the target, **When** the user runs status, **Then** the tool reports clearly that no index is available (and does not crash).

---

### User Story 3 - Configure Defaults Locally (Priority: P3)

A developer sets preferred defaults (such as default output path or logging verbosity) in a user-level config file, or overrides them for a single run with a config flag, without changing how core indexing behaves.

**Why this priority**: Local configuration supports the local-first workflow and reduces repeated flags, but indexing must work with sensible defaults even when no config file exists.

**Independent Test**: Run index with no config file present (defaults work); then provide a config file via the standard user location or an explicit config flag and confirm those settings apply.

**Acceptance Scenarios**:

1. **Given** no user config file exists, **When** the user indexes a project, **Then** indexing succeeds using built-in defaults.
2. **Given** a config file at the standard user location (`~/.grapheinstein/config.yaml`), **When** the user runs a command without `--config`, **Then** settings from that file are applied.
3. **Given** the user passes an explicit `--config` path, **When** the command runs, **Then** that file's settings take precedence over the standard user location for that run.

---

### Edge Cases

- Project path does not exist or is not a directory: fail with a clear error message and non-zero exit status.
- Project path is not readable (permission denied): fail with a clear error; do not write a partial graph silently as success.
- Output path is not writable: fail with a clear error before or during write; exit non-zero.
- Empty project (only ignored files or no files): succeed and write a valid graph with zero or only root-directory nodes as appropriate; status reflects empty inventory.
- Broken or unreadable `.gitignore`: continue with a warning and best-effort ignore handling (or no ignores) rather than aborting the whole index.
- Invalid or malformed config file: fail with a clear validation error identifying the config problem.
- Very large directory trees: indexing completes without requiring network access; progress or logging remains usable for long runs.

## Requirements *(mandatory)*

<!--
  Grapheinstein constitution constraints in scope for this feature:
  - Local-first / offline-capable defaults; no required cloud APIs
  - CLI subcommands; structured graph file for agent reuse
  - File/directory nodes as the Phase-1 inventory (edges/provenance expand later)
  - Respect .gitignore during discovery
-->

### Functional Requirements

- **FR-001**: Users MUST be able to install Grapheinstein as a local package and invoke a `grapheinstein` command from their shell.
- **FR-002**: Users MUST be able to index a project by supplying a project path and receive a portable graph file (default name `graph.json` unless overridden).
- **FR-003**: The default invocation with a project path MUST perform indexing (equivalent outcome to the explicit `index` subcommand).
- **FR-004**: The system MUST provide an `index` subcommand that scans the project folder and builds an initial inventory of file and directory nodes.
- **FR-005**: The system MUST provide a `status` subcommand that reports inventory statistics (at minimum: file count, directory count, total nodes, and output/graph location when known).
- **FR-006**: Discovery MUST respect `.gitignore` rules in the target project so ignored paths are excluded from the inventory.
- **FR-007**: The graph file MUST include a nodes list representing discovered files and directories, each with enough metadata for later enrichment (at minimum: stable identity, path, and node kind of file or directory).
- **FR-008**: For this increment, relationship edges beyond basic containment MAY be omitted or limited to directory-contains-child links; if any edges are written, each MUST be labeled with provenance `extracted` or `inferred` per the project constitution.
- **FR-009**: Users MUST be able to load configuration from the standard user config path `~/.grapheinstein/config.yaml` or from a path supplied via `--config`.
- **FR-010**: Indexing and status MUST work with built-in defaults when no config file is present.
- **FR-011**: The CLI MUST present human-readable progress and summaries suitable for interactive use, and MUST emit diagnostic logs suitable for troubleshooting failed runs.
- **FR-012**: Machine-oriented graph output MUST be written to the declared file path; human-oriented messages MUST NOT corrupt that file's contents.
- **FR-013**: All indexing and status operations MUST run locally without requiring network access or cloud services.
- **FR-014**: On failure (bad path, permissions, invalid config), the CLI MUST exit with a non-zero status and a clear error message.

### Key Entities

- **Project Root**: The folder the user points the tool at; the boundary for discovery.
- **Inventory Node**: A file or directory entry in the graph, with path and kind metadata.
- **Graph Artifact**: The portable output file (typically `graph.json`) consumed later by agents and query features.
- **Ignore Rules**: Patterns from `.gitignore` (and equivalent) that exclude paths from discovery.
- **User Config**: Optional local settings (defaults for output path, verbosity, and similar) loaded from the user config location or an explicit config path.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can install the tool and produce a graph file for a sample project of at least 50 tracked files in under 2 minutes on a typical developer laptop (excluding install time for system package managers).
- **SC-002**: For a fixture project with known ignored paths, 100% of paths matching ignore rules are absent from the written node inventory, and 100% of intentionally included fixture files appear as nodes.
- **SC-003**: After a successful index, `status` reports file and directory counts that match the node inventory in the graph file.
- **SC-004**: With no config file present, first-time users complete index successfully using only project path and optional output path arguments.
- **SC-005**: Failed runs (missing project path, unwritable output, invalid config) always return a non-zero exit status and a message that names the problem in plain language.
- **SC-006**: Indexing a project requires no network connectivity once the tool is installed.

## Assumptions

- This feature is limited to the installable CLI skeleton plus file/directory inventory; code parsing, document/media ingestion, entity extraction, and query commands (`explain`, `path`, `ask`) are out of scope and will follow in later features.
- Default invocation with a project path runs indexing; `status` is always an explicit subcommand.
- Default output filename is `graph.json` in the current working directory unless config or `--output` overrides it.
- Only `.gitignore` is required for ignore behavior in this increment; additional ignore files (e.g., `.ignore`) may be added later.
- If directory-containment edges are included, they are marked `extracted`; inferred edges are not required in this increment.
- Pretty terminal output and structured logging are part of the user experience for this CLI; exact libraries are chosen at planning/implementation time consistent with the project constitution.
- The tool is distributed as an installable local package exposing the `grapheinstein` console command; package layout is decided in the implementation plan.
- Slash-command and MCP server hosting are out of scope for this feature.
