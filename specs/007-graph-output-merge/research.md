# Research: Valid Graph Output, Compression, Versioning & Merge

**Feature**: `007-graph-output-merge`  
**Date**: 2026-07-17

## R1. Always-valid complete graph writes (atomic + validate)

**Decision**:

1. Keep building the artifact via existing `to_artifact_dict` (NetworkX `node_link_data` with `edges="links"`, then normalize nodes/links/graph meta).
2. Before writing bytes, run `validate_artifact` on the in-memory dict (same rules as load). If validation fails, abort with a clear error and **do not** write the destination.
3. Write atomically: serialize to a temp file in the same directory as the destination, `fsync` when practical, then `os.replace` onto the final path so readers never observe a truncated JSON file under the success path.
4. On OSError during write/replace, leave any prior successful artifact untouched; do not leave a `.tmp` success path.

**Rationale**: Spec FR-001–004 and Story 1 require complete metadata and no corrupt success artifacts. Validate-before-write catches serializer regressions; atomic replace addresses crash/interrupt mid-write.

**Alternatives considered**:
- Write-in-place with indent — simpler but can leave truncated files on crash.
- Validate only on load — insufficient; writers can still emit invalid artifacts.
- Dual-write (validate after write by re-reading) — good defense-in-depth; optional in tests, not required if validate-before-write + atomic replace are solid.

## R2. Compression format and CLI

**Decision**:

- Algorithm: **gzip** via stdlib `gzip` module (no new dependency).
- CLI: `--compress` flag on `index` (and `merge`).
- Path rule: if `--compress` and the resolved output path does **not** end with `.gz`, append `.gz` (e.g. `graph.json` → `graph.json.gz`). If the user already passes `*.json.gz`, use that path as-is.
- Default remains uncompressed `.json`.
- Load path (`load_artifact` and merge inputs): if path ends with `.gz` **or** content is detected as gzip magic, decompress then parse JSON; otherwise plain UTF-8 JSON.
- Minimum bar: index write + merge read of `.json.gz`. Prefer routing `visualize`/`status` through the same loader so gzip works everywhere graphs are read (small change, high consistency).

**Rationale**: Spec assumes gzip; stdlib keeps installs light. Auto-appending `.gz` avoids writing gzip bytes to a path that looks like plain JSON.

**Alternatives considered**:
- ZIP archive — heavier UX; multi-member unnecessary for one JSON doc.
- zstd — better ratios but new dependency; rejected for v1.
- Always compress — breaks agent workflows that expect plain `graph.json`; rejected.

## R3. File versioning (`graph_vN.json`)

**Decision**:

- CLI: `--versioned` on `index` (default off).
- When enabled, after (or as part of) a successful write of the primary `--output` “latest” file, also write a snapshot named `graph_v{N}.json` (or `graph_v{N}.json.gz` if compressing) in the **same directory** as the primary output path.
- `N` = max existing `N` among files matching `graph_v(\d+)\.json(\.gz)?` in that directory, plus one; if none exist, `N = 1`.
- Never overwrite an existing `graph_vN` file; if the computed path somehow exists, skip to next free `N` (defensive).
- Primary `--output` is still written/overwritten as today’s “latest” pointer (FR-007).
- Versioning does not change `schema_version`; it is filesystem snapshot naming only.

**Rationale**: Matches spec Stories 3 and Assumptions; directory-local numbering is predictable and offline.

**Alternatives considered**:
- Version only (no latest overwrite) — conflicts with FR-007 and agent “always read graph.json” habit.
- Content-hash filenames — harder for humans; deferred.
- Embed version in schema envelope — orthogonal; schema already has `schema_version` for format, not run history.

## R4. Merge semantics and conflicts

**Decision**:

- New command: `grapheinstein merge INPUT [INPUT ...] --output PATH [--compress]`.
- Require **≥ 2** inputs; fewer → usage error, non-zero exit.
- Load each input via gzip-aware loader; each must pass `validate_artifact` and share the **same** `schema_version` equal to the running tool’s `SCHEMA_VERSION` (`6.0.0`). Mismatch → fail, name the file and versions.
- **Nodes**: union by `id`.
  - Missing in accumulator → add.
  - Present with **equivalent** payload (`type` equal and `metadata` deep-equal) → keep one.
  - Present with incompatible `type` or `metadata` → **hard fail** naming the `id` and input paths; write no success output.
- **Edges**: union keyed by `(source, target, type, provenance)` plus normalized optional attrs (`confidence`, `evidence`, `reason`). Identical → dedupe; incompatible attrs on same key → hard fail.
- **Graph-level metadata** on result:
  - `generated_at`: fresh UTC ISO-8601 at merge time.
  - `merged`: `true`.
  - `merged_from`: list of absolute (or resolved) input path strings in CLI order.
  - `project_root`: if all inputs share the same `project_root`, keep it; if they differ, omit a single false root and set `project_roots` (list of unique roots) instead (and MAY set `project_root` to `""` or omit — contract will specify omit + `project_roots` only when divergent).
  - Retain other graph keys only when identical across all inputs; drop non-identical optional flags rather than inventing values.
- Output written with the same atomic + validate + optional gzip pipeline as index.

**Rationale**: Spec FR-008–011 and Story 4; hard-fail conflicts avoid silent corruption of agent libraries. Constitution calls out graph merge tests.

**Alternatives considered**:
- Last-write-wins — rejected by spec Assumptions.
- Soft-merge metadata (deep-merge maps) — ambiguous for agents; deferred.
- Re-index from filesystem during merge — out of scope (FR: artifacts only).

## R5. Schema version

**Decision**: Remain on **`schema_version` `6.0.0`**. Document additive optional `graph` keys (`merged`, `merged_from`, `project_roots`). No new node/edge types. Loaders continue to require exact `6.0.0`.

**Rationale**: Constitution requires bumps for breaking shape changes. Optional graph metadata that existing validators ignore is additive and compatible with current `validate_artifact`.

**Alternatives considered**:
- Bump to `6.1.0` or `7.0.0` — unnecessary churn for optional keys; would force re-index of all graphs just to merge.
- Separate “merge envelope” format — fragments the portable artifact story; rejected.

## R6. Config surface

**Decision**: CLI flags are the primary surface (`--compress`, `--versioned`). Optionally accept matching YAML keys `compress` / `versioned` in config with same precedence as other flags (CLI > config file > user config > default `false`). Do not change default index behavior when flags are absent.

**Rationale**: Keeps one-shot agent invocations explicit; config convenience is optional and low risk.

**Alternatives considered**:
- Config-only — worse for discoverability and one-off merges.
- Environment variables — skip for v1; flags suffice.
