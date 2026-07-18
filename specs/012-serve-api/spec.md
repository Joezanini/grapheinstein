# Feature Specification: Serve & Agent API

**Feature Branch**: `012-serve-api`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Add optional: grapheinstein serve --port 8000 (FastAPI) exposing /index, /query endpoints. Or simple Python API for Cursor slash-command integration (function that takes folder and returns graph). Document how to call from other agents."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Call Indexing from Another Agent via Python (Priority: P1)

An AI coding agent (for example a Cursor slash-command handler or another local assistant) needs a project knowledge graph without shelling out to the CLI. It imports Grapheinstein’s public Python API, passes a project folder path, and receives a portable graph result it can reason over or write to disk—using the same indexing semantics as `grapheinstein index`.

**Why this priority**: Constitution requires slash-command and MCP-style integrations to reuse the same library as the CLI. A stable callable API is the minimum surface that unblocks agent integration without introducing a long-lived process.

**Independent Test**: From a small Python script or test, call the public index function on a fixture project folder and assert a valid portable graph is returned (or written) with the same essential structure as a CLI index of that folder.

**Acceptance Scenarios**:

1. **Given** Grapheinstein is installed in the agent’s environment, **When** the agent calls the documented public function with a valid project folder path, **Then** it receives (or can persist) a portable project graph consistent with CLI indexing of that folder.
2. **Given** the agent supplies an output path or equivalent option, **When** indexing completes successfully, **Then** a `graph.json` (or documented equivalent) is written there and the function returns a success result that includes enough information to locate or use the graph.
3. **Given** the project path does not exist or is not readable, **When** the agent calls the index function, **Then** the call fails with a clear, structured error the agent can surface (not a silent empty graph).
4. **Given** optional indexing settings (config path, ignore/cache-related options already supported by the CLI), **When** the agent passes those options through the Python API, **Then** behavior matches the equivalent CLI flags/config for the same project.

---

### User Story 2 - Ask Questions via Python Without Leaving the Agent Process (Priority: P1)

After a graph exists (just indexed or loaded from disk), the agent asks a natural-language question through the public Python API and receives a structured answer with citations/subgraph information equivalent to the CLI query experience—so slash commands can answer “what does auth do?” without spawning a separate CLI process.

**Why this priority**: Index-only integration is incomplete for agent workflows; query is the other half of the agent loop and must share CLI semantics.

**Independent Test**: With a known fixture graph, call the public query function with a fixed question and assert the returned answer structure matches the documented query-answer contract used by the CLI (answer text, citations or supporting nodes/edges as defined today).

**Acceptance Scenarios**:

1. **Given** a valid portable graph for a project, **When** the agent calls the documented query function with a question string, **Then** it receives a structured answer suitable for machine consumption (same information the CLI query would produce for that graph and question).
2. **Given** the agent points at a graph file path rather than an in-memory graph, **When** query runs, **Then** the graph is loaded and queried without requiring a separate CLI invocation.
3. **Given** the question cannot be answered from the graph (empty/sparse graph or no relevant evidence), **When** query runs, **Then** the result clearly indicates low/no evidence rather than inventing unsupported claims.
4. **Given** invalid inputs (missing graph path, unreadable graph file), **When** query is invoked, **Then** the call fails with a clear structured error.

---

### User Story 3 - Optional Local HTTP Serve for Index and Query (Priority: P2)

A developer or local tool starts an optional local HTTP service with `grapheinstein serve` (default port 8000, configurable via `--port`). Other local clients POST to `/index` and `/query` to trigger the same operations as the Python API/CLI, receiving structured JSON responses—useful when the caller prefers HTTP over importing Python.

**Why this priority**: HTTP is convenient for heterogeneous clients, but it is optional complexity; the Python API alone already satisfies slash-command integration. Serve wraps the same core operations.

**Independent Test**: Start serve on a free local port; POST a valid index request for a fixture folder and receive a success JSON payload referencing or containing the graph; POST a query against that graph and receive a structured answer JSON; stop the server cleanly.

**Acceptance Scenarios**:

1. **Given** Grapheinstein is installed with the optional serve capability available, **When** the user runs `grapheinstein serve --port 8000` (or another free port), **Then** a local HTTP service listens on that port and remains responsive until stopped.
2. **Given** the service is running, **When** a client sends a valid request to `/index` with a project folder path, **Then** the service indexes using the same semantics as the CLI/Python API and returns a structured success response (graph location and/or graph payload as documented).
3. **Given** the service is running and a graph is available, **When** a client sends a valid request to `/query` with a question (and graph reference as documented), **Then** the service returns a structured answer consistent with CLI/Python query.
4. **Given** a request with missing required fields or an invalid path, **When** `/index` or `/query` handles it, **Then** the response is a clear error status with a machine-readable message (not a generic crash).
5. **Given** the user runs `grapheinstein serve --help`, **Then** help documents purpose, `--port`, and points to agent-integration docs for request/response shapes.

---

### User Story 4 - Documented Agent Integration Playbook (Priority: P2)

An author of Cursor slash commands, MCP tools, or other agents reads project documentation that shows exactly how to call Grapheinstein—Python import examples, optional HTTP examples, expected inputs/outputs, and parity notes with CLI commands—so they can integrate without reverse-engineering the package.

**Why this priority**: The feature fails if agents cannot discover the contract; documentation is part of the deliverable, not an afterthought.

**Independent Test**: Follow the documented Python path and (if serve is installed) the HTTP path against a fixture project and obtain a graph and a query answer without consulting source code beyond the docs.

**Acceptance Scenarios**:

1. **Given** the published agent-integration documentation, **When** a reader follows the Python API section, **Then** they can index a folder and query a graph with copy-pasteable examples that match the shipped public API.
2. **Given** the same documentation, **When** a reader follows the optional HTTP section, **Then** they see how to start `serve`, which endpoints to call (`/index`, `/query`), example request bodies, and example success/error responses.
3. **Given** the documentation, **When** a reader compares surfaces, **Then** it states that CLI, Python API, and HTTP serve share the same indexing and query semantics (no divergent “HTTP-only” behavior).
4. **Given** optional serve dependencies are not installed, **When** a reader checks the docs, **Then** they learn how to install/enable serve and that the Python API remains available without the HTTP stack.

---

### Edge Cases

- Serve port already in use: fail at startup with a clear error naming the port; do not silently bind a different port.
- Concurrent `/index` requests for different folders: MUST NOT corrupt each other’s outputs; document whether requests are serialized or isolated.
- Very large projects: long-running `/index` MAY take minutes; clients MUST receive either a completed result or a clear timeout/error—no silent hang without feedback (progress MAY be limited over HTTP).
- Path traversal or absolute paths outside the intended project: treat paths as filesystem paths the local user can already access; serve is a local tool, not a multi-tenant remote API.
- Query without a prior successful index / missing graph reference: clear error asking for a graph path or prior index result.
- Optional HTTP dependencies missing: `grapheinstein serve` fails with an actionable install hint; core CLI and Python API remain usable.
- Stopping the server (Ctrl+C / SIGTERM): process exits cleanly without leaving orphaned workers that continue indexing indefinitely after shutdown is requested (in-flight work MAY be aborted).

## Requirements *(mandatory)*

<!--
  Grapheinstein constitution constraints in scope for this feature:
  - Local-first / offline-capable defaults; no required cloud APIs
  - CLI-first; slash/MCP/HTTP MUST reuse the same library/API as the CLI
  - Portable graph.json for agent reuse
  - Incremental simplicity: HTTP serve is optional; Python API is the primary agent surface
  - No mandatory hosted backends or remote multi-tenant auth model
-->

### Functional Requirements

