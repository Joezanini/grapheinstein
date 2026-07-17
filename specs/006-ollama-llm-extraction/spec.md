# Feature Specification: Local LLM Entity & Relation Extraction

**Feature Branch**: `006-ollama-llm-extraction`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Integrate local LLM (Ollama) for grapheinstein. For each chunk/file: Extract entities/concepts (functions already from AST + domain terms); Infer relations (e.g. \"this function implements X from doc\", \"depends on library Y\"). Every edge must have \"source\": \"extracted\" | \"inferred\", \"confidence\": float, \"evidence\": text snippet. Update graph building pipeline. Configurable model (default qwen3.5-2b-mlx:fp16-8gbGPU or whatever is local)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enrich Index with Local LLM Concepts and Relations (Priority: P1)

A developer indexes a local project with a local language model available (Ollama or equivalent local runner). During graph building, the tool processes each eligible file/chunk offline: it keeps AST-derived functions and symbols already in the graph, extracts additional domain concepts/terms from the text, and infers typed relations such as “function implements concept from docs” or “file depends on library Y.” The resulting portable graph includes these nodes and edges so agents can reason beyond structural containment and references.

**Why this priority**: Local LLM concept/relation extraction is the constitution’s next vertical after parsers; without it, the graph is mostly structural and weak for install/ops Q&A.

**Independent Test**: Index a small fixture with code plus a short doc that names a concept the code implements; with LLM enrichment enabled and a local model configured, confirm new concept nodes and inferred relations appear with confidence and evidence; without enrichment (or without a usable model), prior structural graph behavior remains intact.

**Acceptance Scenarios**:

1. **Given** a project with code that already yields AST function nodes and a doc mentioning a domain concept those functions implement, **When** the user runs index with local LLM enrichment enabled and a usable local model, **Then** the graph includes concept/entity nodes for domain terms and at least one inferred relation linking code entities to those concepts.
2. **Given** the same project, **When** the user runs index with LLM enrichment disabled, **Then** no new LLM-derived concept nodes or LLM-inferred relations are added; existing AST and parser edges remain.
3. **Given** enrichment enabled and a successful offline model response for a chunk, **When** indexing completes, **Then** every edge written by this feature carries provenance (`extracted` or `inferred`), a numeric confidence, and a non-empty evidence text snippet grounded in the chunk.
4. **Given** ignore rules that exclude a file, **When** indexing with enrichment enabled, **Then** that file is not sent to the local model and does not receive LLM-derived nodes/edges.

---

### User Story 2 - Provenance, Confidence, and Evidence on Every New Edge (Priority: P1)

An agent or developer consuming `graph.json` must trust and filter edges. Every edge produced or updated by this enrichment step MUST expose: provenance labeled exactly `extracted` or `inferred` (see Assumptions for field naming), a floating-point confidence score, and an evidence snippet (short quote or paraphrase anchor from the source chunk). AST/parser structure remains `extracted`; LLM-suggested links are `inferred`.

**Why this priority**: Constitution Principle III requires provenance; confidence and evidence make inferred edges usable for agents and debugging.

**Independent Test**: After an enriched index of a fixture, inspect all edges added by this feature and verify required fields; confirm AST containment/call-style edges stay `extracted` and LLM concept links are `inferred`.

**Acceptance Scenarios**:

1. **Given** an enriched graph from a fixture, **When** a consumer inspects edges created by LLM relation inference, **Then** each such edge has provenance `inferred`, a confidence between 0.0 and 1.0 inclusive, and a non-empty evidence string.
2. **Given** domain terms that appear verbatim in a chunk and are recorded as extracted entities related to that chunk/file, **When** those extraction edges are written, **Then** they use provenance `extracted` with confidence and evidence present.
3. **Given** an enriched graph, **When** a consumer filters to `extracted` only, **Then** LLM-inferred relations are excluded while AST/parser and extracted-entity edges remain available.
4. **Given** a low-confidence model suggestion below a documented minimum threshold, **When** enrichment merges results, **Then** that relation is omitted rather than written as a high-trust edge.

---

### User Story 3 - Configure Local Model Name and Fall Back Gracefully (Priority: P1)

A developer configures which local model to use (default preference: a small local model such as `qwen3.5-2b-mlx:fp16-8gbGPU`, or another model already available on the machine). Configuration is local (CLI flag and/or config file). If the preferred model is missing, the tool uses a documented fallback (configured alternate, or clearly reports that enrichment cannot run) without requiring cloud APIs. Index of non-LLM graph structure still succeeds when enrichment is skipped due to unavailable model.

**Why this priority**: Local-first operation depends on configurable models and safe failure when Ollama/models are absent.

**Independent Test**: Run index with an explicit model name that exists locally and confirm enrichment uses it; run with a missing model and confirm clear messaging plus a valid structural graph (no crash, no cloud call).

**Acceptance Scenarios**:

1. **Given** a local model matching the configured default or an explicit override is available, **When** the user indexes with enrichment enabled, **Then** enrichment runs against that model entirely offline.
2. **Given** the user sets a different model name via documented config or CLI option, **When** indexing with enrichment enabled, **Then** that model is used instead of the default.
3. **Given** the configured model is not available locally, **When** indexing with enrichment enabled, **Then** the tool reports a clear human-readable error or skip warning for enrichment and still produces a valid graph from prior pipeline stages (file/dir/code/docs/media as already implemented).
4. **Given** no network access, **When** enrichment runs with a local model present, **Then** indexing completes without requiring remote LLM APIs.

---

### User Story 4 - Pipeline Integration Without Breaking Existing Index (Priority: P2)

LLM enrichment is a stage in the existing graph building pipeline: after structural parsing (and other modality parsers), per chunk/file enrichment merges new concept nodes and edges into the same portable graph. Re-indexing replaces or refreshes enrichment for that run consistently with existing index semantics. Progress for long enrichment runs remains visible on the human-readable stream.

**Why this priority**: Keeps the CLI usable as increments stack; agents already depending on `graph.json` must not see broken schemas or lost structural edges.

**Independent Test**: Index a multi-file fixture with enrichment on; confirm structural edges from earlier features remain and LLM nodes/edges appear alongside; confirm progress messages during multi-chunk enrichment.

**Acceptance Scenarios**:

1. **Given** a project already indexable by prior features, **When** enrichment is enabled, **Then** the output graph still includes prior file/dir/code/docs/(media) structure and adds LLM-derived concepts/relations without dropping required prior edge types.
2. **Given** many chunks to enrich, **When** indexing runs, **Then** the tool emits progress suitable for a long run (at least periodic indication that enrichment is underway) on the human-readable stream.
3. **Given** one chunk fails model parsing or returns unusable output, **When** enrichment continues, **Then** that chunk is reported/skipped and other chunks still enrich; the whole index does not abort solely for one bad chunk.
4. **Given** a repeated index of the same project with enrichment enabled, **When** the run completes, **Then** the written graph reflects this run’s enrichment (consistent with existing replace-output semantics).

---

### Edge Cases

- Local model runner installed but no models pulled: clear skip/error for enrichment; structural graph still written when possible.
- Model returns empty, malformed, or hallucinated entities with no evidence in the chunk: discard those suggestions; do not invent evidence.
- Chunk larger than practical model context: process via existing chunking / truncated window with documented behavior; do not silently drop the whole file without a warning when truncation occurs.
- Duplicate concept names across files: reuse or merge concept identity in a stable, documented way rather than creating unbounded near-duplicate nodes for the same term in one project (exact merge rules are planning-level; outcome MUST be deterministic for a fixture).
- AST functions already present: do not recreate duplicate function nodes; LLM may add concept nodes and relations involving existing function nodes.
- Confidence exactly at threshold: apply documented inclusive/exclusive rule consistently (default: require confidence ≥ threshold to keep).
- Enrichment disabled via flag/config: zero LLM calls; pipeline identical to pre-feature structural path for enrichment stage.
- Air-gapped machine with model present: full enrichment works offline.

## Requirements *(mandatory)*

<!--
  Grapheinstein constitution constraints in scope for this feature:
  - Local-first / offline-capable defaults; no required cloud APIs
  - CLI subcommands; portable graph.json for agent reuse
  - Typed edges with provenance: extracted | inferred
  - Prefer rule-based AST for code structure; local LLM for concept/relation inference
  - Modalities: operates on chunks/files already produced by code/docs/PDF/media parsers
-->

### Functional Requirements

- **FR-001**: System MUST integrate a local LLM runner (Ollama or equivalent local HTTP/local API) into the graph building pipeline to enrich indexed chunks/files offline.
- **FR-002**: For each eligible chunk/file, the system MUST extract domain entities/concepts in addition to retaining AST-derived functions and symbols already produced by parsers.
- **FR-003**: For each eligible chunk/file, the system MUST infer typed relations among entities (including examples such as implements-concept and depends-on-library) when supported by the chunk content.
- **FR-004**: Every edge produced by this feature MUST include: provenance of exactly `extracted` or `inferred`, a floating-point `confidence` in `[0.0, 1.0]`, and a non-empty `evidence` text snippet tied to the source chunk.
- **FR-005**: AST/parser-derived structural edges remain provenance `extracted`; LLM-suggested relations MUST use provenance `inferred`.
- **FR-006**: Users MUST be able to configure the local model name; the documented default MUST prefer `qwen3.5-2b-mlx:fp16-8gbGPU` when available, otherwise a user-configured model or a clear unavailable-model outcome (no silent cloud fallback).
- **FR-007**: Users MUST be able to enable or disable LLM enrichment via documented CLI and/or local config; when disabled, the index MUST NOT call the local LLM.
- **FR-008**: System MUST NOT require cloud LLM APIs for this feature; remote models MUST NOT be the default path.
- **FR-009**: System MUST continue to respect `.gitignore` and configured ignore rules so ignored paths are not enriched.
- **FR-010**: System MUST NOT abort the entire index solely because one chunk’s enrichment fails; failures MUST be reported and successful chunks MUST still contribute.
- **FR-011**: Output MUST remain a portable project graph suitable for agent reuse, including prior modality nodes/edges plus new concept nodes and enrichment edges.
- **FR-012**: System MUST omit inferred relations whose confidence is below a documented minimum threshold (default 0.5 unless config overrides).
- **FR-013**: Evidence MUST be grounded in the processed chunk (quote or clearly derived snippet); the system MUST NOT fabricate evidence for unsupported suggestions.
- **FR-014**: Enrichment MUST update the graph building pipeline as an explicit stage after structural/modality parsing merges, not as a separate unrelated export.

### Key Entities

- **Concept / Domain Entity Node**: A non-file entity representing a domain term, library, or documented concept; attributes include stable id, type/kind, display name, and optional defining chunk/path references.
- **Existing Code Entity Node**: AST-derived function/class/symbol nodes already in the graph; enrichment links to them rather than duplicating them.
- **Chunk / File Context**: The unit of LLM input (file or chunk from prior parsers); enrichment is scoped per unit.
- **Enrichment Edge**: Typed relationship (e.g., implements, depends_on, mentions, or documented equivalents) with required `provenance`, `confidence`, and `evidence`.
- **Model Configuration**: Local settings naming the model, enable/disable enrichment, optional confidence threshold, and runner endpoint/path as applicable.
- **Enrichment Failure Record**: Non-fatal record that a chunk could not be enriched, without failing the whole index.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a fixture with code functions and a doc naming a concept those functions implement, one offline enriched index produces at least one concept node and at least one `inferred` relation with confidence and evidence linking code to that concept.
- **SC-002**: 100% of edges written by this enrichment stage in test fixtures include provenance (`extracted` or `inferred`), confidence in `[0.0, 1.0]`, and non-empty evidence.
- **SC-003**: With enrichment disabled, or with no usable local model, indexing still writes a valid structural graph from existing parsers and makes zero successful remote/cloud LLM calls.
- **SC-004**: Changing the configured model name causes enrichment to target that model when it is available; a missing model yields a clear skip/error for enrichment within one index run without crashing the CLI process.
- **SC-005**: On a multi-chunk fixture where one chunk returns unusable model output, at least the remaining successful chunks are enriched and a valid graph is written.
- **SC-006**: A developer can enable enrichment and select a model using only documented local config/CLI options and obtain an updated portable graph without changing ignore-rule or output-path behavior of prior index features.

## Assumptions

- Field naming: the existing portable graph already uses edge endpoints `source`/`target` and provenance via `provenance` (`extracted` | `inferred`). The user’s requested edge `"source": "extracted"|"inferred"` is interpreted as the provenance/origin label, implemented as the existing `provenance` field (constitution-aligned), plus new `confidence` and `evidence` attributes on enrichment edges. Renaming `provenance` to `source` is out of scope because it would collide with node-link `source`.
- Default model name string: `qwen3.5-2b-mlx:fp16-8gbGPU`; if absent, enrichment does not invent a cloud substitute—user must configure an installed local model or accept skipped enrichment.
- Local runner: Ollama is the primary integration target; other local OpenAI-compatible endpoints MAY be accepted if they satisfy the same offline contract (planning decision).
- Enrichment is opt-in for this increment (flag and/or config) so default index stays fast on machines without models; exact flag name is a planning/CLI contract detail.
- Confidence threshold default: 0.5; values below threshold are dropped.
- AST function/class extraction remains owned by Tree-sitter parsers; the LLM MUST NOT be the sole source of function inventory.
- Relation type vocabulary (implements, depends_on, etc.) will be documented in the graph contract during planning; provenance/confidence/evidence rules above are fixed.
- Schema version MAY bump if new required edge attributes or node types require it; older graphs without enrichment fields remain readable for prior edge kinds.
- Query commands (`explain`, `path`, `ask`) are unchanged except that enriched graphs remain consumable by existing visualize/status flows.
- Chunking for LLM context reuses or extends existing chunk boundaries from docs/media/code where present; exact prompt design is a planning concern, not a stakeholder requirement.
- No mandatory GPU: CPU-only local models are acceptable when configured; performance targets are “completes offline on a small fixture,” not hardware-specific latency SLAs.
