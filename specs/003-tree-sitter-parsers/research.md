# Research: Tree-sitter Code Parsers

**Feature**: `003-tree-sitter-parsers`  
**Date**: 2026-07-16

## R1. Parser stack and grammar packaging

**Decision**: Use the official Python bindings package `tree-sitter` (`py-tree-sitter`) with **explicit per-language grammar packages** as install-time dependencies:

| Config name | Grammar package (planned) | Notes |
|-------------|---------------------------|--------|
| `python` | `tree-sitter-python` | |
| `javascript` | `tree-sitter-javascript` | `.js`, `.mjs`, `.cjs` |
| `typescript` | `tree-sitter-typescript` | Use TS + TSX language entry points; `.ts`, `.tsx` |
| `java` | `tree-sitter-java` | |
| `go` | `tree-sitter-go` | |
| `rust` | `tree-sitter-rust` | |
| `cpp` | `tree-sitter-cpp` | `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hh`; `.h` only when confidently C++ or paired with cpp sources (conservative: parse `.h` as cpp when `cpp` enabled) |
| `sql` | `tree-sitter-sql` (or best-maintained SQL grammar wheel available at implement time) | Dialects vary; extract best-effort |

Bundle grammars with the package install so default indexing needs **no runtime network download**.

**Rationale**: Constitution requires local-first/offline defaults. `tree-sitter-language-pack` can auto-download grammars, which conflicts with offline guarantees unless download is disabled and all eight grammars are pre-vendored—more opaque than listing wheels in `pyproject.toml`. Official `Language(pkg.language())` + `Parser` + `Query` / `QueryCursor` is the documented py-tree-sitter pipeline.

**Alternatives considered**:
- `tree-sitter-language-pack` with auto-download — rejected for default path (network).
- `py-tree-sitter-languages` monolith — convenient but less transparent versioning per grammar; optional later if wheels simplify CI.
- Regex-only extractors — rejected; constitution and spec require structure-aware AST extraction.
- Native `ast` module for Python only — rejected; multi-language requirement.

## R2. Schema version bump

**Decision**: Bump `schema_version` to **`3.0.0`**. Loaders that currently accept only `file`|`dir` nodes and `contains`|`references` edges MUST be updated to accept code-entity nodes and new edge types. Artifacts with `schema_version` `2.0.0` (or older) are **rejected** by visualize/status with a clear re-index message (same fail-closed policy as 2.x vs 1.x). No silent migration.

**Rationale**: Constitution: schema changes are breaking; bump version, document migration, prevent silent misreads. Current `NODE_TYPES` / `EDGE_TYPES` frozensets would reject new kinds if left unchanged.

**Alternatives considered**:
- Stay on `2.0.0` and widen types without bump — rejected (consumers cannot detect capability).
- Dual-read 2.x + 3.x — deferred; keep fail-closed for this increment.

## R3. Code entity identity and node shape

**Decision**:

- New node `type` values: `function`, `class`, `method` (mandatory kinds for this feature).
- Node `id` format (stable, unique):  
  `{file_posix_path}::{kind}::{name}::{start_line}`  
  Example: `src/app.py::function::greet::12`
- Required attributes on code-entity nodes:
  - `type`: `function` | `class` | `method`
  - `metadata` object including at least: `name`, `language`, `file` (same as file node id), `start_line` (1-based int). Optional: `end_line`, `qualified_name`.
- File/dir nodes remain `type: file|dir` as in schema 2.x.

Anonymous / unnamed definitions: **omit** (no synthetic names) unless the grammar exposes a stable name field.

**Rationale**: Spec requires location (line) and distinct entities when names collide across files. Encoding file + kind + name + line in `id` keeps NetworkX node keys unique without a separate registry.

**Alternatives considered**:
- UUID ids — less useful for agents and diffs.
- Name-only ids — collisions.
- Separate nodes for every import/call *expression* — optional later; edges carry relationship semantics for v1 of this feature.

## R4. Extraction via tree-sitter Queries

**Decision**: For each language, maintain Tree-sitter query patterns (`.scm` files or Python string constants under `core/parsers/`) that capture:

- Function / method / class definitions (name + start line from capture node `start_point`)
- Import statements (module / symbol text)
- Call expressions (callee name / attribute tail)

Shared orchestration:

1. Map file suffix → language (if enabled)
2. Read bytes (UTF-8; on decode failure skip structure extract with warning)
3. `parser.parse(source)` → walk/query
4. Emit entity records + raw import/call facts
5. Resolve facts to edges (R5)
6. Merge into the inventory DiGraph

Parse errors: Tree-sitter still returns a tree; treat files with no extractable named definitions as empty structure (not fatal). On language load failure or unexpected exceptions per file: log warning, skip structure for that file, continue index.

**Rationale**: Matches documented py-tree-sitter `Query` / `QueryCursor` usage; keeps language differences in query files rather than ad-hoc walkers everywhere.

**Alternatives considered**:
- Hand-written node walks only — harder to maintain across eight grammars.
- External SCIP/LSIF indexers — heavier deps, not CLI-local simple.

