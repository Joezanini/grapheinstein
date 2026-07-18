# Research: Path Between Concepts

**Feature**: `009-path-query`  
**Date**: 2026-07-17

## R1. CLI shape and exit semantics

**Decision**:

- Command: `grapheinstein path START END --input PATH [--output PATH] [--match-threshold F] [--max-hops N] [--no-llm-explain] [--llm-model …] [--llm-base-url …] [--config …]`.
- `START` and `END` are required positionals; empty/whitespace → usage error, non-zero exit.
- `--input` / `-i` required.
- `--output` / `-o` optional: when set, write the structured path-answer JSON to that file; always print the same JSON to stdout on success (agents pipe stdout). Human explanation and progress on stderr.
- Exit `0` when both endpoints resolve and a path (including trivial same-node) is found and the answer is emitted.
- Exit non-zero when: invalid/missing input, validation failure, either endpoint unmatched, no connecting path, path exceeds `max_hops`, or output write failure.

**Rationale**: Matches FR-001, FR-007–009 and constitution CLI-first (structured stdout/file + human stream). Optional `--output` covers agents that prefer files without breaking pipe-friendly defaults.

**Alternatives considered**:

- Require `--output` like explain — heavier for quick human queries; path answers are smaller than subgraphs.
- Human-only text on stdout — breaks agent consumption (SC-007).

## R2. Endpoint resolution

**Decision**:

- Reuse `core/match.py` scoring (fuzzy always; optional local embeddings when available) with the same defaults as explain (`match_threshold` default **`0.55`**).
- Resolve **exactly one** node per endpoint: the top-ranked candidate with `final_score ≥ threshold`.
- If either side has zero candidates above threshold → fail and report which endpoint(s) failed.
- Tie-break: same as match.py (higher score, prefer `concept`, shorter id).
- Do not merge multi-match neighborhoods (unlike explain); path needs single terminals.

**Rationale**: Spec Story 3 and Assumptions require explain-style matching; single terminals keep shortest_path well-defined.

**Alternatives considered**:

- Exact ID only — fails approximate-phrase scenarios.
- Top-N starts × top-N ends and pick best path — combinatorially heavier; defer if needed later.
- Fail when embeddings unavailable — conflicts with graceful degradation.

## R3. Directed weighted shortest path (NetworkX)

**Decision**:

- Load input as a NetworkX **DiGraph** (schema `directed: true`, `multigraph: false`).
- Compute `networkx.shortest_path(G, source, target, weight=weight_fn)` where `weight_fn(u, v, data) -> float` returns a positive edge cost.
- Treat the graph as **directed**; do not invent reverse edges.
- Same start and end node → trivial path: `nodes=[id]`, `steps=[]`, explanation notes identity.
- `NetworkXNoPath` → clear “no path” failure, non-zero exit.
- Optional safety: `--max-hops` / config default **`32`** (edge count). If the found path has more than `max_hops` edges → fail clearly (avoid dumping unbounded walks).

**Rationale**: Spec and user input require NetworkX shortest_path with multi-factor weights; directed matches schema and Assumptions.

**Alternatives considered**:

- Undirected view — can invent reverse semantics; rejected for v1 (document if users need undirected later).
- Unweighted BFS — fails Story 2 (prefer trustworthy routes).
- Yen’s k-shortest paths — useful for alternatives UI; out of scope for v1 (return one preferred path).

## R4. Edge cost / multi-weight policy

**Decision**: Positive cost so lower total = preferred. For each edge:

```text
cost = type_base[type] * provenance_factor[provenance] / max(confidence, ε)
```

Defaults:

| Factor | Values |
|--------|--------|
| `ε` (missing/zero confidence floor) | `0.35` when confidence absent; clamp used confidence to `[ε, 1.0]` |
| `provenance_factor` | `extracted` → `1.0`; `inferred` → `1.75` |
| `type_base` | Semantic / dependency edges cheaper than pure containment (see table below) |

**Default `type_base`** (tunable via config map `path_type_weights` later; ship these built-ins):

| Edge type | Base |
|-----------|------|
| `implements`, `depends_on`, `calls`, `imports` | `1.0` |
| `mentions`, `references`, `related_to`, `defines` | `1.25` |
| `section_of` | `1.5` |
| `contains` | `2.0` |
| unknown / other allow-listed types | `1.5` |

Missing `confidence` → treat as `0.5` before applying `ε` floor (so absent confidence is neutral, not best).

Document that exact numeric bases are planning defaults; behavior contract is: higher confidence and `extracted` lower cost than low confidence / `inferred` when type is equal.

**Rationale**: Spec Story 2 and FR-004/011; containment-heavy shortest hop-count paths are usually less explanatory than semantic links.

**Alternatives considered**:

- Hop-count only — rejected by multi-weight requirement.
- Confidence-only weight — ignores provenance and type preference.
- Softmax / learned weights — overkill for v1.

## R5. Path answer shape and explanation

**Decision**:

- Primary machine artifact: **Path Answer JSON** (see [contracts/path-json.md](./contracts/path-json.md)), not a schema `6.0.0` graph file.
- Include: resolved start/end ids + scores, ordered `nodes`, ordered `steps` (`source`, `target`, `type`, `provenance`, optional `confidence`), total cost, explanation text, schema/version fields.
- **Deterministic explanation** always: template that walks steps (“A —[calls/extracted]→ B —[…]→ C”).
- Optional local LLM polish (reuse `chat_text` when available): rewrite for readability **from the same step facts only**; on failure/unavailable, keep deterministic text. `--no-llm-explain` skips polish.
- Explanation text is included in the JSON (`explanation`) and also printed on stderr for humans.

**Rationale**: FR-005–007, FR-012; agents get one JSON object; humans get stderr narrative without corrupting stdout JSON when piping.

**Alternatives considered**:

- Emit a path chain as `graph.json` subgraph — nice later; v1 path-answer is simpler and matches “path answer” constitution wording.
- LLM-required explanation — conflicts with offline deterministic fallback.

## R6. Artifact I/O

**Decision**:

- Load via existing gzip-aware `load_artifact`; validate schema `6.0.0`.
- Convert to DiGraph with existing/shared node-link helpers (add thin helper in `graph.py` or `path.py` if missing).
- Do not mutate or rewrite the input graph.
- Optional `--output`: atomic write of path-answer JSON (plain UTF-8; `.gz` only if shared helpers already support generic JSON gzip—default plain JSON).

**Rationale**: Query-only feature; no schema bump for input graphs.

**Alternatives considered**:

- Schema 7.0.0 — unnecessary; path answer is a separate contract.

## R7. Agent context script

**Decision**: This Spec Kit install has **no** `update-agent-context` script under `.specify/scripts/`. Skip agent-context update for this plan run; design artifacts under `specs/009-path-query/` are the source of truth for `/speckit-tasks`.

**Rationale**: Same as features 006–008.

**Alternatives considered**: Hand-edit unrelated agent docs — out of scope for `/speckit-plan`.
