# Feature Specification: Large Repo Guards

**Feature Branch**: `014-large-repo-guards`

**Created**: 2026-07-19

**Status**: Draft

**Input**: User description: "From the OpenClaw run log for google-api-python-client: preflight passed (634 MB / 8,796 files under 800 MB / 20k), code-only mode timed out after 1200s with no graph.json. Repo makeup is mostly generated docs HTML and discovery JSON with only ~87 Python files. Root cause: code-only still inventories every file, then reference scanning reads each file's text against every unique basename (~76M searches / ~635 MB read). Existing guardrails (byte/file caps, timeout, reject policy) do not estimate reference-scan cost, burn the full timeout with no output, and lack default ignores for generated docs. Priority: (1) scope code-only away from docs dumps, (2) bound reference scanning, (3) smarter preflight on estimated scan cost / non-code share, (4) defer path sharding/merge to intentional full-tree cases."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Code-Only Indexes the Real Package, Not Doc Dumps (Priority: P1)

An operator (or automated wrapper) indexes a large open-source Python package in code-only mode. The repository contains a small amount of source code and a huge tree of generated documentation HTML and discovery/cache JSON. Without special flags, indexing focuses on the code (and other code-like assets) and skips well-known generated documentation and discovery-cache areas by default. The run finishes with a usable portable graph instead of hanging until timeout.

**Why this priority**: Scoping before any heavier work is the highest-leverage fix; the same repo that currently burns twenty minutes becomes a small, finishable job when generated docs are out of scope for code-only.

**Independent Test**: Point indexing at a fixture that mimics a tiny source tree plus a large `docs/` / `docs/dyn/` / discovery-cache tree; run code-only indexing with defaults; confirm generated-doc and discovery-cache paths are absent from the graph and that a graph file is written successfully.

**Acceptance Scenarios**:

1. **Given** a project whose bulk is under generated documentation or discovery-cache paths and whose source lives in a small code package tree, **When** the user runs code-only indexing with default ignores, **Then** those generated documentation and discovery-cache paths are excluded from the inventory and from reference linking, and a graph file is written.
2. **Given** the same project, **When** the user explicitly opts in to include generated documentation or discovery-cache paths, **Then** those paths may be included (subject to other limits), and the run does not silently re-apply the default exclusions.
3. **Given** a normal project without those generated trees, **When** the user runs code-only indexing, **Then** ordinary source and project docs that are not on the default exclusion list remain indexable as today.

---

### User Story 2 - Reference Linking Stays Bounded (Priority: P1)

After inventory, the product builds cross-file reference links by looking for mentions of other indexed files' names inside file contents. For large or mostly non-code trees, that step MUST NOT read and scan unbounded amounts of text across every inventoried file against every unique filename. Reference linking skips files that are not eligible for content scanning (non-code in code-only mode, oversize/skipped files, and content beyond a documented size cap), so CPU stays proportional to the code being linked rather than to documentation dumps.

**Why this priority**: Even if inventory is large, unbounded reference scanning is what pegs CPU and burns the full timeout; bounding it is required for reliability on real OSS checkouts.

**Independent Test**: Build a fixture with many large non-code text files that mention many unique basenames, plus a few small code files with genuine mentions; run code-only indexing; confirm reference edges exist among eligible code files and that the large non-code / oversize files are not fully scanned for references.

**Acceptance Scenarios**:

1. **Given** code-only mode, **When** reference linking runs, **Then** only files treated as code (or otherwise eligible for content linking in that mode) are scanned for basename mentions.
2. **Given** a file already skipped as oversize or otherwise excluded from content processing, **When** reference linking runs, **Then** that file is not fully read again for basename scanning.
3. **Given** an eligible file whose content exceeds the documented scan size cap, **When** reference linking runs, **Then** at most the capped prefix (or documented equivalent bound) is considered for mentions, and indexing still completes.
4. **Given** a small fixture where file A’s eligible content contains a whole-token mention of unique file B, **When** indexing completes, **Then** a `references` edge from A to B is still produced (existing linking semantics preserved for eligible files).

---

### User Story 3 - Preflight Rejects Hopeless Jobs Early (Priority: P2)

