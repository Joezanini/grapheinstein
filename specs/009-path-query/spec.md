# Feature Specification: Path Between Concepts

**Feature Branch**: `009-path-query`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Add: grapheinstein path <start> <end> --input graph.json. Use NetworkX shortest_path (multi-weighted by relation type/confidence). Output path with edge labels (extracted/inferred) and explanation."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find How Two Concepts Connect (Priority: P1)

A developer (or agent) has a portable project graph and wants to know how one concept relates to another. They run `grapheinstein path` with a start concept, an end concept, and an input graph. The tool resolves both endpoints, finds a preferred connecting path through the graph (favoring stronger, more trustworthy relationships when weights are available), and reports the ordered path with each edge’s relationship type and provenance (`extracted` or `inferred`), plus a short explanation of how the start connects to the end.

**Why this priority**: Path is a constitution-listed core query command; without it, users can inspect neighborhoods but cannot answer “how does A relate to B?” across the project graph.

**Independent Test**: Given a fixture graph with a known chain from start to end, run path for those endpoints; confirm the reported path includes the expected nodes in order, each connecting edge shows type and provenance, and an explanation is produced—without requiring cloud APIs.

**Acceptance Scenarios**:

1. **Given** a valid portable input graph containing a clear route from start to end, **When** the user runs path with those endpoints and `--input`, **Then** the tool reports an ordered path from the resolved start node to the resolved end node.
2. **Given** a successful path, **When** the user inspects the result, **Then** each step lists the relationship type and provenance label (`extracted` or `inferred`) for the connecting edge.
3. **Given** a successful path, **When** the command completes, **Then** the user receives a human-readable explanation of how the start connects to the end, grounded in the reported path (not inventing edges absent from the result).
4. **Given** no network access and a usable local graph file, **When** the user runs path, **Then** resolution, path finding, and explanation complete without requiring remote AI services.

---

### User Story 2 - Prefer Stronger, More Trustworthy Routes (Priority: P1)

When multiple routes exist between the same endpoints, the tool selects a preferred path using edge weights derived from relationship type and confidence (when present), together with provenance so more reliable connections are favored over weak or speculative ones. Users get the most useful “how they connect” answer, not an arbitrary walk.

**Why this priority**: Multi-weight preference is the differentiating value of this command; an unweighted hop-count-only path can prefer long chains of weak inferred edges over a short, high-confidence extracted link.

**Independent Test**: On a fixture graph with two routes—one short but low-confidence/inferred-heavy, one preferred by the documented weighting policy—path returns the preferred route; edge labels and explanation match that chosen route.

**Acceptance Scenarios**:

1. **Given** two distinct routes between the same endpoints with different weight totals under the documented policy, **When** the user runs path, **Then** the tool returns the preferred (lowest-cost) route according to that policy.
2. **Given** edges that carry confidence scores and provenance labels, **When** path computes preference, **Then** higher-confidence and `extracted` edges are favored over lower-confidence and purely `inferred` edges when other factors are equal (per documented weighting rules).
3. **Given** edges missing optional confidence values, **When** path runs, **Then** the tool still finds a path using documented default weights for missing confidence and does not fail solely because confidence is absent.
4. **Given** a successful weighted path, **When** the user reads the explanation, **Then** the explanation describes the chosen route’s relationships, not an alternate discarded route.

---

### User Story 3 - Resolve Endpoints Flexibly and Fail Clearly (Priority: P2)

Users rarely know exact node IDs. Path resolves `<start>` and `<end>` using the same style of fuzzy/text matching (and local semantic matching when available) used by other concept-query commands. When either endpoint cannot be resolved, or no connecting path exists, the tool fails clearly with a useful message and does not invent a path.

**Why this priority**: Matching and failure clarity make the command reliable for agents and humans; secondary to the happy-path weighted path loop.

**Independent Test**: Run path with approximate start/end names that match fixture nodes and confirm success; run with an unresolvable endpoint and with two resolvable but disconnected nodes and confirm unsuccessful exits with clear messages and no fabricated path.

**Acceptance Scenarios**:

1. **Given** a graph with nodes whose labels approximate (but do not exactly equal) the start and end phrases, **When** the user runs path with those phrases, **Then** the tool resolves both endpoints and returns a path when one exists.
2. **Given** a start or end phrase that matches no node above the documented relevance threshold, **When** the user runs path, **Then** the tool reports which endpoint failed, exits unsuccessfully, and does not present a success-looking path.
3. **Given** both endpoints resolve but no route connects them in the directed sense used by the graph, **When** the user runs path, **Then** the tool reports that no path exists and exits unsuccessfully.
4. **Given** a missing, unreadable, or invalid input graph, **When** the user runs path, **Then** the tool reports a clear error and does not produce a path or explanation as if the run succeeded.

---

### Edge Cases

