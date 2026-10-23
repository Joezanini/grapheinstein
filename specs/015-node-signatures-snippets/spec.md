# Feature Specification: Code Node Signatures and Snippets

**Feature Branch**: `015-node-signatures-snippets`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "Graph nodes produced by grapheinstein should carry function/method signatures (params with types, return type) and a short code snippet (body, truncated to ~40 lines / ~2KB) for function, method, and class nodes, at least for TypeScript/JavaScript, Python and Dart. Today nodes only have name, file and line range, so downstream agents (Lursa MCP) can cite the right functions but have to guess arguments. Example target repo: Zanini-Software-LLC/clickup-kitchen-sink (e.g. src/client/index.ts ClickUpClient.createTask, setCustomFieldValue, createWebhook). New fields must be optional and backward compatible in the output JSON schema; there must be a config/flag to disable snippets and a size cap; never include secrets (skip snippet for files matching .env or secret patterns). Docs and a CHANGELOG entry (bump minor version) are required, plus unit tests for each language that are in place and passing. Open a PR to main and do not publish to PyPI."

## Clarifications

### Session 2026-10-23

- Q: How should each parameter record calling convention, beyond a single optional flag? → A: Each parameter has a name, a declared type when present, a kind of `positional`, `named`, `rest`, or `keywords`, and a `required` boolean. `rest` is a positional rest (`*args`, `...args`). `keywords` is a keyword rest (`**kwargs`). Dart required named parameters are `named` and required. Parameters with defaults or a language optional marker are not required.
- Q: How much of a declared type is kept when the type is a union, object type, generic, or array? → A: The type is the source type text with line breaks and repeated spaces collapsed to a single space. Unions, inline object types, generics, and arrays stay intact. The type is not simplified to a placeholder such as `any` or `Object`. The same rule applies to the return type. Example shape: `createTask(listId: string, data: { name: string; description?: string; ... })` keeps `string` and the object type, and `setCustomFieldValue`'s `value` keeps its union.
- Q: Does the graph schema version change when these optional fields are added? → A: The graph schema version stays `6.0.0`. Old graphs and new graphs both remain valid. The product version becomes `0.4.0`. Consumers read optional code-entity metadata keys `signature`, `parameters`, `return_type`, `snippet`, `snippet_truncated`, and `signature_truncated`. Absence means not captured. `parameters` entries use `name`, `type` (only when declared), `kind`, and `required`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Callable Signatures on Function and Method Nodes (Priority: P1)

An agent or developer indexes a local project and later reads the project graph to cite a function or method. For TypeScript, JavaScript, Python, and Dart, each function and method node carries the callable contract that is written in source: ordered parameters (name, declared type when present, passing kind, and whether the parameter is required), and the declared return type when present. A reader can tell what arguments to pass, and whether they are positional, named, rest, or keyword-rest, without opening the source file and guessing.

**Why this priority**: Downstream agents already locate the right function by name, file, and line range, then guess arguments. The signature is the missing fact that makes a citation usable.

**Independent Test**: Index a small fixture in each of TypeScript, JavaScript, Python, and Dart that defines a function or method with named parameters, at least one declared type, and a declared return type. Confirm the matching node exposes those parameter names, declared types, and the return type, while name, file, and line range remain present.

**Acceptance Scenarios**:

1. **Given** a TypeScript class method with typed positional parameters and a declared return type (as in a client method such as `createTask`, `setCustomFieldValue`, or `createWebhook`), **When** the project is indexed, **Then** the method node lists each parameter name, its declared type, passing kind `positional`, whether it is required, and the declared return type.
2. **Given** a Python function with annotated parameters and an annotated return type, including a keyword-only parameter or `*args` / `**kwargs` when present in the sample, **When** the project is indexed, **Then** the function node lists those parameter names, annotations, passing kind (`positional`, `named`, `rest`, or `keywords`), whether each is required, and the return annotation.
3. **Given** a Dart function or method with typed positional and named parameters, including at least one optional named parameter and one required named parameter, **When** the project is indexed, **Then** the node lists each parameter name, its declared type, passing kind (`positional` or `named`), whether it is required, and the declared return type.
4. **Given** a JavaScript function whose parameters and return type are not declared, **When** the project is indexed, **Then** the function node still lists parameter names and passing kind, and does not invent types or a return type.
5. **Given** a graph produced before this feature, **When** a consumer reads it, **Then** existing name, file, and line-range information remains valid and the absence of signature information is not an error.

