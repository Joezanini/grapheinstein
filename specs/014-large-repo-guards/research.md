# Research: Large Repo Guards

**Feature**: `014-large-repo-guards`  
**Date**: 2026-07-19

## R1. Where guards live (core vs wrapper-only)

**Decision**: Implement scoping, reference bounds, scan-cost preflight, optional byte/file caps, and cooperative timeout **in grapheinstein core** (`index` / `api.index` / config). Treat OpenClaw-style wrappers as consumers that can set stricter timeouts/limits, not as the only place guards exist.

**Rationale**: Today core always inventories the full non-ignored tree and runs unbounded `add_reference_edges` (full UTF-8 read × unique basenames). Wrapper preflight that only checks total MB / file count still admits google-api-python-client and then burns 1200s with no graph. Core ownership fixes all entrypoints (CLI, Python API, serve).

**Alternatives considered**:
- **Wrapper-only path allowlist** — helps one integrator; leaves CLI users exposed; rejected as sole fix.
- **Core sharding/merge first** — heavier than scope+bounds; deferred per spec FR-012.

## R2. Code-only mode and default ignores

**Decision**:

1. Add boolean **`code_only`** (CLI `--code-only`, config `code_only`, API kwarg).
2. When `code_only` and not `include_generated_docs`, merge **`CODE_ONLY_DEFAULT_IGNORES`** into discovery ignores (after `.gitignore` + `ignored_patterns`):

   ```text
   docs/
   docs/dyn/
   **/docs/dyn/
   discovery_cache/
   **/discovery_cache/
   ```

3. Add **`--include-generated-docs`** / `include_generated_docs: true` to omit those built-in patterns for intentional full-doc graphs (still subject to cost/size gates).
4. Default CLI behavior without `--code-only` remains current inventory semantics (no auto `docs/` exclusion), but **reference bounds** (R3) still apply globally.

**Rationale**: Spec priority “scope before chunk”; user recommendation explicitly names `docs/`, `docs/dyn/`, discovery caches. Excluding all of `docs/` under code-only matches the incident repo; operators who need hand-written docs under `docs/` can opt in or point `--code-only` off and use custom ignores.

**Alternatives considered**:
- **Always ignore `docs/dyn/` even without code-only** — reasonable, but may surprise doc-first indexes; keep tied to code-only + opt-in for clarity.
- **Index only `googleapiclient/` by hardcoded package name** — not general; rejected.
- **Inventory all files but skip docs only in reference scan** — still leaves huge inventories and preflight size; weaker than path exclusion.

## R3. Bounding reference scanning

**Decision**: Change `add_reference_edges` to:

1. **Skip** files with `metadata.skipped == "oversize"` (align with parsers).
2. **Skip** symlinks (unchanged).
3. When `code_only`: **only scan** files whose suffix is in Tree-sitter `EXTENSION_MAP` (code-eligible). Basename **targets** may still resolve to any unique inventoried file (so a `.py` file can reference another `.py`); non-code files are not *sources* of scans.
4. **Cap** bytes read per eligible file: `max_reference_scan_bytes` (default **262144** / 256 KiB). Read at most that many bytes (binary-safe then decode UTF-8 with replacement or skip on hard failure—prefer decode of the capped slice).
5. Preserve whole-token regex semantics and longest-basename-first ordering for the scanned text slice.
6. Keep `extracted` provenance on created `references` edges.

**Rationale**: Incident cost was ~eligible_files × unique_basenames with full-text reads of HTML/JSON. Skipping non-code + oversize and capping text cuts work by orders of magnitude while keeping SC-006 happy-path edges among code files.

**Alternatives considered**:
- **Aho-Corasick / single-pass multi-pattern** — better asymptotics later; not required if eligibility shrinks N; defer.
- **Scan only after structure parse / only “parsed” files** — tighter but changes when refs run; eligibility filter is enough for v1.
- **Drop reference edges in code-only** — fails SC-006 / product value; rejected.

## R4. Preflight metrics and thresholds