- **FR-001**: The system MUST expose a public Python API function (or small set of functions) that accepts a project folder path and performs indexing with the same semantics as the CLI index command, returning or persisting a portable project graph.
- **FR-002**: The system MUST expose a public Python API function that accepts a natural-language question and a graph reference (in-memory and/or filesystem path) and returns a structured query answer with the same semantics as the CLI query command.
- **FR-003**: Python API errors MUST be distinguishable failures (exceptions or structured error results) with human-readable messages suitable for agent display; they MUST NOT return a fake empty success graph on hard failures.
- **FR-004**: The system MUST provide an optional CLI subcommand `grapheinstein serve` that starts a local HTTP service exposing at least `/index` and `/query` endpoints backed by the same core operations as the Python API.
- **FR-005**: `grapheinstein serve` MUST accept `--port` (default **8000**) to select the listen port.
- **FR-006**: By default, the HTTP service MUST bind only to the local machine (loopback), not to all network interfaces, unless the user explicitly opts into a broader bind address documented as advanced/unsafe for untrusted networks.
- **FR-007**: The `/index` endpoint MUST accept a project folder path (and documented optional settings) and return a structured JSON success or error response.
- **FR-008**: The `/query` endpoint MUST accept a question and a graph reference as documented and return a structured JSON answer or error response consistent with the CLI/Python query contract.
- **FR-009**: Serve and the Python API MUST NOT introduce a second indexing or query implementation with different semantics from the CLI; they MUST call shared core operations.
- **FR-010**: HTTP serve dependencies MUST be optional: installing or using core CLI/Python API MUST NOT require the HTTP stack; invoking `serve` without those dependencies MUST fail with an actionable message.
- **FR-011**: The project MUST ship agent-integration documentation covering: (a) Python API usage for Cursor slash-command style callers, (b) optional HTTP `serve` usage with `/index` and `/query` examples, (c) parity statement with CLI commands, (d) how to enable optional serve dependencies.
- **FR-012**: `grapheinstein serve --help` MUST document the command purpose, `--port`, default port, and where to find agent-integration documentation.
- **FR-013**: The HTTP surface MUST NOT require cloud accounts, remote auth providers, or network access beyond the local machine for default operation.
- **FR-014**: Machine-consumable responses (Python return values and HTTP JSON bodies) MUST remain separate from human diagnostic logging; logs/progress MUST NOT corrupt structured payloads.

### Key Entities

- **Agent Index Request**: Project folder path plus optional settings (config path, output location) used to build or refresh a portable graph.
- **Agent Query Request**: Natural-language question plus graph reference (path or prior index result) used to produce a structured answer.
- **Portable Project Graph**: Existing Grapheinstein graph artifact (`graph.json` or documented equivalent) with typed nodes/edges and provenance labels; unchanged schema unless a separate schema feature revises it.
- **Structured Query Answer**: Existing query-answer shape (answer text plus citations / supporting graph evidence as already defined by the query feature).
- **Local Serve Session**: Optional short-lived local HTTP listener bound to a port, exposing `/index` and `/query` until the user stops it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An agent developer can index a small fixture project through the Python API and obtain a usable portable graph in under 5 minutes of following the documentation (excluding model download time on first use).
- **SC-002**: For the same fixture project and question, Python API query and CLI query produce answers with the same cited evidence set (same supporting node/edge identities), demonstrating semantic parity.
- **SC-003**: With optional serve enabled, a local client can complete one `/index` and one `/query` round-trip against a fixture project without using the CLI, and receive structured success responses in both cases.
- **SC-004**: 100% of documented Python and HTTP examples in the agent-integration docs succeed against the shipped package on a clean install (core for Python; optional extras for HTTP).
- **SC-005**: When optional HTTP dependencies are absent, core CLI commands and the Python index/query API remain usable; only `serve` fails with a clear install hint.
- **SC-006**: Default serve binding rejects connection attempts from non-local clients (loopback-only default), protecting users who start serve without intending remote exposure.

## Assumptions

- Both surfaces ship in this feature: Python API is required (P1); HTTP `serve` is optional but in scope (P2), not an either/or choice. The user’s “or” is interpreted as two complementary integration paths.
- The optional HTTP service is a thin local wrapper around the shared core; planning may choose a common local web-framework stack, but the product contract is endpoint behavior and CLI/Python parity—not a specific framework brand.
- Serve is a **local developer/agent convenience**, not a multi-user production API: no authentication, TLS, or rate limiting in v1; loopback bind is the security boundary.
- Existing index/query CLI contracts and `graph.json` / query-answer shapes are reused; this feature does not redefine graph schema or hybrid-query ranking.
- Cursor slash-command integration means calling the Python API from the agent host process (or optionally HTTP); shipping a Cursor marketplace plugin is out of scope.
- Full MCP server hosting of a graph library remains a later extension; this feature only documents and enables programmatic/local-HTTP access to index and query.
- Default port is **8000** when `--port` is omitted, matching the user request.
- Path and explain CLI commands are not required as HTTP endpoints in this feature; only `/index` and `/query` are mandatory. Additional endpoints MAY be added later without blocking this spec.
