# Implementation Plan: Large Repo Guards

**Branch**: `014-large-repo-guards` | **Date**: 2026-07-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-large-repo-guards/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Design details live in `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

## Summary

Stop code-only (and default) indexing from hanging on doc-heavy OSS trees like `google-api-python-client` by (1) applying code-only default ignores for generated docs/discovery caches, (2) bounding reference linking so it skips oversize/non-eligible files and caps text read, and (3) adding core preflight that rejects on estimated reference-scan cost / non-code share before burning a timeout. Path sharding/merge stays out of scope. Graph schema stays `6.0.0`; CLI/API/config contracts are additive.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing — Typer, NetworkX, pathspec, Rich, Loguru, PyYAML, Tree-sitter. No new third-party packages. See [research.md](./research.md).

**Storage**: Local filesystem — YAML config (`ignored_patterns` + new keys); portable `graph.json` unchanged at schema `6.0.0`

**Testing**: pytest; Typer `CliRunner`; unit tests for ignore merge, scan eligibility, cost estimate, reference skip/cap; integration fixture mimicking doc-dump proportions; contract tests for new CLI flags/config keys and reject exit codes

**Target Platform**: macOS / Linux developer workstations (Windows best-effort via pathlib); offline

**Project Type**: Installable CLI package (extend `cli.py`, `api.py`, `utils.py`, `core/index.py`, `core/references.py`; mirror options on `serve/`)

**Performance Goals**: Doc-dump fixture (thousands of generated files, &lt;100 source files) completes default `--code-only` index in under 2 minutes on a typical laptop; high-cost trees reject in under 30 seconds (SC-001, SC-004)

**Constraints**: Local-first; no cloud; hard caps still win over overrides; reference whole-token semantics unchanged for eligible files; sharding/resume out of scope; cooperative timeout with phase reporting (no silent success)

**Scale/Scope**: Guards + scoping + bounded references + preflight for single-process index; modalities = code primary under `--code-only`; generated docs/discovery excluded by default in that mode; full-tree doc graphs deferred

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

### Pre-research (Phase 0 entry)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | All gates local; ignore/config only; no cloud |
| CLI-first parity | PASS | New flags/config keys on `index`; same params on `api.index` and serve `/index` |
| Provenance graph | PASS | `references` remain `extracted`; no schema mutation |
| Multi-modal scope | PASS | Code-only scopes inventory/scan; `--include-docs` / PDFs / media unchanged when paths not excluded |
| Incremental simplicity | PASS | Bound existing O(files×basenames) path; no shard/merge platform |
| Schema/contract | PASS | Graph `6.0.0` retained; CLI contract additive with tests |

### Post-design (Phase 1 exit)

| Gate | Status | Notes |
|------|--------|-------|
| Local-first | PASS | Confirmed in research R1–R7; quickstart offline |
| CLI-first parity | PASS | [contracts/cli.md](./contracts/cli.md), [contracts/python-api.md](./contracts/python-api.md) |
| Provenance graph | PASS | No graph schema change; eligibility only filters who is scanned |
| Multi-modal scope | PASS | Code-only default ignores documented; opt-in restores generated docs |
| Incremental simplicity | PASS | No Complexity Tracking violations; sharding deferred (FR-012) |
| Schema/contract | PASS | Graph `6.0.0`; CLI contract version `14.0.0` additive |

## Project Structure

### Documentation (this feature)

```text
specs/014-large-repo-guards/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── cli.md
│   └── python-api.md
└── tasks.md             # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/grapheinstein/
├── cli.py                 # --code-only, --include-generated-docs, --allow-large-repo,
│                          # timeout / scan-cap / limit flags (or config-driven)
├── api.py                 # Mirror new index kwargs
├── utils.py               # AppConfig keys; CODE_ONLY_DEFAULT_IGNORES; threshold defaults;
│                          # init template comments
└── core/
    ├── index.py           # Merge code-only ignores; preflight after discovery;
    │                      # phase markers for timeout; pass eligibility into refs
    ├── references.py      # Skip oversize/non-eligible; text byte cap; code-ext filter
    ├── graph.py           # Unchanged schema 6.0.0 (unless metadata-only notes)
    └── parsers/registry.py  # Reuse EXTENSION_MAP for “code-eligible” suffixes
serve/
    └── app.py             # IndexBody fields for new options

tests/
├── fixtures/
│   └── large_repo_guards/ # Tiny package + docs/dyn HTML dump + discovery_cache JSON
├── unit/
│   ├── test_references.py           # extend: oversize skip, cap, code-only filter
│   ├── test_ignore_patterns.py      # extend: code-only default ignores
│   └── test_preflight_scan_cost.py  # NEW: cost estimate + reject/override
├── integration/
│   └── test_cli_large_repo_guards.py
└── contract/
    └── test_cli_index_guards.py     # flags, exit codes, help text
```

**Structure Decision**: Single Python CLI package (existing layout). Changes concentrate in discovery/index orchestration and `references.py`; config/CLI/API remain the control surface. No new top-level packages.

## Complexity Tracking

> No constitution violations requiring justification. Sharding/merge explicitly rejected for this increment (spec FR-012).
