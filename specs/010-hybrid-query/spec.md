# Feature Specification: Hybrid Natural-Language Query

**Feature Branch**: `010-hybrid-query`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Add: grapheinstein query \"plain language question\" --input graph.json --k 20. Hybrid: vector search on chunks + graph traversal → extract relevant subgraph → LLM generates answer with citations to nodes/edges. Output: answer + subgraph.json + visualization summary."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask a Plain-Language Question Over a Project Graph (Priority: P1)

A developer (or agent) has a portable project graph and wants an answer to an open-ended question in plain language (for example, “How does authentication work?” or “Where is the database connection configured?”). They run `grapheinstein query` with the question, an input graph path, and a result-size limit (`--k`). The tool retrieves the most relevant content chunks and related graph structure, extracts a focused subgraph that supports the question, and produces a grounded natural-language answer that cites specific nodes and edges from that subgraph—using a local language model, offline. Alongside the answer, it writes the supporting subgraph and a short visualization summary of what was retrieved.

**Why this priority**: Query is a constitution-listed core query command (answer a plain-language question by returning a relevant subgraph). Without it, users can explain single concepts and find paths between two endpoints, but cannot ask open questions that span multiple entities.

**Independent Test**: Given a fixture graph with known chunks and relationships about a topic, run query with a question that that topic answers; confirm an answer is produced with citations to nodes/edges present in the written subgraph, a portable subgraph file is written, and a visualization summary is shown—without requiring cloud APIs.

**Acceptance Scenarios**:

1. **Given** a valid portable input graph with content relevant to a plain-language question, **When** the user runs query with that question, `--input`, and `--k`, **Then** the tool produces a natural-language answer grounded in retrieved graph content and writes a portable supporting subgraph.
2. **Given** a successful query, **When** the user inspects the answer, **Then** the answer includes citations that identify specific nodes and/or edges from the supporting subgraph (so a reader can verify claims against the graph).
3. **Given** a successful query, **When** the command completes, **Then** the user also receives a visualization summary describing the supporting subgraph at a glance (scale, key nodes/relationships, or equivalent structural overview)—separate from the full answer prose.
4. **Given** no network access and local embedding/language models configured and available, **When** the user runs query, **Then** retrieval, subgraph extraction, answer generation, and summary complete without requiring remote AI services.

---

### User Story 2 - Hybrid Retrieval: Chunk Similarity Plus Graph Context (Priority: P1)

Open questions are rarely answered by a single node. Query combines (1) similarity search over content chunks associated with the graph and (2) graph traversal from those hits to gather related entities and relationships. The union of retrieved chunks and traversed neighbors becomes the candidate evidence set, which is then reduced to a relevant supporting subgraph (bounded by `--k` and documented safety caps) before answer generation.

**Why this priority**: Hybrid retrieval is the differentiating value of this command versus explain (neighborhood of one concept) or path (route between two endpoints). Chunk-only search misses structure; traversal-only search misses semantic match to the question wording.

**Independent Test**: On a fixture where the best chunk hits are neighbors of the entities needed to answer the question, query includes both the high-similarity chunks’ nodes and their traversed related nodes/edges in the supporting subgraph; an answer that depends only on isolated chunk text without structural context is not required when the graph holds the connecting relationships.

**Acceptance Scenarios**:

1. **Given** a graph with chunk-linked nodes whose text is semantically close to the question, **When** the user runs query, **Then** the tool ranks and selects up to `--k` primary retrieval hits by local similarity (when embeddings are available).
2. **Given** primary retrieval hits, **When** query builds evidence, **Then** it expands via graph traversal from those hits to include related nodes and connecting edges within a documented traversal policy (depth/neighbor limits).
3. **Given** hybrid evidence larger than needed for a focused answer, **When** query extracts the supporting subgraph, **Then** the subgraph remains bounded (respecting `--k` and documented caps) and still contains the citations later used in the answer.
4. **Given** embeddings are unavailable, **When** the user runs query, **Then** the tool falls back to documented non-vector text matching for chunk/node selection when possible, or fails clearly if no usable retrieval path exists—without calling cloud services.

---

### User Story 3 - Control Result Size and Fail Clearly (Priority: P2)

Users control how broad retrieval is with `--k` (default 20). When the question is empty, the graph is invalid, or nothing relevant is found, the tool fails clearly without writing a misleading success subgraph or inventing an answer. When retrieval succeeds but the local answer model is unavailable, the supporting subgraph and visualization summary are still produced and the missing answer is reported clearly.

