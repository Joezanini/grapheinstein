# Research: Hybrid Natural-Language Query

**Feature**: `010-hybrid-query`  
**Date**: 2026-07-17

## R1. CLI shape and exit semantics

**Decision**:

- Command: `grapheinstein query QUESTION --input PATH --output PATH [--k N] [--hops 1|2] [--match-threshold F] [--llm-model …] [--llm-base-url …] [--no-answer] [--config …]`.
- `QUESTION` is a required positional; empty/whitespace → usage error, non-zero exit.
- `--input` / `-i` and `--output` / `-o` required (supporting subgraph is a first-class artifact, same as explain).
- `--k` default **20**; integer ≥ 1; max **200** (reject outside range).
- Exit `0` when ≥1 primary hit passes threshold and the supporting subgraph is successfully written (answer may succeed or be skipped).
- Exit non-zero when: invalid/missing input, validation failure, no evidence above threshold, option validation errors, or subgraph write failure.
- On success: structured **query-answer JSON on stdout**; human-readable answer, visualization summary, and progress/errors on **stderr**; subgraph only at `--output`.

**Rationale**: Matches FR-001–003, FR-005, FR-009 and constitution CLI-first (structured stdout + file + human stream). Soft-skip for missing LLM after successful retrieval matches FR-011 and explain’s summary pattern.

**Alternatives considered**:

- Optional `--output` with subgraph only on request — conflicts with spec’s explicit `subgraph.json` deliverable as a primary output.
- Answer only on stderr with no stdout JSON — weaker for agents (path already established stdout JSON).
- Fail hard when LLM missing — conflicts with FR-011.

## R2. What counts as a “chunk” for retrieval

**Decision**:

Build a **chunk corpus** from input graph nodes as follows:

1. **Prefer native text chunks**: any node with non-empty `metadata.text` (today: `media_text`, `transcript_chunk`, and any future type that stores body text).
2. **Include searchable nodes without body text**: for other nodes, use the same composed search string as `match.node_search_text` (`id`, `type`, metadata `name`/`text`/`file`/`language`/`path`/`kind`) so typical code/docs/concept graphs remain queryable without media.
3. Each corpus entry is a **Chunk Candidate**: `{node_id, chunk_text, node_type, source}` where `source` is `metadata_text` or `composed`.
4. Deduplicate by `node_id` (one candidate per node). Empty corpus (zero nodes or zero usable text) → clear failure.

**Rationale**: Spec assumes chunk-level similarity, but schema `6.0.0` does not persist embeddings and most index graphs lack `metadata.text` on code/docs. Composed text keeps query useful on existing fixtures while still prioritizing real chunk bodies when present. No index-pipeline or schema bump required.

**Alternatives considered**:

- Only `media_text` / `transcript_chunk` — too narrow; most project graphs would no-evidence fail.
- Require persisted embeddings at index time — better recall later; out of scope (touches index + schema).
- Re-read source files at query time — breaks portable-graph-only assumption and ignore/local-path coupling.

## R3. Primary retrieval scoring (`--k`)

**Decision**:

- Score chunk candidates with the same blend as `core/match.py`: fuzzy always; optional local embeddings via Ollama `embed_texts` when available.
- `final_score = max(fuzzy_score, embedding_score or 0)`; default **`query_match_threshold = 0.40`** (slightly lower than explain’s 0.55 because open questions are longer/paraphrased; config/CLI overridable).
- Select up to **`--k`** candidates with `final_score ≥ threshold`, sorted by score desc (tie-break: prefer `metadata_text` source, then `concept` type, then shorter `node_id`).
- Embeddings: reuse explain’s soft-skip (note on stderr; continue fuzzy-only). For large corpora, embed only a fuzzy prefilter (e.g. top 200) then re-rank — same pattern as `score_nodes`.
- Zero hits above threshold → no-evidence failure; **do not** write a success subgraph.

**Rationale**: FR-003/004 and Story 2; reuse battle-tested match helpers; `--k` bounds primary hits before traversal (SC-003).

**Alternatives considered**:

- Exact keyword BM25 library — new dependency; defer.
- Fail when embeddings unavailable — conflicts with Story 2 degradation.
- Persist vectors in graph.json — schema/index scope creep.

## R4. Graph traversal expansion