- Empty or whitespace-only start or end argument → rejected with a clear usage/validation error.
- Start and end resolve to the same node → reported as a trivial path (single node, no edges) with a brief explanation that the endpoints are the same entity.
- Input graph with zero nodes → no resolution; unsuccessful exit with clear message.
- Multiple strong matches for an endpoint → the best match is used; if scores are tied within a documented tolerance, the tool picks deterministically and notes ambiguity when it affects the result.
- Very long paths → tool may apply a documented maximum path length; if exceeded with no acceptable shorter route, fail clearly rather than dumping an unbounded walk.
- Parallel edges between the same node pair → the preferred edge under the weighting policy is used for that step; its type and provenance appear in the output.
- Compressed input graphs (if supported by existing loaders) → path accepts the same graph inputs the rest of the CLI can load.
- Machine-consumable path output requested (stdout JSON or `--output` file when provided) → structured path data remains separate from progress/errors on the human-readable stream.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CLI MUST provide a `path` subcommand of the form `grapheinstein path <start> <end> --input <graph>` (equivalent option names allowed if documented; start and end positionals are required).
- **FR-002**: Path MUST load a portable project graph from `--input` in the same documented graph format family used by index/merge/explain.
- **FR-003**: Path MUST resolve `<start>` and `<end>` to graph nodes using fuzzy/text matching, and MUST use local vector/semantic similarity when embeddings are available; resolution MUST NOT require cloud services.
- **FR-004**: Path MUST compute a preferred connecting route between the resolved endpoints using a documented multi-factor edge-weighting policy that considers relationship type and confidence (when present), and that favors more trustworthy provenance (`extracted` over `inferred` when other factors are equal).
- **FR-005**: Path MUST report the ordered sequence of nodes from start to end and, for each connecting edge, the relationship type and provenance label (`extracted` | `inferred`).
- **FR-006**: Path MUST produce a human-readable explanation of how the start connects to the end, grounded in the reported path edges and labels.
- **FR-007**: Path MUST support machine-consumable structured output for the path answer (JSON on stdout and/or a documented `--output` file path), while progress and errors remain on the human-readable stream.
- **FR-008**: When either endpoint cannot be resolved above the relevance threshold, Path MUST fail clearly (non-success exit), identify which endpoint failed when possible, and MUST NOT invent a path.
- **FR-009**: When both endpoints resolve but no connecting path exists, Path MUST fail clearly and MUST NOT invent edges or nodes.
- **FR-010**: Path MUST preserve and surface existing provenance and relationship types from the input graph; it MUST NOT silently relabel `extracted` edges as `inferred` or the reverse.
- **FR-011**: When confidence is missing on an edge, Path MUST apply a documented default weight contribution and still attempt path finding.
- **FR-012**: Path finding and explanation MUST be offline-capable; they MUST NOT require cloud APIs. If an optional local language model is used to polish the explanation, a deterministic path-based explanation MUST still be available when no local model is present.
- **FR-013**: Local embedding (and optional local model) settings MUST be configurable via the project’s existing local configuration mechanisms (and/or CLI overrides), consistent with other query features.

### Key Entities

- **Path Query**: The user-supplied start and end phrases plus the input graph reference used to request a connection.
- **Endpoint Match**: A graph node scored against a start or end phrase (identity/label/text and optional embedding similarity), with a relevance score used for ranking and thresholding.
- **Weighted Path**: An ordered sequence of nodes and connecting edges from start to end, selected under the documented multi-factor weighting policy (relationship type, confidence, provenance).
- **Path Step**: One edge in the weighted path, including source, target, relationship type, provenance (`extracted` | `inferred`), and confidence when available.
- **Path Explanation**: A human-readable description of how start connects to end, grounded in the weighted path’s steps and labels.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a fixture graph with a known start–end connection, users obtain a correct path (ordered nodes plus edge types and provenance) in under 15 seconds on a typical developer machine for graphs up to a few thousand nodes/edges.
- **SC-002**: At least 90% of path runs on a prepared fixture suite with intentionally approximate endpoint phrases (typos/partials) resolve both endpoints to the intended nodes when those nodes are clearly the best candidates.
- **SC-003**: On fixtures with two competing routes, 100% of runs return the route preferred by the documented weighting policy (not the discarded alternate).
- **SC-004**: In offline evaluation (network disabled), path completes endpoint resolution, path finding, and explanation whenever the input graph and local tooling are present.
- **SC-005**: 9 out of 10 evaluators reading the explanation alongside the path steps agree the explanation is consistent with those steps and does not invent major relationships absent from the path.
- **SC-006**: On unresolvable endpoints or disconnected pairs, 100% of runs exit unsuccessfully with a clear message and do not present a fabricated success path.
- **SC-007**: Agents can consume the structured path answer without manual repair, using the documented path output shape.

## Assumptions

- The input is an existing portable graph produced (or merge-compatible with graphs produced) by prior Grapheinstein features; this feature does not re-index the project.
- Endpoint resolution reuses the same matching approach and relevance-threshold patterns as the explain-concept feature (fuzzy/text always; local vectors when available).
- The graph is treated as directed for path finding unless the documented graph schema states otherwise; reverse edges are not invented.
- Weighting policy defaults (exact numeric costs per relation type, confidence scaling, provenance multipliers) are established during planning; the user-facing contract is that extracted/high-confidence edges are preferred over inferred/low-confidence ones.
- Missing confidence uses a neutral default (neither best nor worst) so path finding remains usable on graphs that omit confidence.
- Explanation is primarily a path-grounded narrative of the selected steps; optional local-LLM polishing may be added but MUST degrade to a deterministic explanation when no local model is available.
- Structured path output defaults to machine-consumable JSON on stdout when appropriate for agents; a documented `--output` option may write that artifact to a file. Human-readable explanation appears on the human-readable stream (and may also be included as a field in the structured answer).
- Slash-command / MCP surfaces are out of scope for this feature; the CLI subcommand is the delivery vehicle (same library API may be reused later).
- Exact shortest-path library choice and algorithm parameters are implementation details for planning; this specification requires weighted preferred-path behavior and provenance-labeled output, not a particular library name in the user-facing contract.
- Modalities already present in the input graph are path-queryable insofar as they appear as nodes/edges; path does not add new parsers.
