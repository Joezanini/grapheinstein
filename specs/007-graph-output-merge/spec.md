# Feature Specification: Valid Graph Output, Compression, Versioning & Merge

**Feature Branch**: `007-graph-output-merge`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Ensure grapheinstein index always outputs valid graph.json (NetworkX node_link_data format) with all metadata. Add compression option, versioning (graph_v1.json), and `grapheinstein merge` for combining graphs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Index Always Produces a Valid, Complete Graph Artifact (Priority: P1)

A developer (or agent) runs `grapheinstein index` on a project and always receives a portable graph file that is structurally valid in the documented NetworkX node-link data shape, includes the required envelope and graph-level metadata, and preserves every node and edge attribute collected during indexing—including each node's `metadata` map and every edge's relationship type and provenance. Downstream tools can load the file without repair or guessing.

**Why this priority**: Invalid or incomplete graph files break agent reuse, visualization, and merge; correctness of the primary artifact is the foundation for compression, versioning, and merge.

**Independent Test**: Index a fixture project that exercises multiple node types and edges with metadata; confirm the written file validates against the documented portable graph contract (required top-level fields, nodes with `id`/`type`/`metadata`, links with `source`/`target`/`type`/`provenance`, graph-level metadata present) and that known metadata keys from the index run are present on the corresponding nodes and edges.

**Acceptance Scenarios**:

1. **Given** a readable project path, **When** the user runs index with an output path, **Then** the written file is valid portable graph JSON in NetworkX node-link data form (directed, non-multigraph envelope with `nodes` and `links`) and includes required graph-level metadata such as project root and generation time.
2. **Given** an index run that produced nodes with non-empty `metadata` and edges with provenance (and any conditional edge attributes required by the current schema), **When** the output file is inspected, **Then** those attributes are present and unchanged in the written artifact—no silent dropping of metadata.
3. **Given** an empty or fully ignored project, **When** indexing succeeds, **Then** the output is still a valid graph document (at minimum a well-formed envelope with a root or empty node/link lists as defined by the current schema), not a truncated or non-JSON file.
4. **Given** indexing fails before a successful write, **When** the command exits, **Then** it does not leave behind a success-looking but invalid graph file at the intended output path (no partial corrupt success artifact).

---

### User Story 2 - Optionally Compress Graph Output (Priority: P2)

A developer indexing a large project wants a smaller on-disk artifact. They enable a compression option on index (and can also compress when writing merged graphs) and receive a gzip-compressed graph file that decompresses back to the same valid portable JSON.

**Why this priority**: Compression reduces storage and transfer cost for large graphs but is optional; uncompressed valid output remains the default path.

**Independent Test**: Index the same fixture twice—once without compression and once with—and confirm the compressed file is smaller or equal in size for a non-trivial graph, decompresses to JSON that matches the uncompressed graph content (same nodes, links, and metadata), and that tools that accept compressed input can read it when supported.

**Acceptance Scenarios**:

1. **Given** a successful index, **When** the user enables the compression option, **Then** the tool writes a gzip-compressed graph file (recognizable compressed extension or documented compressed path) instead of (or as specified for) plain JSON.
2. **Given** a gzip-compressed graph file produced by Grapheinstein, **When** it is decompressed, **Then** the result is the same valid portable graph JSON that would have been written without compression.
3. **Given** compression is not requested, **When** the user indexes, **Then** the default remains an uncompressed `.json` graph file.

---

### User Story 3 - Versioned Graph Snapshots on Index (Priority: P2)

A developer wants to keep prior index results while re-indexing. They enable versioning so each successful index writes a numbered snapshot such as `graph_v1.json`, `graph_v2.json`, and so on, without losing earlier versions.

**Why this priority**: Versioned snapshots support comparison and rollback of project knowledge over time; secondary to always-valid primary output.

**Independent Test**: Run index twice into a versioning-enabled output directory; confirm `graph_v1.json` and `graph_v2.json` both exist, each is a valid complete graph, and earlier files are not overwritten by later runs.

**Acceptance Scenarios**:

1. **Given** versioning is enabled and no prior versioned files exist in the target location, **When** the user indexes successfully, **Then** the tool writes `graph_v1.json` (or `graph_v1.json.gz` if compression is also enabled) as the first snapshot.
2. **Given** `graph_v1.json` already exists from a prior run, **When** the user indexes again with versioning enabled, **Then** the tool writes the next free number (`graph_v2.json`, then `graph_v3.json`, …) and does not overwrite existing `graph_vN.json` files.
3. **Given** the user also specifies a primary `--output` path (e.g., `graph.json`), **When** versioning is enabled, **Then** the primary output path is still written (or updated) for “latest” use **and** a new numbered `graph_vN` snapshot is written.
4. **Given** versioning is disabled (default), **When** the user indexes to an explicit output path, **Then** behavior matches today’s single-file write (overwrite that path) with no automatic `graph_vN` files.

---

### User Story 4 - Merge Multiple Graphs into One (Priority: P1)

A developer (or agent) has two or more valid graph files—e.g., from different subprojects, incremental runs, or versioned snapshots—and runs `grapheinstein merge` to combine them into a single portable graph that preserves nodes, edges, provenance, and metadata from the inputs.

**Why this priority**: Combining graphs is a first-class agent and library-building workflow called out by the product direction; it is independently valuable once valid graph files exist.

**Independent Test**: Merge two fixture graphs with disjoint node ids; confirm the result contains the union of nodes and links with metadata intact. Separately merge graphs with an intentional node-id conflict and confirm the documented conflict behavior.

**Acceptance Scenarios**:

1. **Given** two or more valid graph input files, **When** the user runs `grapheinstein merge` with those inputs and an output path, **Then** a single valid portable graph file is written containing the union of nodes and links from the inputs.
2. **Given** inputs that share identical nodes/edges (same ids and equivalent attributes), **When** merge runs, **Then** duplicates are collapsed to a single occurrence (no redundant identical copies).
3. **Given** two inputs that use the same node `id` but disagree on required identity attributes (e.g., different `type` or conflicting `metadata` that cannot be safely unified), **When** merge runs, **Then** the command fails with a clear non-zero error naming the conflicting id and does not write a success artifact.
4. **Given** merge output options for compression and/or an explicit output path, **When** the user requests them, **Then** the merged graph is written accordingly and remains loadable as a valid graph.
5. **Given** an invalid or unreadable input graph, **When** merge is attempted, **Then** the command fails with a clear error identifying the bad input and does not produce a partial merged success file.

---

### Edge Cases

- Index interrupted or failing mid-run: no corrupt “successful” graph left at the final output path.
- Output directory missing for versioned or merge writes: create parent directories when reasonable, or fail with a clear path error if creation is impossible.
- Compression enabled with versioning: numbered files use the compressed extension (e.g., `graph_v1.json.gz`).
- Mixing compressed and uncompressed inputs to merge: accept both; normalize to one valid merged graph; honor the output compression flag for the result.
- Schema/version envelope mismatch across merge inputs (incompatible documented schema generations): fail with a clear error rather than silently combining incompatible shapes.
- Empty merge input list or fewer than two inputs: fail with a clear usage error.
- Very large graphs: compression and merge complete locally without network access; long runs remain usable via progress or logging on stderr.
- Graph-level metadata on merge (e.g., `project_root`, `generated_at`): result includes fresh `generated_at` and documented merge provenance in graph-level metadata (e.g., list of source paths or a merge marker); conflicting `project_root` values are recorded without inventing a false single root when roots differ.

## Requirements *(mandatory)*

<!--
  Grapheinstein constitution constraints in scope for this feature:
  - Local-first / offline-capable defaults; no required cloud APIs
  - CLI subcommands; portable graph.json for agent reuse
  - Typed edges with provenance: extracted | inferred (preserved through write/merge)
  - Portable NetworkX node-link graph.json as the documented persistence format
  - Modalities: this feature is format/CLI I/O — all modalities already present in input graphs are preserved; no new parsers
-->

### Functional Requirements

