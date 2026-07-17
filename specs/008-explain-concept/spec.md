# Feature Specification: Explain Concept Subgraph

**Feature Branch**: `008-explain-concept`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Add subcommand: grapheinstein explain <concept> --input graph.json --output subgraph.json. Find node(s) matching concept (fuzzy/vector), return neighborhood (1-2 hops) + natural language summary using local LLM."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Explain a Concept from a Project Graph (Priority: P1)

A developer (or agent) has a portable project graph and wants to understand a concept by name or short phrase. They run `grapheinstein explain` with the concept, an input graph path, and an output path. The tool finds the best-matching node(s) for that concept, extracts a focused neighborhood around those nodes (within 1–2 hops), writes that neighborhood as a portable subgraph file, and produces a natural-language summary of what the concept means in this project based on the neighborhood—using a local language model, offline.

**Why this priority**: Explain is a constitution-listed core query command; without it, users can index graphs but cannot get a human-readable concept answer from them.

**Independent Test**: Given a fixture graph with a known concept node and related neighbors, run explain for that concept; confirm a subgraph file is written containing the match and its neighborhood, and a readable summary is produced that refers to information present in that neighborhood—without requiring cloud APIs.

**Acceptance Scenarios**:

1. **Given** a valid portable input graph containing a node whose label or identity clearly matches the requested concept, **When** the user runs explain with that concept, `--input`, and `--output`, **Then** the tool writes a valid portable subgraph to the output path that includes at least the matched node and its neighbors within the configured hop distance.
2. **Given** a successful match and neighborhood, **When** explain completes with a usable local language model, **Then** the user receives a natural-language summary describing the concept in the context of this project, grounded in the selected neighborhood (not inventing unrelated project structure).
3. **Given** no network access and a local model configured and available, **When** the user runs explain, **Then** matching, subgraph export, and summary generation complete without requiring remote AI services.
4. **Given** a successful explain run, **When** the user inspects the human-readable stream and the output file, **Then** machine-consumable subgraph content is at the declared output path and progress/errors remain on the human-readable stream (not mixed into the subgraph file as unstructured prose).

---

### User Story 2 - Match Concepts by Fuzzy Text and Semantic Similarity (Priority: P1)

Users rarely know exact node IDs. Explain MUST locate concept nodes using fuzzy name/text matching and, when embeddings are available for the graph or can be computed locally, vector/semantic similarity. Results are ranked so the best match(es) drive the neighborhood. If multiple nodes score highly, the tool includes them (within a documented limit) and merges their neighborhoods into one subgraph.

**Why this priority**: Matching quality determines whether explain is useful; exact-ID-only lookup would fail common developer workflows.

**Independent Test**: On a fixture graph, explain with a slightly misspelled or partial concept name returns the intended node; explain with a semantically related phrase (when embeddings are available) returns a relevant node even if the string differs; low-scoring noise nodes are not treated as primary matches.

**Acceptance Scenarios**:

1. **Given** a graph with a node labeled similarly but not identically to the query (e.g., pluralization, partial token, or minor typo), **When** the user runs explain with that approximate phrase, **Then** the tool still selects that node as a match when it is clearly the best candidate.
2. **Given** a graph with embedding-capable node text and a local embedding path available, **When** the user runs explain with a paraphrased concept phrase, **Then** the tool can select a semantically related node even when the exact string does not appear.
3. **Given** several nodes with high match scores for the same query, **When** explain runs, **Then** the subgraph includes up to a documented maximum number of top matches and the union of their neighborhoods within the hop limit.
4. **Given** embeddings are unavailable, **When** the user runs explain, **Then** fuzzy/text matching still works and the command remains usable (vector matching is skipped or degraded with a clear note, not a hard failure of the whole command when a text match exists).

---

### User Story 3 - Control Neighborhood Depth and Handle Misses Gracefully (Priority: P2)

Users can influence how wide the explanation subgraph is (1 or 2 hops; default within that range). When no node matches the concept well enough, the tool fails clearly without writing a misleading “success” subgraph. When the local model is unavailable for summary generation but matching succeeds, the subgraph is still written and the absence of a summary is reported clearly.

**Why this priority**: Depth control and failure clarity make the command reliable for agents and humans; secondary to the happy-path explain loop.

**Independent Test**: Run explain with hop depth 1 and hop depth 2 on the same concept and confirm neighborhood size grows as expected; run with a nonsense concept and confirm a non-zero exit and no false success output; run with model unavailable and confirm subgraph write plus clear messaging about the missing summary.

**Acceptance Scenarios**:

1. **Given** a matched node with distinct 1-hop and 2-hop neighborhoods, **When** the user requests hop depth 1 versus hop depth 2, **Then** the written subgraph includes only nodes/edges within the requested distance (default is 2 hops when the user does not specify).
2. **Given** a concept that matches no node above the documented relevance threshold, **When** the user runs explain, **Then** the tool reports a clear human-readable failure, exits unsuccessfully, and does not leave a success-looking subgraph at the output path.
3. **Given** a successful match but no usable local language model for summarization, **When** the user runs explain, **Then** the subgraph is still written to `--output` and the tool reports that the summary could not be generated (without calling cloud APIs).
4. **Given** a missing, unreadable, or invalid input graph, **When** the user runs explain, **Then** the tool reports a clear error and does not produce a subgraph or summary as if the run succeeded.

---

### Edge Cases

