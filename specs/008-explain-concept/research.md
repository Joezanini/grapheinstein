# Research: Explain Concept Subgraph

**Feature**: `008-explain-concept`  
**Date**: 2026-07-17

## R1. CLI shape and exit semantics

**Decision**:

- Command: `grapheinstein explain CONCEPT --input PATH --output PATH [--hops 1|2] [--top-n N] [--match-threshold F] [--llm-model …] [--llm-base-url …] [--config …] [--no-summary]`.
- `CONCEPT` is a required positional; empty/whitespace → usage error, non-zero exit.
- `--input` / `-i` and `--output` / `-o` required.
- Exit `0` when a match is found and the subgraph is successfully written (summary may succeed or be skipped).
- Exit non-zero when: invalid/missing input, validation failure, no match above threshold, hop/option validation errors, or subgraph write failure.
- Summary text always on the human-readable stream (stderr via Rich/console); never written into the subgraph JSON as free-form prose replacing the artifact.

**Rationale**: Matches FR-001, FR-006–009 and constitution CLI-first (structured file + human stream). Treating LLM-unavailable as soft-skip after a successful match keeps agents able to consume subgraphs without a running model.

**Alternatives considered**:
- Fail hard when LLM missing — stronger summary guarantee, but conflicts with FR-009 and offline matching value.
- Write summary into `graph.summary` only — useful later; v1 prefers stderr so `--output` stays a pure portable graph for existing loaders.

## R2. Fuzzy matching (always on)

**Decision**:

1. Build a searchable text string per node from: `id`, `type`, and common metadata string fields (`name`, `text`, `file`, `language`, `path` if present), joined/normalized (lowercase, collapse whitespace, strip).
2. Score each node with a blend of:
   - Exact / casefold equality on `id` or `metadata.name` → score `1.0`
   - Substring / token containment (query tokens ⊆ node text or vice versa)
   - `difflib.SequenceMatcher` ratio on normalized query vs node text
3. Final fuzzy score ∈ [0.0, 1.0]; default match threshold **`0.55`** (config/CLI overridable).
4. Prefer concept nodes slightly when scores tie (stable tie-break: higher score, then `type == concept`, then shorter `id`).
5. Select up to **`top_n` (default 3)** candidates with score ≥ threshold; if none, no-match failure.

**Rationale**: Spec requires fuzzy matching without a new dependency; stdlib `difflib` is enough for typos/partials on developer graphs. Threshold and top-N are documented and overridable (Assumptions).

**Alternatives considered**:
- **rapidfuzz** — better quality; rejected as required dep for v1 (may revisit as optional).
- Exact ID / slug only — fails Story 2 acceptance scenarios.
- Rank every node type equally with no concept bias — acceptable but concept-first tie-break matches explain intent.

## R3. Vector / semantic matching (optional, local)

**Decision**:

- When Ollama is reachable **and** embeddings succeed for the query and candidate texts, compute cosine similarity via Ollama **`POST /api/embeddings`** (stdlib HTTP, same base URL as chat).
- Combine scores: `final = max(fuzzy_score, embedding_score)` (or a documented weighted max) so strong fuzzy hits are never demoted by weak embeddings.
- If Ollama is down, the model lacks embeddings, or embedding calls fail → **skip vector path** with a single clear note on the human stream; continue with fuzzy-only. Do **not** fail the command when fuzzy matches exist.
- No required `sentence-transformers` / FAISS / vector DB for v1. No cloud embedding APIs.
- Do not persist embedding vectors into `graph.json` in v1 (compute at query time on the selected candidate pool or full graph if small; for large graphs MAY embed only top fuzzy prefilter, e.g. top 200 by fuzzy, then re-rank — document in implementation notes).

**Rationale**: Spec FR-003 and Story 2 require vector matching when available and graceful degradation otherwise. Ollama embeddings reuse the existing local runner with zero new Python packages (constitution incremental simplicity).