---

### User Story 2 - Attach a Short Source Snippet to Function, Method, and Class Nodes (Priority: P1)

An agent citing a function, method, or class can read a short verbatim excerpt of that entity from the graph. The excerpt starts at the entity's declaration (including an attached decorator or annotation when one sits directly above it) and includes the body. It is truncated so a single node stays small: about 40 lines and about 2KB, whichever limit is reached first. The consumer can tell when the excerpt was cut short.

**Why this priority**: A signature says how to call the entity; a short excerpt shows the body the agent would otherwise have to open and guess through. Both are required for the stated agent workflow.

**Independent Test**: Index fixtures whose function, method, and class bodies exceed 40 lines and 2KB, and fixtures whose bodies are shorter. Confirm each of those node kinds has an excerpt within both limits, that short entities are not padded, and that truncated excerpts are marked truncated.

**Acceptance Scenarios**:

1. **Given** a function, method, or class whose source is shorter than both limits, **When** the project is indexed, **Then** the node's excerpt is the verbatim declaration-through-body text and is marked as not truncated.
2. **Given** an entity whose source exceeds 40 lines or 2KB, **When** the project is indexed, **Then** the excerpt stops at the first limit reached, stays within both limits, and is marked truncated.
3. **Given** a class and a method inside that class, **When** the project is indexed, **Then** the class excerpt covers the class and the method excerpt covers that method, each truncated on its own.
4. **Given** a function or method node that has a signature, **When** a snippet is stored, **Then** the signature information remains available even though the excerpt also shows source text.

---

### User Story 3 - Turn Snippets Off and Cap Their Size (Priority: P2)

An operator indexing a large or sensitive tree can turn snippet capture off for a run, or set a tighter size cap, without losing signatures. A saved local setting and a one-run control both work. When snippets are off, function, method, and class nodes still carry signatures where this feature extracts them, and they do not carry source excerpts.

**Why this priority**: Snippets copy source into the graph. Operators need an explicit off switch and a bound so graph size and source exposure stay under their control. Signatures are smaller and remain useful when excerpts are disabled.

**Independent Test**: Index the same fixture three times: default caps, a tighter cap, and snippets disabled. Compare the three graphs.

**Acceptance Scenarios**:

1. **Given** snippet capture is turned off in local configuration or by a one-run control, **When** indexing completes, **Then** function, method, and class nodes have no source excerpt, and function and method nodes still include their signatures.
2. **Given** the operator sets a lower line limit or a lower size limit, **When** indexing completes, **Then** every excerpt respects the tighter limit and truncation is marked when the source was cut.
3. **Given** no snippet setting is provided, **When** indexing completes, **Then** excerpts use the default limits of 40 lines and 2KB.

---

### User Story 4 - Keep Secrets Out of Snippets (Priority: P1)

A project that contains dotenv files or other secret-pattern files is indexed without copying those files' contents into node excerpts. Matching files still follow normal discovery rules (ignored files stay ignored). When such a file is indexed anyway, its function, method, and class nodes do not receive a source excerpt.

**Why this priority**: Graphs are shared with downstream agents. A snippet that copies a secret file would leak credentials into an artifact meant to be reused.

**Independent Test**: Index a fixture that contains a supported-language file whose path matches a secret pattern and a normal source file. Confirm the normal file's entities have excerpts and the secret-pattern file's entities do not.

**Acceptance Scenarios**:

1. **Given** a file named `.env` or `.env.local`, or a path whose file name matches a secret pattern (see Assumptions), **When** that file is included in an index, **Then** none of its nodes carry a source excerpt.
2. **Given** a normal source file that does not match a secret pattern, **When** indexing completes, **Then** its function, method, and class nodes still receive excerpts under the usual rules.
3. **Given** a secret-pattern file that also defines a function with a visible signature, **When** indexing completes, **Then** the signature may be present and the source excerpt is absent.

---

### User Story 5 - Document the Addition as a Minor Release (Priority: P2)

