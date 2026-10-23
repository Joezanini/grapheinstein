# Research: Code Node Signatures and Snippets

## R1. Where signatures come from

**Decision**: Build signatures from the Tree-sitter nodes the extractor already visits for Python, JavaScript, TypeScript, and Dart. Do not add a second parser or an LLM pass.

**Rationale**: Those four grammars expose parameter lists and return types as syntax nodes. The current `CodeEntity` only stores kind, name, lines, and parent class. Probing the installed grammars shows:

- Python `function_definition` has `parameters` (`typed_parameter`, `typed_default_parameter`, `list_splat_pattern` for `*args`, `dictionary_splat_pattern` for `**kwargs`) and a trailing `type` node for the return annotation. Decorators wrap the function in `decorated_definition`.
- JavaScript `function_declaration` / `method_definition` use `formal_parameters` (`identifier`, `assignment_pattern` for defaults, `rest_pattern`). There is no type node.
- TypeScript uses the same shapes plus `required_parameter`, `optional_parameter`, and `type_annotation` (unions, `generic_type`, inline object types). Overloads are preceding `function_signature` siblings that the current query does not turn into nodes.
- Dart splits a function into `function_signature` plus a following `function_body` sibling. Methods are `method_signature` plus `function_body`. Constructors are `constructor_signature` inside `declaration`. Named parameters live in `optional_formal_parameters` (`{...}`), with `required` written in the source. Optional positional parameters use `[...]`.

**Alternatives considered**: Regex over the first line (breaks on the multi-line `createTask` object type). A documentation-comment parser (the spec forbids inventing types from prose). Expanding node kinds for interfaces and abstract methods (out of scope; those nodes are not extracted today).

## R2. ClickUp client shape

**Decision**: Cover `ClickUpClient.createTask`, `setCustomFieldValue`, and `createWebhook` with a local TypeScript fixture shaped like `src/client/index.ts` in `Zanini-Software-LLC/clickup-kitchen-sink`. Do not clone that repository in tests.

**Rationale**: The published file uses `async` class `method_definition` nodes, positional parameters, inline object types, and unions (`value: string | number | boolean | { ... }`), plus a generic return type such as `Promise<Task>`. The current TypeScript query already captures `method_definition`. JSDoc blocks sit above the methods and are comments, not decorators, so snippets start at `async createTask` and still include the short body within 40 lines.

**Alternatives considered**: Indexing the live repository in CI (network, drift, and the spec says a local fixture is enough).

## R3. Snippet span

**Decision**:

- Start at the first attached decorator or annotation immediately above the entity. In Python that is the parent `decorated_definition`. In Dart that is a preceding `annotation` sibling. Comments, including JSDoc, are not part of the span.
- End at the end of the declaration node when that node includes the body (Python, JavaScript, TypeScript).
- For Dart, extend through the following `function_body` sibling (block or `=>` expression). Constructor declarations include the trailing semicolon inside the `declaration` node.
- Class snippets use the class node (`class_definition` / `class_declaration`), which already includes the body, then truncate.

**Rationale**: Matches the spec. Starting at JSDoc would spend the 40-line budget on comments before the body of `createTask`.

**Alternatives considered**: Body-only snippets without the signature line (agents would lose the citation header that the structured signature also provides, and the spec asks for declaration through body).

## R4. Caps, disable switch, and secrets

**Decision**:

- Defaults: `snippets=true`, `snippet_max_lines=40`, `snippet_max_bytes=2048`.
- Config keys use those names. CLI: `--no-snippets`, `--snippet-max-lines`, `--snippet-max-bytes`. One-run flags override config. Values below 1 or above the defaults raise `ConfigError` before indexing.
- Apply the line cap first, then the UTF-8 byte cap, cutting on a character boundary. Set `snippet_truncated` true when either cap shortens the text. When the excerpt is stored, always set `snippet_truncated`.
- When snippets are disabled, omit `snippet` and `snippet_truncated`. Still write signatures.
- Secret check uses the file basename only: `.env`, `.env.*`, basename containing `secret`, `credential`, or `password` (case-insensitive), suffix `.pem` or `.key`, or basename `id_rsa`. Matching files omit snippet fields. Signatures remain.

**Rationale**: The spec fixes the defaults, forbids raising them, and lists the path patterns. Basename matching avoids treating a directory named `secrets` as a secret file, which the requirement phrases as file name.

**Alternatives considered**: Redacting string literals inside ordinary source (explicitly out of scope). A hard-coded 40-line slice with no config (fails the disable/cap requirement).

## R5. Schema version and cache

**Decision**: Keep `SCHEMA_VERSION = "6.0.0"`. Bump `_AST_PARSER_VERSION` from `tree-sitter-v1` to `tree-sitter-v2` and include snippet settings in the AST `settings_hash` so cached `CodeEntity` values without signatures are not replayed, and a cap change does not reuse a snippet truncated under a different cap.

**Rationale**: `load_artifact` rejects every version other than `6.0.0`. A schema bump would make old graphs unloadable, which fails SC-006. Optional metadata keys are ignored by older consumers and accepted by the current validator because it only requires `name`, `language`, `file`, and `start_line` on code entities. The pickle cache stores the whole `ExtractResult`, so the parser version must change when `CodeEntity` grows.

**Alternatives considered**: Schema `6.1.0` or `7.0.0` (breaks the loader contract). Leaving the cache version unchanged (serves signature-less entities until the file changes).

## R6. What stays out of scope

**Decision**: Do not extract TypeScript `interface_declaration` methods or `abstract_method_signature` nodes. Do not add signatures for Java, Go, Rust, C++, or SQL. Do not publish to PyPI.

**Rationale**: Those TypeScript forms are not nodes today. The spec says not to invent node kinds. The user named three languages plus JavaScript and a minor version bump with no package publish.

**Alternatives considered**: Opportunistic signatures for every grammar (larger test surface, not requested).
