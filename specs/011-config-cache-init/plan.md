# Implementation Plan: Config, Cache & Init Polish

**Branch**: `011-config-cache-init` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-config-cache-init/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Polish the local-first CLI with a complete YAML config surface (`ignored_patterns`, `embedding_model`, `llm_model`, `max_file_size`, `cache_dir`), a `grapheinstein init` command that writes a commented starter config, durable on-disk caching of parse chunks / ASTs / embeddings (stdlib sqlite + blob files under `cache_dir`), Rich progress on long runs, and fuller help/error text. No graph schema bump; no cloud services; no new required packages beyond the existing stack (sqlite3 stdlib).

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing — Typer, NetworkX, pathspec, Rich, Loguru, PyYAML, Tree-sitter, Ollama helpers. New cache uses **stdlib `sqlite3`** + filesystem blobs (not joblib; not tqdm — Rich `Progress` instead). See [research.md](./research.md).

**Storage**: Local filesystem — `~/.grapheinstein/config.yaml` (or `--config` / init `--output`); cache under resolved `cache_dir` (`index.sqlite` + `blobs/`); portable `graph.json` unchanged at schema `6.0.0`

**Testing**: pytest; Typer `CliRunner`; unit tests for config coercion, ignore merge, size skip, cache hit/miss/corrupt; contract tests for `init` help/flags and expanded config keys; integration: init → edit config → index twice (cache hits) on fixture project

**Target Platform**: macOS / Linux developer workstations (Windows best-effort via pathlib)

**Project Type**: Installable CLI package (extend existing `cli.py` + `utils.py` + `core/` layout)

**Performance Goals**: Unchanged re-index of ≥200 files finishes in ≤50% of cold-cache wall time on the same machine (SC-002); init completes in under 30 seconds (SC-001)

**Constraints**: Offline-only; CLI flags > `--config` > user config > defaults; human progress/errors on stderr only; non-interactive init must not hang; corrupt cache entries must not fail the whole index; older configs without new keys remain valid

**Scale/Scope**: Config + cache + init + CLI polish only — no new parsers, query algorithms, or schema version; modalities already supported continue to participate when indexed

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | YAML config + local cache dir; ignore rules; no cloud |
| CLI-first parity | PASS | New `init` subcommand; config/cache helpers in library modules for later MCP reuse |
| Provenance graph | PASS | No edge/provenance changes; indexing behavior only filters inputs |
| Multi-modal scope | PASS | Cache wraps existing code/docs/PDF/media parse + embedding paths; no new modalities |
| Incremental simplicity | PASS | stdlib sqlite + files; Rich already present; no Neo4j/vector DB |
| Schema/contract | PASS | Stay on graph `6.0.0`; CLI contract documents `init` + new config keys; tests required |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R1–R7; quickstart offline scenarios |
| CLI-first parity | PASS | [contracts/cli.md](./contracts/cli.md) documents `init` and config keys |
| Provenance graph | PASS | No graph schema mutation; [data-model.md](./data-model.md) is config/cache entities |
| Multi-modal scope | PASS | Cache kinds cover ast/chunk/embedding across existing parsers |
| Incremental simplicity | PASS | No Complexity Tracking violations; joblib/tqdm rejected |
| Schema/contract | PASS | Graph `6.0.0` retained; CLI contract additive |

## Project Structure

### Documentation (this feature)

```text
specs/011-config-cache-init/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cli.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/grapheinstein/
├── cli.py                 # init command; richer help; progress; _KNOWN_COMMANDS
├── utils.py               # AppConfig fields; load_config coercion; defaults; init template helper
└── core/
    ├── cache.py           # NEW: sqlite + blob cache API
    ├── index.py           # ignored_patterns + max_file_size; cache wiring; progress hooks
    ├── parsers/           # get/put around AST/chunk work where expensive
    └── parsers/llm_ollama.py  # optional embed cache wrapper (or thin helper in cache/embed)

tests/
├── fixtures/
│   └── config_cache/      # project with bulky dirs, oversized file, .gitignore
├── contract/
│   ├── test_cli_help.py   # extend: init listed; help non-empty
│   └── test_cli_init.py
├── integration/
│   └── test_cli_config_cache.py
└── unit/
    ├── test_config.py     # extend new keys
    ├── test_cache.py
    └── test_ignore_patterns.py
```

**Structure Decision**: Keep the existing single-package `cli.py` + `core/` layout. Add `core/cache.py` for the store; extend `utils.py` for config/init template; wire discovery and parsers through cache. No web/mobile options.

## Complexity Tracking

> No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