- **FR-001**: Every successful `grapheinstein index` MUST write a graph artifact that validates as the documented portable NetworkX node-link data format (required envelope fields, `nodes`, `links`) for the current schema generation.
- **FR-002**: The written graph MUST include all node attributes required by the current schema, including each node's `metadata` object (empty object when no attributes apply), and MUST NOT drop collected metadata on write.
- **FR-003**: The written graph MUST include all edge attributes required by the current schema, including relationship `type` and `provenance` (`extracted` or `inferred`), and any conditional attributes required for those edge types.
- **FR-004**: Graph-level metadata REQUIRED by the current schema (at minimum project root and generation timestamp) MUST be present on every successful index write.
- **FR-005**: Users MUST be able to enable an optional compression mode that writes the graph as gzip-compressed portable JSON.
- **FR-006**: Users MUST be able to enable optional output versioning that writes incremental snapshot files named `graph_v1.json`, `graph_v2.json`, … (or the compressed equivalent) without overwriting prior numbered snapshots.
- **FR-007**: When versioning is enabled together with an explicit primary output path, the system MUST write both the primary “latest” file and a new numbered snapshot.
- **FR-008**: Users MUST be able to run `grapheinstein merge` with two or more graph input paths and an output path to produce one combined portable graph.
- **FR-009**: Merge MUST preserve node and edge payload attributes (including provenance and metadata) from inputs when combining non-conflicting data.
- **FR-010**: Merge MUST reject conflicting node identities (same `id`, incompatible attributes) with a clear error and non-zero exit; it MUST NOT write a success output in that case.
- **FR-011**: Merge MUST accept gzip-compressed graph inputs as well as plain JSON when those files were produced in the documented compressed form.
- **FR-012**: Index and merge MUST operate fully offline with no required cloud services.
- **FR-013**: Human-readable errors and progress MUST go to stderr; the graph artifact itself MUST be written only to the declared file path(s), not mixed into stdout as the primary success artifact.

### Key Entities

- **Graph Artifact**: A portable directed graph document in NetworkX node-link data form with schema envelope, graph-level metadata, nodes, and links.
- **Node**: Project entity with stable `id`, `type`, and `metadata` map.
- **Edge (Link)**: Directed relationship with `source`, `target`, relationship `type`, and `provenance`; may carry additional schema-required attributes.
- **Versioned Snapshot**: Numbered on-disk graph file (`graph_vN`) representing one successful write in a versioning-enabled location.
- **Merged Graph**: Single graph artifact produced by combining multiple input graph artifacts under documented union and conflict rules.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of successful index runs on fixture projects used for acceptance, the output file passes portable-graph validation (envelope, nodes, links, required metadata) with zero silent metadata loss for attributes present in the in-memory index result.
- **SC-002**: Users can enable compression and obtain a gzip graph file that, after decompression, byte-for-byte or structurally matches the uncompressed graph content for the same index run (same nodes, links, and metadata).
- **SC-003**: With versioning enabled, three successive successful index runs produce `graph_v1`, `graph_v2`, and `graph_v3` snapshots, all readable, with earlier snapshots unchanged after later runs.
- **SC-004**: Users can merge at least two valid disjoint graphs into one valid graph in under 30 seconds for fixture graphs of up to 10,000 combined nodes on a typical developer machine.
- **SC-005**: 100% of intentional merge conflict fixtures (same node id, incompatible attributes) fail with a clear error and leave no success output file.
- **SC-006**: 90% of first-time users (or evaluators following the quickstart) successfully produce a valid graph, optionally compress it, and merge two sample graphs on the first attempt without undocumented workarounds.

## Assumptions

- Compression means gzip of the JSON graph document; default index/merge output remains uncompressed JSON unless the user opts in.
- Versioning uses the `graph_vN.json` naming pattern in the output directory (or beside the primary output); numbering is the next unused positive integer, not a content hash.
- Primary `--output` (e.g., `graph.json`) remains the “latest” pointer when versioning is on; numbered files are additional snapshots.
- Merge requires at least two input graphs; identical duplicate nodes/edges are deduplicated; incompatible same-id nodes are hard failures (no last-write-wins).
- Merge does not re-parse the filesystem; it only combines existing graph artifacts.
- Current schema generation and node/edge allow-lists from prior features remain in force; this feature hardens write completeness and adds I/O/CLI capabilities rather than inventing a new entity taxonomy.
- Existing commands that read graphs (e.g., visualize) SHOULD accept gzip inputs where practical in a follow-on polish if not already covered; minimum bar for this feature is index write + merge read of compressed files.
- No cloud storage, remote merge service, or UI is in scope.