A maintainer or downstream agent author can read the product documentation and the changelog and learn what the new optional information is, how to turn excerpts off, what the default size cap is, and which paths are treated as secret files. The product version increases by a minor version. The change is not published to a package index as part of this work.

**Why this priority**: Agents and operators cannot rely on undocumented fields, and a minor version tells consumers the addition is backward compatible.

**Independent Test**: Read the changelog and the operator documentation after the change. Confirm the minor version bump, the optional fields, the off switch, the cap, and the secret-path rule are described, and that no package-index publish is required.

**Acceptance Scenarios**:

1. **Given** the feature is delivered, **When** a reader opens the changelog, **Then** a new minor version entry describes signatures and snippets as an addition.
2. **Given** the feature is delivered, **When** a reader opens the operator documentation, **Then** they can see the optional node information, the default cap, how to disable excerpts, and the secret-path rule.
3. **Given** an existing consumer that only reads name, file, and line range, **When** it loads a newly indexed graph, **Then** it can ignore the new information and continue to work.

---

### Edge Cases

- Parameter with no declared type: the name, passing kind, and required flag are kept; no type is invented.
- Declared type is a union, inline object, generic, or array: the collapsed source text of that type is kept on the parameter or return type. Nested fields inside an object type are not turned into extra parameters.
- Return type not declared: return type is omitted; it is not guessed from the body.
- Optional parameters (`?`, default values, Dart optional positional or named parameters): `required` is false. Dart `required` named parameters are `kind` `named` and `required` true. A default value that appears in source is included in the readable signature text and is not a reason to drop the signature. Passing kind is `positional` for ordinary and optional positional parameters, `named` for keyword-only and Dart named parameters, `rest` for `*args` and `...args`, and `keywords` for `**kwargs`.
- Overloaded declarations: the readable signature lists every overload in source order, then the implementation signature when it differs. The structured parameter list and return type describe the implementation signature when a body exists; otherwise they describe the first overload.
- `async` functions and methods: the readable signature preserves that the entity is async. Generator markers that are part of the declaration are preserved the same way.
- Decorators or annotations attached directly above the declaration: the excerpt starts at the first such decorator or annotation. The readable signature does not include decorator bodies.
- Class nodes: receive an excerpt and a short declaration line (name, type parameters, and base types when written). They do not receive a function-style parameter list. Constructors remain method nodes and follow the function/method signature rules.
- Entity shorter than the cap: excerpt is complete and marked not truncated.
- Entity that hits the line cap before the byte cap, or the byte cap before the line cap: excerpt stops at the first limit and is marked truncated. The excerpt never exceeds either limit.
- Snippets disabled: no excerpt and no truncation flag. Signatures remain.
- Secret-pattern file: no excerpt even if snippet capture is enabled. Signature rules still apply.
- Language outside TypeScript, JavaScript, Python, and Dart: this feature does not add signatures or excerpts. Existing name, file, and line-range behavior is unchanged. No signature or excerpt is fabricated.
- Entities the indexer does not already record (for example anonymous lambdas that are not nodes today): this feature does not create new node kinds for them.
- Syntax the extractor cannot confidently turn into a signature: the node keeps name, file, and line range; signature fields are omitted rather than partially guessed into a misleading contract.
- Empty body or abstract/interface declaration with no body: signature is still recorded; the excerpt is the declaration text within the cap.
- Re-index: a later index replaces prior signature and excerpt values for the same entities; disabling snippets on a later run removes excerpts from the newly written graph.
- Very large signature text: readable signature text and the structured parameter payload together stay within a 2KB bound. If the source signature is longer, it is truncated and marked so consumers know the contract text is incomplete.
- Graph commands that return code-entity nodes (index output and any later view that echoes those nodes) pass the new information through when it is present and do not strip it.

## Requirements *(mandatory)*

<!--
  Grapheinstein constitution constraints in scope for this feature:
  - Local-first / offline-capable defaults; no required cloud APIs
  - CLI index subcommand enrichment; portable graph.json for agent reuse
  - Typed graph edges with provenance unchanged (extracted | inferred)
  - Modality covered: code (TypeScript, JavaScript, Python, Dart)
  - Additive optional node information only; previously written graphs stay valid
-->

