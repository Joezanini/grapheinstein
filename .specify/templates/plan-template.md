# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (Grapheinstein)*

- **Local-first**: Feature works offline with local models/config; no
  required cloud APIs; respects `.gitignore` / ignore rules; cache paths
  configurable.
- **CLI-first parity**: Capability exposed via `grapheinstein` subcommands;
  slash-command/MCP (if any) reuse the same library/API; structured JSON
  output supported for agent consumption.
- **Provenance graph**: Edges use explicit relationship types; every edge
  is labeled `extracted` or `inferred`; portable `graph.json` (or
  documented equivalent) remains the interchange format.
- **Multi-modal scope**: Ingestion/query behavior states which modalities
  are in/out of this feature (code, docs, SQL, shell, PDF, image, media).
- **Incremental simplicity**: Default stack stays Python + NetworkX + local
  files; optional backends/servers justified in Complexity Tracking.
- **Schema/contract**: Changes to graph schema or CLI contracts include
  versioning/migration notes and tests where constitution requires them.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Grapheinstein default is a single Python CLI package.
  Delete unused options; delivered plan must not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project CLI (DEFAULT for Grapheinstein)
src/grapheinstein/
├── cli/                 # Typer command tree
├── ingest/              # Discovery, parsers, chunking
├── graph/               # NetworkX model, merge, persistence
├── extract/             # Entity/relation extraction (rule + local LLM)
├── query/               # explain, path, ask/subgraph
└── config/              # YAML config, cache, ignore rules

tests/
├── contract/            # CLI + graph.json schema contracts
├── integration/         # Fixture-project end-to-end
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
