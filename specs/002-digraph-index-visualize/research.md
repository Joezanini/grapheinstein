# Research: Directed File Graph Index & Visualize

**Feature**: `002-digraph-index-visualize`  
**Date**: 2026-07-16

## R1. Schema version and node shape migration

**Decision**: Bump `schema_version` to `2.0.0`. Nodes use `id`, `type` (`file` | `dir`), and `metadata` (object, default `{}`). Drop `kind` / `directory` / top-level duplicate `path` as required fields (path identity remains `id`). Loaders reject artifacts that use the 1.x shape or missing required v2 fields with a clear “unsupported format; re-index” error. No silent field mapping.

**Rationale**: Spec clarifications require new-shape only. Constitution treats schema changes as breaking: bump version, document migration (re-index), prevent silent misreads.

**Alternatives considered**:
- Dual-read old+new — rejected by clarification.
- On-load migrate — rejected by clarification.
- Keep `kind`/`directory` names — conflicts with requested `type`/`dir` API.

## R2. Symlink-safe discovery

**Decision**: During `iterdir` walks, if `entry.is_symlink()`, treat as a `file` node and **do not** push onto the directory stack. Do not call `is_dir()` before the symlink check (pathlib `is_dir()` follows symlinks by default and would traverse targets). Continue ignoring `.git` and `.gitignore` matches as in feature 001.

**Rationale**: Matches FR-015 and avoids cycles / escaping the project root.

**Alternatives considered**:
- Follow in-project symlinks — rejected by clarification.
- Omit symlinks entirely — rejected; spec requires a `file` node for the link path.

## R3. Whole-token basename `references`

**Decision**: After the inventory graph exists, build a map of basename → list of file node ids. Only basenames with exactly one file id are eligible. For each UTF-8-decodable text file (skip binary / decode failures with a warning), scan content with a regex of the escaped basename using lookarounds so adjacent characters are **not** in the path-token class `[A-Za-z0-9._+-]`. Case-sensitive. No self-edges. At most one `references` edge per (source, target) pair. Edge attributes: `type=references`, `provenance=extracted`.

Process candidate basenames **longest-first** when scanning a file to prefer fuller names when overlapping patterns could compete in tests (still constrained by lookarounds).

Text detection heuristic: attempt `read_text(encoding="utf-8")`; on `UnicodeDecodeError` treat as binary/non-text and skip mention scan (node still present).

**Rationale**: Clarification chose whole-token matching; including `.` / `+` / `-` in the boundary class prevents `main` matching inside `main.py` while still matching `main.py` as its own token.

**Alternatives considered**:
- `\b` word boundaries — false positives for `main` inside `main.py`.
- Substring match — rejected by clarification.
- AST/import resolution — out of scope.
- Aho–Corasick multi-pattern — optional optimization later; simple loop is enough for Phase scope.

## R4. Serialization (node-link) and stats

**Decision**: Continue NetworkX `DiGraph` + `json_graph.node_link_data(..., edges="links")` with envelope fields `schema_version`, `directed`, `multigraph`, `graph` metadata. Normalize exported nodes to `{id, type, metadata}` and links to `{source, target, type, provenance}`. Update `GraphStats` / status / index summary to count `type == file|dir` and optionally report edge counts by type for visualize.

**Rationale**: Constitution default interchange format; matches FR-002 and existing package skills.

**Alternatives considered**:
- Custom non-node-link JSON — breaks constitution default and NetworkX round-trip convenience.
- MultiGraph — unnecessary; one edge per pair/type is enough.

## R5. Visualize summary and DOT export

**Decision**: Add `grapheinstein visualize --input PATH [--dot PATH]`. Always print a Rich summary (files, dirs, total nodes, contains count, references count, short sample of node ids / edges) to the human console stream. If `--dot` is set, write a UTF-8 DOT file (overwrite if exists) using a **hand-written** emitter (no pydot/pygraphviz dependency). DOT: `digraph G { ... }` with quoted node ids; edges labeled with relationship type.

**Rationale**: Clarification: DOT to file + keep summary. Avoiding Graphviz Python bindings keeps install light; users can run `dot` externally if installed.

**Alternatives considered**:
- `nx.drawing.nx_pydot` — adds fragile native deps.
- DOT on stdout only — rejected by clarification.
- Suppress summary when exporting — rejected by clarification.

## R6. CLI surface and overwrite semantics

**Decision**: Keep `index` / default-path alias / `status`. Register `visualize` in the known-command set so default-path rewriting does not swallow it. Index `--output` and visualize `--dot` overwrite existing writable files without prompts. Fail clearly on missing project path, unreadable/malformed/unsupported graph, or unwritable targets.

**Rationale**: Aligns with FR-001, FR-008–009, FR-012, FR-016 and existing Typer entrypoint patterns.

**Alternatives considered**:
- `--force` gate for overwrite — rejected by clarification.
- Interactive confirm — rejected (non-interactive agents).

## R7. Status command compatibility

**Decision**: Update `status` (and any load/stats helpers) to read v2 `type` fields only. Old graphs fail with the same unsupported-format error as visualize. Do not remove the `status` command.

**Rationale**: Spec assumes status remains; schema break applies to all loaders.

**Alternatives considered**:
- Leave status on v1 fields — would contradict FR-014 and confuse users.
