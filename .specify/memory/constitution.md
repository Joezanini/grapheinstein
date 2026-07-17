<!--
Sync Impact Report
- Version change: (template placeholders) → 1.0.0
- Modified principles:
  - [PRINCIPLE_1_NAME] → I. Local-First & Offline Operation
  - [PRINCIPLE_2_NAME] → II. CLI-First Agent Interface
  - [PRINCIPLE_3_NAME] → III. Provenance-Labeled Knowledge Graph
  - [PRINCIPLE_4_NAME] → IV. Multi-Modal Project Ingestion
  - [PRINCIPLE_5_NAME] → V. Incremental Simplicity & Extensibility
- Added sections:
  - Architecture & Technology Constraints
  - Development Workflow
  - Governance (filled)
- Removed sections: none (template placeholders replaced)
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ updated (Constitution Check gates)
  - .specify/templates/spec-template.md ✅ updated (mandatory constraints note)
  - .specify/templates/tasks-template.md ✅ updated (graph/parser/query task guidance)
  - .specify/templates/commands/*.md ⚠ N/A (directory not present)
  - README.md / docs/quickstart.md ⚠ pending (not yet created)
- Follow-up TODOs: none
-->

# Grapheinstein Constitution

## Core Principles

### I. Local-First & Offline Operation

Grapheinstein MUST run entirely on the user's machine without required
cloud services. Indexing, embedding, entity extraction, and query MUST
work offline when local models (e.g., Ollama, LM Studio, local
sentence-transformers) are configured. The tool MUST respect `.gitignore`
(and equivalent ignore rules) during project walks. Model paths, cache
directories, and parser options MUST be configurable via local config
(YAML or equivalent). Intermediate artifacts MUST be cacheable on disk
so re-indexing can skip unchanged work.

**Rationale**: The product is a local-first knowledge tool; users and
open-source communities MUST be able to map private or air-gapped
codebases without sending content to remote APIs.

### II. CLI-First Agent Interface

All core capability MUST be available through a single `grapheinstein`
CLI entrypoint with clear subcommands. The CLI MUST accept a project
path (e.g., `.`) and produce a portable `graph.json` (or equivalent
documented schema) suitable for later consumption by AI agents.
Slash-command and MCP integrations MUST reuse the same library/API as
the CLI; they MUST NOT fork divergent indexing or query semantics.
Human-readable progress/errors go to stderr; machine-consumable results
(graph exports, subgraphs, path answers) MUST support structured output
(JSON) on stdout or a declared file path.

**Rationale**: CLI and assistant slash commands are equal first-class
surfaces; one implementation keeps agent behavior predictable.

### III. Provenance-Labeled Knowledge Graph

The primary artifact is a queryable knowledge graph of the target
project. Nodes MUST represent entities (files, directories, functions,
classes, concepts, tables, media assets, etc.) with metadata such as
path, type, language, and chunk identity where applicable. Edges MUST
use explicit relationship types (e.g., `imports`, `calls`, `references`,
`contains`, `mentions`, `depends_on`). Every edge MUST carry a
provenance label of exactly `extracted` (derived directly from
parsers/AST/regex/metadata) or `inferred` (derived from LLM, similarity,
or other heuristic reasoning). Consumers MUST be able to filter or
weight by provenance. Persistence MUST use a documented portable format
(`graph.json` via NetworkX node-link data by default) so graphs can be
collected into libraries for MCP-hosted troubleshooting agents.

**Rationale**: Agents need typed structure and trust signals; unlabeled
edges make debugging and OSS install support unreliable.

### IV. Multi-Modal Project Ingestion

Indexing MUST understand more than source code. Parsers MUST cover
multi-language code (Tree-sitter or equivalent), documentation
(Markdown and similar), SQL, shell scripts, PDFs, images (metadata/OCR
as configured), and audio/video (transcription via local tooling as
configured). Unsupported or failed files MUST be recorded without
aborting the whole index when possible. Plugin-style parsers SHOULD be
the extension point for new formats.

**Rationale**: Real projects mix code, docs, and media; a code-only
graph cannot answer install and ops questions.

### V. Incremental Simplicity & Extensibility

Deliver working CLI increments phase by phase; each phase MUST leave a
usable tool. Prefer NetworkX and local files over external graph
databases until a concrete need appears. Prefer rule-based extraction for
code structure and reserve local LLMs for concept/relation inference.
Do not add cloud backends, hosted vector DBs, or Neo4j as required
dependencies for the default path. Complexity (optional backends,
HTTP servers, MCP hosting) MUST be justified against a simpler local
alternative and documented in Complexity Tracking when it violates
these defaults.

**Rationale**: A thin, correct local core beats an overbuilt platform;
`graph.json` libraries and MCP hosting come after the CLI is solid.

## Architecture & Technology Constraints

- **Language**: Python 3.11+ with a packaging layout suitable for a
  console script (`grapheinstein`).
- **CLI framework**: Typer (preferred) or Click; one command tree with
  subcommands for index/build, explain, path, and ask/query.
- **Graph core**: NetworkX for construction, traversal, and
  serialization; optional later backends MUST remain behind an interface
  and MUST NOT break `graph.json` portability.
- **Parsing**: Tree-sitter for multi-language AST; dedicated libraries
  for PDF/media/OCR/transcription as phased features; pathspec/git for
  ignore-aware discovery.
- **Embeddings & LLM**: Local-only by default (sentence-transformers
  and/or Ollama/LM Studio); remote APIs are opt-in and MUST never be
  required for core operation.
- **Query surface (minimum)**:
  - Explain one concept (neighborhood / definition subgraph)
  - Find path between two concepts
  - Answer a plain-language question by returning a relevant subgraph
- **Config**: YAML (or equivalent) for ignore overrides, model paths,
  parser toggles, and cache locations.
- **Downstream use**: Portable graphs are intended for a future MCP
  server that serves a library of project graphs for OSS install
  troubleshooting; that server is an extension, not a Phase-1
  dependency of the CLI.

## Development Workflow

- Use Speckit phases: specify → plan → tasks → implement; prefer
  vertical slices that end in a working CLI command.
- Recommended build order MUST guide prioritization unless a spec
  explicitly revises it: CLI skeleton → file/directory graph →
  multi-language code → docs/non-code → media → entity/relation
  extraction with provenance → persistence → query commands →
  config/cache/polish → slash-command/MCP hooks.
- Tests: unit tests for parsers, graph merge, and provenance labeling;
  integration tests for CLI end-to-end on fixture projects. Tests are
  required when a feature touches graph schema, provenance, or CLI
  contracts.
- Schema changes to `graph.json` are breaking changes: bump the
  documented schema version, provide migration notes, and keep older
  readers from silently misreading provenance or edge types.
- Do not expand scope into hosted platforms, UI dashboards, or
  mandatory cloud AI until the local CLI query loop is complete.

## Governance

This constitution supersedes informal plans and chat proposals when they
conflict. Amendments MUST update `.specify/memory/constitution.md`, bump
`CONSTITUTION_VERSION` using semantic versioning (MAJOR for incompatible
principle removals/redefinitions, MINOR for new principles or materially
expanded guidance, PATCH for clarifications), set **Last Amended** to
the amendment date (ISO 8601), and propagate changes through Speckit
templates (`plan-template`, `spec-template`, `tasks-template`) and any
runtime guidance docs.

All plans MUST pass the Constitution Check gates before Phase 0
research proceeds and again after Phase 1 design. Reviews and
implementations MUST verify: local-first defaults, CLI/API parity,
typed edges with `extracted`/`inferred` provenance, and incremental
scope discipline. Unjustified complexity MUST be recorded in the plan's
Complexity Tracking table or the change MUST be rejected.

**Version**: 1.0.0 | **Ratified**: 2026-07-16 | **Last Amended**: 2026-07-16