- Empty or whitespace-only concept argument → rejected with a clear usage/validation error.
- Input graph with zero nodes → no match; unsuccessful exit with clear message.
- Concept matches a node with no neighbors → subgraph contains at least the matched node; summary still attempts to describe that node from its own attributes.
- Very large neighborhoods at 2 hops → tool applies a documented safety cap on included nodes/edges and notes truncation if applied.
- Compressed input graphs (if supported by existing loaders) → explain accepts the same graph inputs the rest of the CLI can load.
- Output path already exists → overwritten only on successful completion (no partial corrupt success artifact left mid-failure).
- Ambiguous matches with similar scores → top matches included up to the documented limit; summary acknowledges multiple related entities when more than one primary match is used.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CLI MUST provide an `explain` subcommand of the form `grapheinstein explain <concept> --input <graph> --output <subgraph>` (equivalent option names allowed if documented; concept positional is required).
- **FR-002**: Explain MUST load a portable project graph from `--input` and write a portable subgraph to `--output` in the same documented graph format family used by index/merge (valid for downstream agent reuse).
- **FR-003**: Explain MUST find node(s) matching `<concept>` using fuzzy/text matching, and MUST use local vector/semantic similarity when embeddings are available; matching MUST NOT require cloud services.
- **FR-004**: Explain MUST include in the output subgraph the matched node(s) and their neighborhood within a hop distance of 1 or 2 (default 2), including connecting edges and their existing relationship types and provenance labels.
- **FR-005**: Explain MUST produce a natural-language summary of the concept in project context using a local language model when one is available and configured; summary generation MUST be offline-capable and MUST NOT require cloud APIs.
- **FR-006**: The natural-language summary MUST be delivered on the human-readable output stream (or a documented dedicated summary destination); it MUST NOT replace or corrupt the machine-consumable subgraph file.
- **FR-007**: When multiple nodes match above the relevance threshold, Explain MUST include up to a documented maximum of top matches and merge their neighborhoods into a single subgraph.
- **FR-008**: When no match meets the relevance threshold, Explain MUST fail clearly (non-success exit) and MUST NOT write a success-looking subgraph.
- **FR-009**: When matching succeeds but the local summary model is unavailable, Explain MUST still write the subgraph and MUST report that summary generation was skipped or failed.
- **FR-010**: Explain MUST preserve provenance labels (`extracted` | `inferred`) and relationship types on edges copied into the subgraph; it MUST NOT invent new structural edges without labeling them according to existing provenance rules (summary text is narrative output, not unlabeled graph mutation).
- **FR-011**: Users MUST be able to select hop depth of 1 or 2 via a documented option; invalid values MUST be rejected with a clear error.
- **FR-012**: Progress and errors MUST go to the human-readable stream; the subgraph artifact MUST remain structured portable graph data suitable for agents.
- **FR-013**: Local model and embedding settings MUST be configurable via the project’s existing local configuration mechanisms (and/or CLI overrides), consistent with other local-LLM features.

### Key Entities

- **Concept Query**: The user-supplied phrase used to locate graph nodes (raw text; not necessarily an exact node id).
- **Match Candidate**: A graph node scored against the concept query (identity/label/text and optional embedding similarity), with a relevance score used for ranking and thresholding.
- **Explanation Subgraph**: A portable graph document containing matched node(s), nodes within the hop neighborhood, and the edges connecting them, preserving types and provenance from the input graph.
- **Explanation Summary**: A natural-language description of the concept grounded in the explanation subgraph, produced by a local language model when available.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a fixture graph with a known target concept, users obtain a correct match and a written neighborhood subgraph in under 30 seconds on a typical developer machine when the local model is already warm (or under 60 seconds including cold local-model start), excluding first-time model download.
- **SC-002**: At least 90% of explain runs on a prepared fixture suite with intentionally approximate concept phrases (typos/partials) select the intended primary node as a top match.
- **SC-003**: When hop depth is 2, the output subgraph includes all nodes within 2 hops of each primary match up to any documented safety cap; when hop depth is 1, no node farther than 1 hop appears.
- **SC-004**: In offline evaluation (network disabled), explain completes matching and subgraph export successfully whenever the input graph and local tooling are present; summary also completes when the local model is present.
- **SC-005**: 9 out of 10 evaluators reading the summary alongside the subgraph agree the summary is consistent with subgraph contents and does not invent major entities absent from that neighborhood.
- **SC-006**: On no-match queries, 100% of runs exit unsuccessfully with a clear message and leave no success-looking subgraph at the output path.
- **SC-007**: Agents can load the explain output file with the same graph-loading expectations as other Grapheinstein portable graphs without manual repair.

## Assumptions

- The input is an existing portable graph produced (or merge-compatible with graphs produced) by prior Grapheinstein features; this feature does not re-index the project.
- Default hop depth is 2; users may choose 1. Depths beyond 2 are out of scope for this feature.
- Fuzzy/text matching is always attempted; vector matching is used when local embeddings are available and is skipped gracefully otherwise.
- When multiple strong matches exist, a small top-N set (default on the order of a few nodes, e.g., 3) is included rather than only the single best node.
- Natural-language summary goes to the human-readable stream by default; the `--output` path is reserved for the subgraph artifact.
- Local LLM and embedding configuration reuse the same local-first configuration patterns introduced for LLM enrichment (model name, endpoints on localhost, no cloud requirement).
- A documented relevance threshold decides “no match”; exact numeric default may be set during planning but must be user-overridable if exposed.
- A documented safety cap may truncate extremely large 2-hop neighborhoods to keep explain usable; truncation must be visible to the user when applied.
- Slash-command / MCP surfaces are out of scope for this feature; the CLI subcommand is the delivery vehicle (same library API may be reused later).
- Modalities already present in the input graph (code, docs, SQL, shell, PDF, image, media, concepts) are explainable insofar as they appear as nodes; explain does not add new parsers.