Before a long indexing run, the product (or its wrapper preflight) estimates not only total size and file count, but also whether reference-scan work or non-code share would make a successful timely run unlikely. When estimated cost or non-code dominance exceeds documented thresholds, the run is rejected promptly with a clear message that explains why and how to narrow scope or override—rather than consuming the entire timeout window and returning no graph.

**Why this priority**: Early reject turns a twenty-minute empty failure into a seconds-scale actionable failure; operators and agents can adjust scope immediately.

**Independent Test**: Present a tree that passes crude size/count caps but fails the new cost or non-code-share estimate; confirm reject within a short wall-clock bound and that no graph is claimed as success; present an override path and confirm indexing may proceed when explicitly allowed.

**Acceptance Scenarios**:

1. **Given** a project whose estimated reference-scan cost exceeds the documented threshold (even if byte and file-count caps pass), **When** preflight or indexing starts without an override, **Then** the run fails fast with a human-readable explanation citing estimated cost (or non-code share) and suggested remedies (narrow path, code-only ignores, raise override).
2. **Given** a project whose inventoried non-code share is high relative to code under code-only intent, **When** preflight runs without override, **Then** the run is rejected or requires explicit confirmation/override before continuing.
3. **Given** an explicit override for large-repo / high-cost policy, **When** the user re-runs, **Then** indexing proceeds subject to remaining hard limits (timeout, max bytes, max files) and bounded reference scanning.
4. **Given** a modest code-centric project under all thresholds, **When** preflight runs, **Then** indexing proceeds without requiring an override.

---

### User Story 4 - Timeouts Fail Clearly Without Fake Success (Priority: P3)

If a run still hits a time limit after scoping and bounds, the operator learns quickly that the job did not produce a usable graph. The product MUST NOT present a timed-out run as a successful index, and SHOULD surface how far it got (e.g., inventory done, linking incomplete) when such progress information is available.

**Why this priority**: Avoids silent empty outcomes for agents/wrappers that currently wait the full window and get nothing actionable.

**Independent Test**: Force a short timeout on a job that cannot finish; confirm non-zero failure, no successful graph claim, and a clear timeout/partial-progress message.

**Acceptance Scenarios**:

1. **Given** indexing exceeds the configured time limit, **When** the process stops, **Then** the exit status indicates failure and no graph file is reported as a successful complete index.
2. **Given** progress information is available at timeout, **When** the failure is reported, **Then** the message indicates which major phase was in progress or last completed (e.g., discovery vs reference linking).

---

### Edge Cases

- User points the project root at a documentation-only tree in code-only mode: succeed with an empty or minimal code graph, or fail with a clear “no eligible code” message—never hang scanning docs.
- User disables default generated-doc ignores: size/count and scan-cost preflight still apply; unbounded doc dumps may still be rejected early.
- Ambiguous basenames among remaining eligible files: keep existing unambiguous-match rules; do not weaken correctness to gain speed.
- Override flags conflict with hard safety caps (max total bytes / max file count): hard caps still win; override only relaxes advisory cost/share gates.
- Mixed tree (code + legitimate project Markdown outside excluded paths): non-excluded docs remain subject to mode rules (code-only vs full); only default generated/cache paths are auto-excluded.
- Estimated cost is slightly under threshold but runtime is still slow: timeout and bounded scanning remain the backstop; sharding/merge is out of scope for this feature.

## Requirements *(mandatory)*

<!--
  Grapheinstein constitution constraints in scope for this feature:
  - Local-first / offline-capable defaults; no required cloud APIs
  - CLI (and same-API consumers) remain the interface; portable graph.json for agents
  - Typed edges with provenance: references remain extracted where applicable
  - Code modality primary for code-only; docs dumps must not dominate by default
  - Respect ignore rules; extend defaults for generated documentation/cache paths
-->

### Functional Requirements