**Decision**: After discovery produces the inventory candidate set (with oversize metadata), compute:

| Metric | Definition |
|--------|------------|
| `eligible_scan_files` | Files that would be scanned under R3 rules |
| `unique_basenames` | Count from `unique_basename_targets` |
| `estimated_scan_ops` | `eligible_scan_files * unique_basenames` |
| `non_code_share` | `(bytes of non-code files) / (bytes of all regular files)` in inventory; empty inventory → 0 |
| `total_bytes` / `file_count` | Sum/count of regular file sizes in inventory |

**Default thresholds** (config/CLI overridable):

| Key | Default | Gate |
|-----|---------|------|
| `max_reference_scan_ops` | `5_000_000` | Reject if `estimated_scan_ops` exceeds |
| `max_non_code_share` | `0.85` | Reject if `code_only` and share exceeds (doc dumps without ignores) |
| `max_total_bytes` | `838_860_800` (800 MiB) | Hard reject if inventory exceeds |
| `max_file_count` | `20000` | Hard reject if inventory exceeds |
| `large_repo_policy` | `reject` | `allow` skips **advisory** cost/share gates only |

Hard byte/file caps always apply. `large_repo_policy: allow` / `--allow-large-repo` bypasses scan-ops and non-code-share rejects only.

**Rationale**: Matches wrapper’s crude 800 MB / 20k while adding the missing cost dimension; 5e6 ops ≈ few seconds of regex work on a laptop, far below 76e6 incident scale. Thresholds tunable in planning fixtures.

**Alternatives considered**:
- **Wall-clock estimate from ops × constant** — machine-dependent; ops count is enough.
- **Lower defaults to 200 MB / 5k** — optional later; not required if cost gate works.

## R5. Timeout and failure reporting

**Decision**:

1. Add optional `timeout_seconds` (default `0` = disabled in core CLI; wrappers may set 1200).
2. Cooperative checks between major phases and periodically during reference scan (e.g., every N files): if exceeded → raise typed error, exit non-zero, **do not** write success graph.
3. Error message MUST include last completed / in-progress **phase** (`discovery`, `preflight`, `references`, …).
4. Partial graph write on timeout is **out of scope** (spec: no fake success; partial optional later).

**Rationale**: Spec FR-009/010; wrappers already kill with 124 and get nothing—core should fail clearly if a timeout is configured.

**Alternatives considered**:
- **Signal-based hard kill only in wrapper** — no phase info; keep as outer bound, add cooperative core timeout when configured.
- **Always write partial graph.json** — risks agents treating incomplete refs as complete; deferred.

## R6. CLI / API surface

**Decision**: Additive flags and config keys (see contracts):

- `--code-only` / `code_only`
- `--include-generated-docs` / `include_generated_docs`
- `--allow-large-repo` (sets policy allow for this run)
- Config (and optional CLI): `max_reference_scan_bytes`, `max_reference_scan_ops`, `max_non_code_share`, `max_total_bytes`, `max_file_count`, `timeout_seconds`, `large_repo_policy`

Mirror on `api.index` and serve `POST /index` body. Update `grapheinstein init` template comments for new keys.

**Rationale**: Constitution CLI-first parity; agents need the same knobs.

## R7. Graph schema and sharding

**Decision**: Keep **`schema_version` `6.0.0`**. No new edge types. Sharding/path-merge/resume **out of scope** (FR-012).

**Rationale**: Behavior-only change; avoids migration. Full-docs intentional graphs can be a later feature.

## R8. Code-eligible extension source

**Decision**: Reuse `EXTENSION_MAP` keys from `core/parsers/registry.py` as the code-suffix set for scan eligibility under `code_only`. Do not use `media_link.CODE_EXTENSIONS` (includes `.md`/`.pdf`).

**Rationale**: Aligns “code” with Tree-sitter structure languages; avoids scanning Markdown as code under `--code-only`.

---

All Technical Context unknowns resolved; no remaining NEEDS CLARIFICATION.