## R5. Import and call resolution

**Decision** (best-effort, prefer omission over wrong edges):

**Defines**
- File → each top-level `function` / `class` defined in that file (`defines`)
- Class → each `method` defined in that class (`defines`)
- Optionally also File → method (`defines`) for simpler file-centric queries — **yes**: emit both class→method and file→method `defines` when a method has an owning class

**Imports**
- Edge `imports` from **file** node → target when resolvable:
  - Target is a **file** node in the graph when the import maps uniquely to an indexed source file (language-appropriate path rules; start with Python relative/`from x import` → path heuristics and JS/TS relative `./`/`../` paths)
  - If the import names a symbol that uniquely matches a code-entity in that file, prefer entity target; else file target
- Unresolved / external package imports: **no edge** (do not create stub external nodes in this increment)
- Ambiguous targets: **no edge**

**Calls**
- Edge `calls` from caller entity (`function`|`method`) → callee entity when:
  1. Same-file unique name match, else
  2. Project-wide unique name match among enabled-language entities
- Attribute calls (`obj.method`): resolve using the attribute name with the same uniqueness rules (no type inference)
- Ambiguous or unresolved: **no edge**
- Do not create `calls` edges from file nodes unless there is no enclosing function/method (script-level call): then source may be the **file** node

All of the above edges: `provenance: extracted`.

**Rationale**: Spec explicitly prefers confident resolution; fabricating cross-links is worse than omission. Full type-aware resolution is out of scope.

**Alternatives considered**:
- External module stub nodes — deferred (schema noise).
- LLM inferred links — out of scope (inferred provenance).

## R6. Language configuration

**Decision**:

- Canonical language ids (lowercase):  
  `python`, `javascript`, `typescript`, `java`, `go`, `rust`, `cpp`, `sql`
- Default when unset: **all eight**
- Config key in YAML: `languages: [python, go, ...]` (list of strings)
- CLI override on `index`: `--languages python,go` (comma-separated). Empty/absent flag → use config/default. Flag present → that exact set for the run.
- Precedence: CLI `--languages` > `--config` / user config `languages` > built-in all-eight
- Unknown name: **fail** index before write (FR-014); list valid names in the error

**Rationale**: Matches User Story 2 and keeps agent/non-interactive use simple.

**Alternatives considered**:
- Repeated `--language` flags only — also fine; comma-separated is enough for v1.
- Soft-ignore unknown names — rejected by spec clarification-style fail-closed rule.

## R7. Index pipeline integration

**Decision**: After building the file/dir inventory and basename `references` (existing 002 flow), run code-structure extraction over discovered **file** nodes whose suffix maps to an enabled language and that are regular readable files (not symlinks, or skip symlink targets for parse). Merge nodes/edges into the same `DiGraph`, then serialize schema `3.0.0`.

Update index summary / `GraphStats` / visualize to include counts of code-entity nodes (by type) and `defines` / `imports` / `calls` edges without breaking existing file/dir/`contains`/`references` reporting.

**Rationale**: Spec FR-001/FR-013 — extend, don’t replace inventory.

**Alternatives considered**:
- Separate graph file for code — rejected (one portable artifact).
- Parse before ignore-aware discovery — rejected; must respect `.gitignore`.

## R8. SQL construct mapping

**Decision**: Map SQL extractions conservatively:

| Graph kind | SQL constructs (when present) |
|------------|-------------------------------|
| `function` | `CREATE FUNCTION` / procedure-like routines |
| `class` | Omit if no clear analogue (do not invent) |
| `method` | Omit |
| `imports` | Omit unless grammar exposes clear cross-object includes (rare) |
| `calls` | Calls/invocations of known routines when uniquely resolvable |
| `defines` | File → extracted routine entities |

A SQL file with only DDL tables/views may contribute **zero** code-entity nodes; that is success.

**Rationale**: Spec assumptions allow closest natural constructs; tables/views are deferred to a later SQL-schema feature unless trivially available—keep this increment aligned with function/class/method vocabulary.

**Alternatives considered**:
- Table/view nodes now — expands scope beyond requested entity kinds.

## R9. Visualize and loader compatibility

**Decision**: Extend validation allow-lists for node types and edge types. Console summary MUST report:

- Nodes: files, dirs, functions, classes, methods (and total)
- Edges: contains, references, defines, imports, calls (counts)

DOT export includes new nodes/edges with labels (relationship `type`). Reject schema ≠ `3.0.0`.

**Rationale**: FR-016 — consumers remain usable.

## R10. Dependencies and performance

**Decision**: Add `tree-sitter` and the eight grammar packages to main `dependencies` in `pyproject.toml` (not optional), so `pip install grapheinstein` is enough for default multi-language index. Performance target: ≥200 source files / &lt;3 minutes offline on a typical laptop (SC-005). Reuse one `Parser` per language per index run; avoid re-loading grammars per file.

**Rationale**: Constitution multi-modal code parsing is core, not an extra.

**Alternatives considered**:
- Extra (`pip install grapheinstein[code]`) — weaker defaults vs constitution “parsers MUST cover multi-language code”.