**Alternatives considered**:
- **sentence-transformers** required — heavier install; better offline without Ollama, but violates “thin core” for v1; defer as optional extra later.
- Precompute embeddings at index time — better UX later; out of scope (would touch index pipeline / schema).
- Fail when embeddings unavailable — conflicts with FR-003 degradation rule.

## R4. Neighborhood extraction (1–2 hops)

**Decision**:

- Interpret hop distance on the **undirected** view of the digraph (follow in- and out-edges). Knowledge-graph “neighborhood” for explanation includes callers/callees and containers/containees.
- Default **`hops=2`**; allow only `1` or `2` (reject others).
- Primary seeds = selected match node ids. Subgraph = union of ego-neighborhoods of radius `hops` around each seed, plus all edges of the original graph whose both endpoints are in the node set (induced subgraph on undirected reachability within radius).
- Preserve every copied edge’s `type`, `provenance`, and optional enrichment attrs (`confidence`, `evidence`, …).
- Safety cap: default **`explain_node_cap = 500`** nodes in the output subgraph. If the uncapped neighborhood exceeds the cap, keep seeds, then grow by BFS layers until the cap, set `graph.explain_truncated: true`, and warn on the human stream.
- Isolated match (no neighbors) → subgraph with that single node is valid.

**Rationale**: Spec FR-004/011 and edge cases; undirected hops match user expectation for “related to.” Cap prevents pathological 2-hop explosions on dense graphs.

**Alternatives considered**:
- Directed-only out-neighbors — misses important reverse edges (`defines`, `implements` into a concept).
- Radius >2 — explicitly out of scope.
- Soft unlimited neighborhoods — risks huge artifacts and slow LLM prompts.

## R5. Local LLM summary

**Decision**:

- Reuse `llm_model` / `llm_base_url` and `check_ready` patterns from enrichment.
- Add a **plain-text** chat helper (e.g. `chat_text`) that calls Ollama `/api/chat` **without** JSON-schema `format`, returning assistant text. Keep existing structured `chat()` for enrichment unchanged.
- Prompt: system instruction to summarize the concept **only** from provided neighborhood facts (node ids/types/names + edge types); user payload = compact serialization of the subgraph (truncated if needed for context size).
- On model unavailable / timeout / empty response: write subgraph anyway; print clear skip/error for summary; exit `0` if subgraph write succeeded.
- `--no-summary` skips LLM entirely (still match + write).
- Injectable callables in tests (same pattern as `llm_chat` for enrichment).

**Rationale**: Current `chat()` always expects JSON enrichment schema; free-text summary needs a separate path. Soft-skip matches FR-009.

**Alternatives considered**:
- Force structured JSON summary object — nicer for agents later; v1 human narrative on stderr is enough.
- Require LLM for success — conflicts with FR-009.

## R6. Artifact I/O and schema

**Decision**:

- Load via existing gzip-aware `load_artifact`; write via `write_artifact_dict` (validate + atomic).
- Remain on **`schema_version` `6.0.0`**. No new node/edge types.
- Convert artifact ↔ NetworkX with `json_graph.node_link_graph` / `to_artifact_dict` (add a small helper if missing).
- Additive optional `graph` metadata on explain outputs (see data-model): `explained_concept`, `explain_match_ids`, `explain_hops`, `explain_truncated`, fresh `generated_at`; retain `project_root` from input when present.
- Do not invent new structural edges during explain.

**Rationale**: Agents reuse the same loaders (SC-007); additive metadata avoids a schema bump.

**Alternatives considered**:
- Schema 7.0.0 for explain metadata — unnecessary for optional fields.
- Separate `.summary.md` file — extra artifact; deferred.

## R7. Agent context script

**Decision**: This Spec Kit install has **no** `update-agent-context` / agent-context bash script under `.specify/scripts/`. Skip agent-context update for this plan run; design artifacts under `specs/008-explain-concept/` are the source of truth for downstream `/speckit-tasks`.

**Rationale**: Same as features 006/007; no script to invoke.

**Alternatives considered**: Hand-edit unrelated agent docs — out of scope for `/speckit-plan`.