- **FR-001**: In code-only mode, the system MUST apply default path exclusions for well-known generated documentation and discovery/cache trees (at minimum patterns covering `docs/dyn/`, top-level generated `docs/` dumps of that class, and discovery-cache style JSON corpora), so those paths are omitted from inventory and from reference linking unless the user explicitly opts in.
- **FR-002**: Users MUST be able to override or disable those default exclusions for a run when they intentionally want generated documentation or discovery caches in the graph.
- **FR-003**: Reference linking MUST only scan content of files eligible for content-based linking in the active mode (code-only: code-eligible files; not excluded, not skipped-as-oversize).
- **FR-004**: Reference linking MUST NOT re-read or fully scan files already marked skipped/oversize for content processing.
- **FR-005**: Reference linking MUST cap the amount of text considered per eligible file to a documented maximum so a single huge file cannot dominate scan cost.
- **FR-006**: Preflight (or equivalent gate before heavy work) MUST estimate reference-scan cost using inventory factors that reflect work scale (at least: count of files eligible to scan, count of unique linkable basenames, and/or total eligible text volume)—not only total bytes and file count of the whole tree.
- **FR-007**: When estimated scan cost or inventoried non-code share exceeds documented thresholds, the system MUST reject the run by default with a clear message and remediation hints, unless the user supplies an explicit override.
- **FR-008**: Existing hard limits (max total bytes, max file count, timeout, large-repo reject policy) MUST remain in force; this feature adds cost/share estimation and scoping—it MUST NOT remove those guards.
- **FR-009**: A timed-out or rejected run MUST NOT be reported as a successful complete index; absence of a usable graph MUST be explicit to the operator/agent.
- **FR-010**: On timeout, the system SHOULD report which major indexing phase was last completed or in progress when that information is available.
- **FR-011**: Whole-token basename reference semantics and `extracted` provenance for those edges MUST remain unchanged for files that remain eligible to scan.
- **FR-012**: Path sharding, partial-index merge, and resume-across-shards are OUT OF SCOPE for this feature; they MAY be specified later for intentional full-tree documentation graphs.

### Key Entities

- **Inventory Scope**: The set of paths included after ignore rules and mode-specific default exclusions; drives what becomes nodes.
- **Scan Eligibility**: Whether a file’s contents may be read for reference linking (mode, size, skip flags, text cap).
- **Scan Cost Estimate**: Preflight metric derived from eligible file count, unique basenames, and/or eligible text volume used to accept or reject before heavy linking.
- **References Edge**: Directed, provenance-labeled link from an eligible mentioning file to an unambiguously resolved indexed target; unchanged semantics for eligible files.
- **Large-Repo Policy Decision**: Accept, reject, or accept-with-override outcome from size, count, cost, and non-code-share gates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a fixture modeled after google-api-python-client proportions (thousands of generated doc/cache files, under 100 source files), default code-only indexing completes with a written graph in under 2 minutes on a typical developer laptop, without requiring a custom path allowlist beyond defaults.
- **SC-002**: For that same fixture under defaults, at least 95% of generated documentation and discovery-cache files are absent from the graph inventory.
- **SC-003**: Reference linking never fully scans non-eligible or oversize-skipped files; in a controlled fixture, 100% of such files contribute zero reference-scan reads of their full contents.
- **SC-004**: Projects that pass crude size/count caps but exceed scan-cost or non-code-share thresholds are rejected in under 30 seconds with an explanatory message (no full timeout wait).
- **SC-005**: Timed-out runs produce a non-success outcome 100% of the time (no successful complete graph claim).
- **SC-006**: On a small code fixture with known basename mentions among eligible files, reference edge recall matches pre-feature behavior for those eligible pairs (no correctness regression on the happy path).

## Assumptions

- “Code-only” means operators primarily want package source structure and references, not generated API HTML or discovery JSON corpora.
- Default exclusions target generated/cache documentation patterns exemplified by `docs/dyn/` and discovery caches; ordinary hand-written project docs outside those patterns remain subject to existing mode rules.
- Wrapper and core share the same policy intent: early reject and clear messaging are acceptable; producing a partial graph on timeout is not required in this increment.
- Hard numeric defaults for scan-cost and non-code-share thresholds will be chosen during planning from fixture measurements; stakeholders care that thresholds reject the google-api-python-client class of failure and allow normal small/medium repos.
- Lowering global max-bytes / max-files defaults is optional polish; cost estimation plus scoping is the primary fix.
- Job sharding/resume is deferred; this feature succeeds if scoped code-only runs finish without it.
- Local-first operation is unchanged: no cloud services required for guards or preflight.