**Decision**:

- After selecting primary hit node ids as **seeds**, expand with existing `undirected_neighborhood(graph, seeds, hops=…, node_cap=…)`.
- Default **`query_hops = 1`** (with `--k` up to 20, hop-2 often explodes); allow `1` or `2` via `--hops` / config.
- Default **`query_node_cap = 500`**; on truncation set `graph.query_truncated: true` and warn on stderr / in viz summary.
- Supporting subgraph = induced neighborhood (all input edges with both endpoints in the node set); preserve `type`, `provenance`, optional enrichment attrs.
- Do not invent new structural edges.

**Rationale**: Spec hybrid = chunk hits + traversal; undirected neighborhood matches explain’s “related context” semantics. Default hop-1 keeps evidence focused when many seeds are selected.

**Alternatives considered**:

- Default hops=2 like explain — risk of huge subgraphs with k=20 seeds.
- Directed-only expansion — misses reverse relations useful for answering.
- Soft unlimited expansion — violates safety edge cases.

## R5. Cited answer generation

**Decision**:

- Reuse `chat_text` + `check_ready` with `llm_model` / `llm_base_url`.
- Prompt: answer **only** from provided evidence (compact node/edge facts + chunk excerpts); require inline citations of the form `` `[node:<id>]` `` and optionally `` `[edge:<source>-><target>:<type>]` ``.
- After generation, **validate citations**: drop or rewrite any citation whose node/edge is not in the supporting subgraph; if the model returns no valid citations, append a deterministic “Sources:” list of top primary hit ids (and a few key edges) so FR-007 still holds.
- `--no-answer` skips LLM entirely (still retrieve + write subgraph + viz).
- Model unavailable / timeout / empty → write subgraph + viz; report skip/failure on stderr; exit `0` if write succeeded.
- Injectable callables in tests (same pattern as explain/path).

**Rationale**: FR-006/007/011/013; post-filter prevents hallucinated ids from becoming “graph citations” (SC-002).

**Alternatives considered**:

- Trust model citations without validation — fails SC-002/FR-013.
- Structured JSON-only answer schema via `chat()` — nicer later; v1 uses free text + validated citation parse for speed of delivery.
- Require LLM for success — conflicts with FR-011.

## R6. Visualization summary

**Decision**:

- Deterministic **textual** overview on stderr (and mirrored fields in stdout JSON): node count, edge count, counts by node `type` (top few), primary hit ids (up to a small sample), whether truncated, output path.
- Not an image/GUI/DOT write in this feature (users can `visualize` the written subgraph separately).
- Distinct from the answer prose (FR-008).

**Rationale**: Spec Assumptions explicitly define viz summary as CLI/agent text overview; reuses the spirit of `visualize.print_summary` without requiring a second file.

**Alternatives considered**:

- Auto-write DOT/PNG — extra deps/UX; out of scope.
- Only include viz inside stdout JSON — still need human stream for interactive use.

## R7. Artifact I/O and schema

**Decision**:

- Load via `load_artifact`; write via `write_artifact_dict` (validate + atomic).
- Remain on **`schema_version` `6.0.0`**. No new node/edge types.
- Additive optional `graph` metadata on query outputs: `query_question`, `query_hit_ids`, `query_k`, `query_hops`, `query_truncated`, `query_hit_scores` (optional), fresh `generated_at`; retain `project_root` when present.
- Structured answer envelope versioned separately as query-answer JSON (see contracts); not embedded as free-form prose inside the subgraph file.

**Rationale**: Agents reuse the same graph loaders (SC-007); additive metadata avoids a schema bump.

**Alternatives considered**:

- Schema 7.0.0 for query fields — unnecessary for optional keys.
- Stuff answer text into `graph.query_answer` only — splits agent UX; stdout JSON is clearer (path precedent).

## R8. Agent context script

**Decision**: This Spec Kit install has **no** `update-agent-context` / agent-context bash script under `.specify/scripts/`. Skip agent-context update for this plan run; design artifacts under `specs/010-hybrid-query/` are the source of truth for downstream `/speckit-tasks`.

**Rationale**: Same as features 008/009; no script to invoke.

**Alternatives considered**: Hand-edit unrelated agent docs — out of scope for `/speckit-plan`.