### Functional Requirements

- **FR-001**: For every function and method node extracted from TypeScript, JavaScript, Python, or Dart, the graph MUST include a readable signature and a structured parameter list when the declaration can be read confidently. Each parameter MUST include its name, its declared type when the source declares one, a passing kind of exactly `positional`, `named`, `rest`, or `keywords`, and whether the parameter is required. A declared return type MUST be included when the source declares one. `rest` means a positional rest parameter. `keywords` means a keyword rest parameter.
- **FR-002**: The system MUST NOT invent a parameter type or return type when the source does not declare one. When a type is declared, the recorded type MUST be the source type text with whitespace collapsed to single spaces, including unions, inline object types, generics, and arrays. The system MUST NOT replace that text with a simplified placeholder.
- **FR-003**: For every function, method, and class node in those four languages, the graph MUST include a verbatim source excerpt covering the attached decorators or annotations (when present) and the declaration through the body, unless excerpt capture is disabled or the file matches a secret pattern.
- **FR-004**: Each excerpt MUST be limited by both a line cap and a byte cap. The default caps MUST be 40 lines and 2KB (2048 bytes). The excerpt MUST stop at whichever cap is reached first and MUST record that it was truncated when either cap cuts the source.
- **FR-005**: Operators MUST be able to disable excerpt capture both in local configuration and with a one-run control. Disabling excerpts MUST NOT remove signatures.
- **FR-006**: Operators MUST be able to set a lower line cap and a lower byte cap. Excerpts MUST honor the effective caps for that run.
- **FR-007**: The system MUST NOT store a source excerpt for an entity whose file matches a secret pattern: a file named `.env` or starting with `.env.`, or a file name containing `secret`, `credential`, or `password` (case-insensitive), or a file ending in `.pem`, `.key`, or named `id_rsa`.
- **FR-008**: New signature and excerpt information MUST be optional. The graph schema version MUST remain `6.0.0`. Graphs written before this feature MUST remain valid. Consumers that only understand name, file, and line range MUST be able to ignore the new information. Required existing node fields and edge provenance rules MUST NOT change. On function and method nodes the optional keys are `signature` (readable signature text), `parameters` (ordered objects with `name`, optional `type`, `kind`, and `required`), `return_type` (only when declared), `signature_truncated` (only when the signature payload was cut to the 2KB bound), `snippet`, and `snippet_truncated`. On class nodes the optional keys are `signature` (declaration line), `snippet`, and `snippet_truncated`.
- **FR-009**: Languages other than TypeScript, JavaScript, Python, and Dart MUST keep today's node information. This feature MUST NOT fabricate signatures or excerpts for them.
- **FR-010**: Class nodes MUST receive an excerpt (subject to FR-003 through FR-007) and a short declaration line. They MUST NOT be given a function-style parameter list. Constructor methods MUST follow FR-001.
- **FR-011**: Overloaded function or method declarations MUST list every overload in source order in the readable signature, and the structured parameters and return type MUST describe the implementation signature when a body exists, otherwise the first overload.
- **FR-012**: Readable signature text, together with the structured parameter payload, MUST stay within 2KB. Longer source signatures MUST be truncated and marked incomplete rather than dropped silently or allowed to grow without bound.
- **FR-013**: Any user-facing or agent-facing view that returns code-entity nodes from the graph MUST preserve the new optional information when it is present.
- **FR-014**: Operator documentation MUST describe the optional signature and excerpt information, the default caps, how to disable excerpts, how to tighten caps, and the secret-path rule.
- **FR-015**: The changelog MUST record this addition under product version `0.4.0`. Publishing the package to a public package index is out of scope and MUST NOT be performed as part of this feature.
- **FR-016**: Automated checks MUST cover TypeScript, JavaScript, Python, and Dart, and MUST fail if a known function or method in that language loses its parameter names, declared types, declared return type, or a correctly capped excerpt. A separate check MUST fail if a secret-pattern file receives an excerpt.
- **FR-017**: Signature and excerpt capture MUST run locally with no network access and MUST NOT send source text to a remote service.

### Key Entities