**Why this priority**: Result-size control and failure clarity make the command reliable for agents and humans; secondary to the happy-path hybrid answer loop.

**Independent Test**: Run query with small and larger `--k` on the same question and confirm evidence/subgraph breadth grows as expected up to caps; run with a nonsense question and confirm unsuccessful exit with no fabricated answer; run with model unavailable and confirm subgraph/summary plus clear messaging about the missing answer.

**Acceptance Scenarios**:

1. **Given** the same question and graph, **When** the user runs query with a smaller `--k` versus a larger `--k` (within allowed bounds), **Then** the primary retrieval set size respects `--k` (default 20 when omitted) and the supporting subgraph does not ignore that bound for primary hits.
2. **Given** a question that yields no retrieval hits above the documented relevance threshold, **When** the user runs query, **Then** the tool reports a clear failure, exits unsuccessfully, and does not leave a success-looking answer or subgraph presented as a confident result.
3. **Given** successful retrieval but no usable local language model for answering, **When** the user runs query, **Then** the supporting subgraph and visualization summary are still produced and the tool reports that answer generation was skipped or failed (without calling cloud APIs).
4. **Given** a missing, unreadable, or invalid input graph, or an empty/whitespace-only question, **When** the user runs query, **Then** the tool reports a clear error and does not produce answer/subgraph outputs as if the run succeeded.

---

### Edge Cases

- Empty or whitespace-only question → rejected with a clear usage/validation error.
- `--k` less than 1, non-integer, or above a documented maximum → rejected with a clear validation error.
- Input graph with zero nodes or no chunk-capable content → unsuccessful exit with clear message when nothing can be retrieved.
- Question matches many weakly related chunks → ranking and `--k` limit primary hits; traversal and caps prevent dumping the entire graph.
- Supporting subgraph very large after traversal → documented safety cap truncates with a visible note in the visualization summary and/or human-readable stream.
- Answer model returns text without usable citations → tool still lists the supporting subgraph’s key cited entities when possible, or reports that citations could not be aligned; it MUST NOT invent node/edge identifiers absent from the subgraph.
- Compressed input graphs (if supported by existing loaders) → query accepts the same graph inputs the rest of the CLI can load.
- Output subgraph path already exists → overwritten only on successful completion of the subgraph write (no partial corrupt success artifact left mid-failure).
- Modalities already in the graph (code, docs, SQL, shell, PDF, image, media, concepts) participate insofar as they appear as nodes/chunks; query does not add new parsers.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CLI MUST provide a `query` subcommand of the form `grapheinstein query "<question>" --input <graph> [--k <n>]` (equivalent option names allowed if documented; the question positional is required).
- **FR-002**: Query MUST load a portable project graph from `--input` in the same documented graph format family used by index/merge/explain/path.
- **FR-003**: Query MUST accept `--k` as the maximum number of primary retrieval hits (default 20) and MUST reject invalid values with a clear error.
- **FR-004**: Query MUST perform hybrid evidence gathering: local similarity search over content chunks (when embeddings or equivalent local signals are available) combined with graph traversal from those hits to related nodes and edges.
- **FR-005**: Query MUST extract a relevant supporting subgraph from the hybrid evidence and write it as a portable graph artifact (default or documented `--output` path for `subgraph.json` or equivalent), suitable for downstream agent reuse.
- **FR-006**: Query MUST generate a natural-language answer to the question using a local language model when one is available and configured; answer generation MUST be offline-capable and MUST NOT require cloud APIs.
- **FR-007**: The answer MUST include citations to nodes and/or edges that appear in the supporting subgraph so claims can be checked against the graph.
- **FR-008**: Query MUST produce a visualization summary of the supporting subgraph (human-readable structural overview: e.g., counts, key nodes, key relationships)—distinct from the full answer and from the machine-consumable subgraph file.
- **FR-009**: Progress and errors MUST go to the human-readable stream; the subgraph artifact MUST remain structured portable graph data. Machine-consumable packaging of the answer (when offered) MUST remain separate from progress/errors.
- **FR-010**: When no evidence meets the relevance threshold, Query MUST fail clearly (non-success exit) and MUST NOT present a confident invented answer or a success-looking empty “success” subgraph.
- **FR-011**: When retrieval succeeds but the local answer model is unavailable, Query MUST still write the supporting subgraph and visualization summary and MUST report that answer generation was skipped or failed.
- **FR-012**: Query MUST preserve provenance labels (`extracted` | `inferred`) and relationship types on edges copied into the supporting subgraph; it MUST NOT invent new structural edges without labeling them according to existing provenance rules (answer text is narrative output, not unlabeled graph mutation).
- **FR-013**: Citations in the answer MUST refer only to nodes/edges present in the supporting subgraph; unknown or fabricated identifiers MUST NOT be presented as graph citations.
- **FR-014**: Local model and embedding settings MUST be configurable via the project’s existing local configuration mechanisms (and/or CLI overrides), consistent with other local-LLM and embedding features.
- **FR-015**: Hybrid retrieval, subgraph extraction, and answering MUST NOT require cloud services; remote APIs remain opt-in only if already allowed elsewhere and MUST NOT be required for core operation.

