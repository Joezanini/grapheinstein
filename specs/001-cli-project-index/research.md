# Research: CLI Project Index Skeleton

**Feature**: `001-cli-project-index`  
**Date**: 2026-07-16

## R1. CLI framework and default command behavior

**Decision**: Use Typer with a root callback that accepts `project_path` and `--output` / `--config`, and invoke indexing when no subcommand is given. Expose explicit `index` and `status` subcommands that share the same core indexing/status functions.

**Rationale**: Constitution prefers Typer; spec requires default path invocation to equal `index`. Typer supports a callback plus subcommands; shared library functions keep slash/MCP parity later.

**Alternatives considered**:
- Click only — constitution allows it; Typer is preferred and matches user request.
- Separate top-level scripts — rejected; single `grapheinstein` entrypoint is required.
- Require always-explicit `index` — rejected; conflicts with FR-003.

## R2. Ignore-aware file discovery

**Decision**: Walk the project tree with `pathlib`, match paths against patterns loaded from the project's `.gitignore` via `pathspec` (`GitWildMatchPattern` / `from_lines`). Always include the project root as a directory node. On unreadable/broken `.gitignore`, log a warning and continue with empty ignore rules.

**Rationale**: Constitution names pathspec/git for ignore-aware discovery; pathspec is local, offline, and sufficient for this increment without spawning `git`.

**Alternatives considered**:
- Shell out to `git ls-files` — accurate for git repos but fails for non-git folders and adds process dependency.
- Manual glob parser — error-prone vs pathspec.
- `gitignore_parser` — viable; pathspec is the constitution-aligned default.

## R3. Graph model and `graph.json` serialization

**Decision**: Build an in-memory NetworkX `DiGraph`. Nodes: files and directories. Include `contains` edges from parent directory to child (provenance `extracted`). Persist with NetworkX `node_link_data` plus a thin envelope:

```json
{
  "schema_version": "1.0.0",
  "directed": true,
  "multigraph": false,
  "graph": { "project_root": "...", "generated_at": "..." },
  "nodes": [...],
  "links": [...]
}
```

Node `id` = POSIX-relative path from project root (`"."` for root). Node attributes include `kind` (`file` | `directory`) and `path` (same relative path).

**Rationale**: Constitution mandates NetworkX + portable `graph.json` with provenance on edges. Containment edges satisfy FR-008 without inferred relations.

**Alternatives considered**:
- Nodes-only JSON array — simpler but weaker for later queries and weaker constitution fit.
- RDF/Neo4j — premature; violates incremental simplicity.
- Absolute paths as IDs — less portable across machines.

## R4. Config loading

**Decision**: Load YAML config with precedence: CLI flags > `--config` file > `~/.grapheinstein/config.yaml` > built-in defaults. Initial keys: `output` (default `graph.json`), `log_level` (default `INFO`). Missing default config is not an error. Malformed YAML or unknown required types → non-zero exit with clear error.

**Rationale**: Matches FR-009/FR-010 and local-first constitution. Keep v1 config minimal.

**Alternatives considered**:
- TOML-only — YAML matches constitution and user request.
- Require config file — rejected; defaults must work alone.
- Nested profile system — YAGNI for this increment.

## R5. UX libraries (Rich + Loguru)

**Decision**: Rich for tables/panels on stderr (or console configured to stderr) for human summaries; Loguru for diagnostic logging to stderr. Never write human output into the graph file path.

**Rationale**: User-requested stack; separates FR-011 (human UX) from FR-012 (machine artifact).

**Alternatives considered**:
- stdlib logging + plain print — workable but weaker UX than requested.
- structlog — more complex than needed for Phase 1.

## R6. Package layout

**Decision**: Installable `src` layout aligning user-requested modules with constitution packaging:

```text
src/grapheinstein/
  __init__.py
  __main__.py
  cli.py
  utils.py
  core/
    graph.py
    index.py
    parsers/   # stub package for later modalities
pyproject.toml
tests/
```

Console script: `grapheinstein = grapheinstein.cli:app` (Typer app).

**Rationale**: User specified `cli.py` / `core/` / `utils.py`; `src/` layout is standard for hatchling/setuptools and keeps repo root clean. Parsers package is a stub only (no multi-modal parsing in this feature).

**Alternatives considered**:
- Flat `grapheinstein/` at repo root without `src/` — works but messier for tests/packaging.
- Full `cli/` / `ingest/` / `query/` tree from plan template — correct long-term; overkill before those features exist. Grow into that shape in later specs.

## R7. Status command behavior

**Decision**: `status` resolves the graph path from `--output` / config / default `graph.json` (relative to CWD unless absolute). If missing, print a clear “no index” message and exit non-zero (or exit 0 with explicit “not found” status — **choose exit code 2** for not found to distinguish from usage errors). If present, load JSON and report file/directory/total node counts and path.

**Rationale**: Spec requires clear reporting without crash; distinct exit code helps agents.

**Alternatives considered**:
- Always re-scan project for status — slower; status should reflect persisted artifact.
- Store sidecar SQLite — YAGNI.

## R8. Testing approach

**Decision**: pytest with `tests/unit` (ignore matching, graph build, config merge) and `tests/integration` (CLI via `typer.testing.CliRunner` against a fixture project with `.gitignore`). Contract checks assert `schema_version` and required node fields per `contracts/graph-json.md` and `contracts/cli.md`.

**Rationale**: Constitution requires tests when CLI contracts and graph schema are touched.

**Alternatives considered**:
- Manual-only validation — insufficient for schema/CLI contracts.
- unittest only — pytest is the ecosystem default for Typer apps.

## Resolved clarifications

No `NEEDS CLARIFICATION` items remain in Technical Context. Library call signatures will be verified against current docs during `/speckit-implement`.
