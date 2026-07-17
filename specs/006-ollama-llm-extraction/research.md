# Research: Local LLM Entity & Relation Extraction

**Feature**: `006-ollama-llm-extraction`  
**Date**: 2026-07-17

## R1. Local LLM runner integration

**Decision**: Integrate **Ollama** via its local HTTP API (`POST /api/chat`, default base URL `http://localhost:11434`). Use `stream: false` and Ollama’s structured **`format`** (JSON Schema object) so responses parse reliably into entities/relations. Use Python **stdlib** (`urllib.request`) for HTTP—no required new Python package for the Ollama client. Verify model availability with `GET /api/tags` (or equivalent list) before enrichment when `--enrich-llm` is set.

**Rationale**: Spec and constitution name Ollama as the local-first runner. Official `/api/chat` supports structured outputs via `format`, which reduces malformed JSON from small models. Stdlib HTTP keeps the core install light (unlike media’s heavy optional wheels). Ollama itself remains an external local service the user installs.

**Alternatives considered**:
- **ollama Python package** — thin convenience wrapper; adds a dep for little gain over stdlib + documented JSON shapes.
- **LM Studio / OpenAI-compatible only** — acceptable later behind the same client interface; Ollama is the v1 primary target.
- **Cloud OpenAI/Anthropic** — violates local-first; must not be default or required.
- **sentence-transformers only (no generative LLM)** — insufficient for “implements X from doc” style relation inference.

## R2. Optional dependency / missing-model behavior

**Decision**:

- No mandatory `[llm]` Python extra for the Ollama HTTP client (stdlib). Optionally document `[llm]` as empty/reserved or omit until a second backend needs packages.
- When `--enrich-llm` is set and Ollama is unreachable **or** the configured model is not listed locally → **warn and skip enrichment** (do not abort the whole index); still write a valid structural graph from prior stages; emit a clear stderr message naming the model/base URL. Persist `graph.enrich_llm: true` only when enrichment was requested; also persist `graph.llm_model` when enrichment ran or was attempted.
- When `--enrich-llm` is set and Ollama is up but a **single chunk** fails (timeout, bad JSON, empty) → **warn-and-continue** that chunk; enrich others.
- Without `--enrich-llm`, make **zero** Ollama HTTP calls (lazy client construction).

**Rationale**: Spec FR-010 and Story 3 require structural success when the model is missing, unlike media’s fail-closed-on-missing-Python-extras (media extras are install-time; Ollama is runtime service/model). Skipping enrichment with a loud warning matches “no silent cloud fallback” while keeping the CLI usable.

**Alternatives considered**:
- Fail-closed (non-zero exit) when model missing — stronger signal, but conflicts with “still produce valid structural graph” acceptance scenarios.
- Soft-skip without warning — rejected; agents need an explicit signal.

## R3. CLI flag, config keys, default model

**Decision**:

| Surface | Name | Default |
|---------|------|---------|
| CLI flag | `--enrich-llm` | off |
| Config / CLI | `--llm-model` / `llm_model` | `qwen3.5-2b-mlx:fp16-8gbGPU` |
| Config / CLI | `--llm-base-url` / `llm_base_url` | `http://localhost:11434` |
| Config | `llm_confidence_threshold` | `0.5` |

- Precedence: CLI flags > `--config` file > `~/.grapheinstein/config.yaml` > built-ins.
- If the default model string is not installed, do **not** auto-pick another model silently; require `--llm-model` / config override, or skip enrichment with a message listing that the configured model was not found (MAY hint that `ollama list` can show available tags).

**Rationale**: Spec default model name preserved; “or whatever is local” is user configuration, not silent auto-selection (avoids non-deterministic graphs across machines).

**Alternatives considered**:
- Auto-select first local model — convenient but non-reproducible; rejected for v1.
- Always-on enrichment — rejected; slow without models and breaks default index speed.

## R4. Schema version bump

**Decision**: Bump `schema_version` to **`6.0.0`**. Add node type `concept`; add edge types `implements` and `depends_on`. Require `confidence` and `evidence` on edges produced by enrichment (`implements`, `depends_on`, and enrichment-produced `mentions` to concepts). Loaders **reject** `5.0.0` and older with a clear re-index message.

**Rationale**: Constitution treats schema changes as breaking. New node/edge kinds and mandatory enrichment attributes need a major bump so agents do not silently misread artifacts.

**Alternatives considered**:
- Stay on `5.0.0` and widen allow-lists — rejected (no capability signal).
- Reuse only `related_to` for all LLM links — rejected; overloads media heuristics and weakens typed agent queries.

## R5. Concept identity and merge

**Decision**:

- Node `type`: **`concept`**
- Stable `id`: `concept::{slug}` where `slug` is a deterministic lowercase slug of the normalized display name (alphanumeric + hyphens; collapse whitespace; strip punctuation).
- Metadata: `name` (original display string), optional `kind` (`domain_term` | `library` | `other`), optional `aliases` (list).
- First writer wins for `name` casing; subsequent chunks with the same slug **reuse** the node (no duplicates).
- Do **not** create new `function`/`class`/`method` nodes from the LLM; resolve mentions against existing AST nodes by exact symbol name within the same file when possible, else skip that endpoint.

**Rationale**: Deterministic ids keep re-index diffs stable and satisfy the duplicate-concept edge case. AST remains the sole source of code entity inventory (constitution + FR).

**Alternatives considered**:
- Per-file concept ids (`file::concept::…`) — fragments the graph; harder for cross-file “implements X”.
- Embedding-based concept merge — deferred; slug equality is enough for v1 fixtures.

## R6. Edge types, provenance, confidence, evidence

**Decision**:

| Edge `type` | Typical endpoints | Provenance | Notes |
|-------------|-------------------|------------|-------|
| `mentions` | file/chunk/code → `concept` when the term appears in text | `extracted` | Enrichment-produced `mentions` **must** include `confidence` + `evidence` |
| `implements` | code entity (`function`/`class`/`method`) → `concept` | `inferred` | Requires confidence ≥ threshold + evidence |
| `depends_on` | file or code entity → `concept` (library/dependency) | `inferred` | Same |

- `confidence`: float in `[0.0, 1.0]`; keep if `confidence >= llm_confidence_threshold` (default **0.5**, inclusive).
- `evidence`: non-empty string; MUST be a substring of the chunk text **or** a truncated contiguous excerpt (≤ 240 chars) that appears in the chunk after whitespace normalization. If the model’s evidence is not grounded, **drop** the edge (do not invent evidence).
- Prior edge types (`contains`, `references`, `defines`, `imports`, `calls`, `section_of`, media `related_to`, doc `mentions` without enrichment attrs) **MAY omit** `confidence`/`evidence`.
- Persist optional `graph.llm_model` and `graph.enrich_llm` on the artifact.

**Rationale**: Matches spec field mapping (`provenance` not colliding with node-link `source`). Reusing `mentions` for extracted term attachment avoids a third near-synonym; typed `implements` / `depends_on` cover the inferred examples in the user request.

**Alternatives considered**:
- New edge type `extracts` for term attachment — clearer but more vocabulary churn; `mentions` already means “refers to”.
- Require confidence/evidence on **all** graph edges — breaks prior writers; rejected.

## R7. Pipeline stage and chunk units

**Decision**: Add enrichment as the **last merge stage** in `build_inventory_graph`, after inventory, references, code, optional docs/PDF, and optional media:

1. Collect enrichment units: prefer existing text-bearing nodes’ source files — for each non-ignored `file` with extractable text (code source, docs, PDF-derived text if already in memory/on disk, OCR/transcript text when present), build a **chunk** (file text truncated to a max char budget, default **12_000** chars; warn once per truncated file).
2. For each unit, call Ollama with a fixed system prompt + schema `format` requesting `{entities, relations}`.
3. Merge concepts + edges; progress log every N chunks (or each file) on stderr via existing logging.
4. Write schema `6.0.0`.

Injectable `llm_chat=` (or similar) for tests so CI does not need a live Ollama daemon.

**Rationale**: Mirrors media’s injectable engine pattern. Post-parser staging preserves AST-first structure. Truncation + warn matches the large-chunk edge case.

**Alternatives considered**:
- Enrich only code files — too narrow for “implements X from doc”.
- Parallel fan-out to Ollama — defer; sequential is simpler and friendlier to small local GPUs.

## R8. Prompt / response contract (implementation-facing)

**Decision**: Request JSON shaped approximately:

```json
{
  "entities": [
    {"name": "string", "kind": "domain_term|library|other", "evidence": "string", "confidence": 0.0}
  ],
  "relations": [
    {
      "type": "implements|depends_on|mentions",
      "subject": "string",
      "object": "string",
      "evidence": "string",
      "confidence": 0.0
    }
  ]
}
```

Map `subject`/`object` strings to graph node ids (existing code symbols in-file, concept slugs, or file id). Drop unresolved endpoints.

**Rationale**: Small models need a tight schema; Ollama `format` enforces structure. Exact prompt text lives in implementation, not stakeholder docs.

**Alternatives considered**:
- Free-form prose then regex — brittle on small models.
- Tool-calling only — less universal across Ollama model tags.

## R9. Agent context script

**Decision**: This Spec Kit install has **no** `update-agent-context` / agent-context bash script under `.specify/scripts/`. Skip agent-context update for this plan run; design artifacts under `specs/006-ollama-llm-extraction/` are the source of truth for downstream `/speckit-tasks`.

**Rationale**: Skill requires running the script when present; absence → skip without blocking Phase 1.