### Key Entities

- **Question**: The user-supplied plain-language question string used to drive retrieval and answering.
- **Chunk Hit**: A content chunk (linked to one or more graph nodes) scored for relevance to the question, contributing to the primary retrieval set of size up to `--k`.
- **Hybrid Evidence**: The combined set of chunk hits plus nodes/edges reached by traversal from those hits, before final subgraph extraction.
- **Supporting Subgraph**: A portable graph document containing the evidence used for the answer, preserving types and provenance from the input graph.
- **Cited Answer**: A natural-language response to the question that references supporting subgraph nodes and/or edges as citations.
- **Visualization Summary**: A concise human-readable overview of the supporting subgraph’s structure and scale for quick inspection.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a fixture graph with a known answerable question, users obtain an answer, a written supporting subgraph, and a visualization summary in under 60 seconds on a typical developer machine when local models are already warm (or under 120 seconds including cold local-model start), excluding first-time model download.
- **SC-002**: At least 90% of query runs on a prepared fixture suite produce a supporting subgraph that contains every node/edge cited in the answer.
- **SC-003**: When `--k` is set to N, the primary retrieval hit count does not exceed N (before traversal expansion and any documented hard safety caps on the final subgraph).
- **SC-004**: In offline evaluation (network disabled), query completes retrieval and subgraph export successfully whenever the input graph and local tooling are present; the answer also completes when the local language model is present.
- **SC-005**: 9 out of 10 evaluators reading the answer alongside the supporting subgraph agree the answer is consistent with subgraph contents and does not invent major entities or relationships absent from that subgraph.
- **SC-006**: On no-evidence queries, 100% of runs exit unsuccessfully with a clear message and do not present a fabricated confident answer.
- **SC-007**: Agents can load the query supporting-subgraph file with the same graph-loading expectations as other Grapheinstein portable graphs without manual repair.
- **SC-008**: Evaluators can identify, from the visualization summary alone, approximate subgraph scale (e.g., node/edge counts or equivalent) and at least one key entity involved in the answer for fixture cases.

## Assumptions

- The input is an existing portable graph produced (or merge-compatible with graphs produced) by prior Grapheinstein features; this feature does not re-index the project from source files.
- Graphs used with query include (or can expose) chunk-level text suitable for similarity search; if chunk embeddings are missing, they may be computed locally on demand or text fallback is used per planning defaults.
- Default `--k` is 20 primary retrieval hits; traversal expands beyond those hits under a documented limited policy so the final subgraph stays focused.
- Supporting subgraph is written to a documented output path (e.g., `--output subgraph.json`); the answer and visualization summary go to the human-readable stream by default, with optional structured packaging deferred to planning if needed for agents.
- “Visualization summary” means a textual structural overview suitable for CLI/agents, not an interactive GUI or image renderer, in this feature.
- Local LLM and embedding configuration reuse the same local-first patterns introduced for LLM enrichment and explain (model name, localhost endpoints, no cloud requirement).
- A documented relevance threshold decides “no evidence”; exact numeric defaults may be set during planning and should be overridable if exposed.
- Documented safety caps may truncate extremely large hybrid expansions; truncation must be visible when applied.
- Query complements—not replaces—`explain` (concept neighborhood) and `path` (route between two endpoints); those commands remain for their specialized workflows.
- Slash-command / MCP surfaces are out of scope for this feature; the CLI subcommand is the delivery vehicle (same library API may be reused later).
- Modalities already present in the input graph participate as available nodes/chunks; query does not add new file parsers.