- **Code entity node**: An existing function, method, or class in the project graph. Continues to carry name, language, file, and line range. Optionally carries `signature`, `parameters`, `return_type`, `signature_truncated`, `snippet`, and `snippet_truncated` as defined in FR-008.
- **Signature**: The callable contract of a function or method: `signature` text, an ordered `parameters` list (`name`, optional `type`, `kind`, `required`), and `return_type` when declared. For a class, `signature` is only a short declaration line.
- **Source excerpt**: Verbatim text of one function, method, or class in `snippet`, bounded by the active line and byte caps, with `snippet_truncated` set when the excerpt is present.
- **Snippet settings**: The operator's choice to capture excerpts or not, plus the active line cap and byte cap, from local configuration with an optional one-run override.
- **Secret-pattern file**: A file whose name matches the patterns in FR-007. Entities from that file do not receive source excerpts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a sample project for each of TypeScript, JavaScript, Python, and Dart, a reader can identify every declared parameter name, every declared parameter type, and the declared return type of a known function or method from the graph alone, in one lookup, without opening the source file.
- **SC-002**: For a known class method modeled on `createTask`, `setCustomFieldValue`, and `createWebhook`, the graph shows each positional parameter's name and full declared type text (including an inline object type or union when that is what the source writes) and the declared return type.
- **SC-003**: 100% of function, method, and class excerpts in an indexed sample are at most 40 lines and at most 2KB under default settings, and every excerpt that does not contain the full entity is visibly marked truncated.
- **SC-004**: With excerpts disabled, 100% of code-entity nodes in the sample have no source excerpt, and 100% of function and method nodes that had a readable signature with excerpts enabled still have that signature.
- **SC-005**: In a sample that mixes one normal source file and one secret-pattern file, 0% of nodes from the secret-pattern file contain a source excerpt, and the normal file's function, method, and class nodes still contain excerpts.
- **SC-006**: A consumer that only reads name, file, and line range can load both a previously indexed graph and a newly indexed graph without treating either as invalid.
- **SC-007**: A new reader can find the minor version note, the default cap, the disable control, and the secret-path rule in the changelog and operator documentation in under 5 minutes.

## Assumptions

- Downstream agents consume the portable project graph. Putting signatures and excerpts on the code-entity nodes is sufficient; a separate agent protocol is out of scope.
- The motivating repository `Zanini-Software-LLC/clickup-kitchen-sink` illustrates the TypeScript client methods agents need to cite. Verification uses local fixtures with the same method shapes. Cloning that repository is not required to build or test this feature.
- "Line range" today means the start line and, when known, the end line of the entity, plus the file path and name. This feature adds information; it does not remove or rename those facts.
- Optional means a field may be absent. Consumers treat absence as "not captured," not as a failed index.
- The graph schema version stays `6.0.0`. Adding optional metadata is not a breaking graph change: required fields, edge types, and provenance values stay as they are, so previously written graphs and older consumers remain valid. The loader already accepts only `6.0.0`, so changing that version would reject either old or new graphs. The product version moves from `0.3.0` to `0.4.0`.
- Canonical optional metadata keys are `signature`, `parameters`, `return_type`, `signature_truncated`, `snippet`, and `snippet_truncated`. Parameter objects use `name`, `type`, `kind`, and `required`.
- Default excerpt limits are 40 lines and 2048 bytes, measured on the excerpt text in UTF-8. A configurable cap may be lower. It may not be raised above these defaults in this feature, so the stated bound always holds.
- Readable signature text plus structured parameters share a separate 2KB bound and do not count against the excerpt budget.
- Secret handling is path-based, as requested. This feature does not scan ordinary source files for credential-shaped string literals, and it does not redact default-argument literals in non-secret files.
- Ignored files continue to be skipped by discovery. The secret-pattern rule applies only to files that are actually indexed.
- Java, Go, Rust, C++, SQL, documentation, and media nodes are unchanged.
- Excerpt capture has no effect on edge types or provenance labels.
- Publishing to a package index, including PyPI, is out of scope.
- One-run control overrides the saved local configuration when both are present.
- Constructor nodes already recorded as methods receive method signatures. Class declaration lines do not list constructor parameters.
- `async` is part of the readable signature. Decorator arguments are not.
- Automated checks are part of the existing test suite for the project and must pass before the feature is considered done. They are local and do not require network access.
