# Data Model: Code Node Signatures and Snippets

Graph `schema_version` remains `6.0.0`. All keys below are optional. Absence means "not captured", not an error.

## Code entity metadata (existing, unchanged)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | yes | Unchanged |
| `language` | string | yes | Unchanged |
| `file` | string | yes | Project-relative POSIX path |
| `start_line` | int | yes | 1-based |
| `end_line` | int | no | Unchanged |
| `qualified_name` | string | no | Unchanged |

## Signature (function and method)

Written only for `language` in `python`, `javascript`, `typescript`, `dart` when the declaration can be read. Omitted, not guessed, when it cannot.

| Field | Type | When present |
|-------|------|----------------|
| `signature` | string | Readable declaration text, whitespace collapsed to single spaces. Overloads first, in source order, joined with ` ; `, then the implementation signature. Decorators are not included. `async` is included when the declaration is async. |
| `parameters` | array | Same order as the implementation signature when a body exists; otherwise the first overload. Empty array when the declaration has no parameters. Omitted on class nodes. |
| `return_type` | string | Only when the source declares one. Collapsed source type text. |
| `signature_truncated` | bool | Present and `true` only when the signature payload was cut to stay within 2048 UTF-8 bytes. |

### Parameter object

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | yes | Source name. A destructuring pattern with no single name uses the collapsed pattern text (`{a, b}`). |
| `type` | string | no | Collapsed source type. Omitted when the source has no type. Not replaced with `any` or `Object`. |
| `kind` | string | yes | `positional`, `named`, `rest`, or `keywords` |
| `required` | bool | yes | `false` when the parameter has a default, a `?` marker, or sits in an optional positional/named group without `required`. `true` otherwise. |

Kind mapping:

| Kind | Source |
|------|--------|
| `positional` | Ordinary positional, Python positional-only, Dart required positional, Dart optional positional `[...]`, JS/TS non-rest parameters |
| `named` | Python keyword-only (after `*` / `*args`), Dart `{...}` named parameters |
| `rest` | Python `*args`, JS/TS `...args` |
| `keywords` | Python `**kwargs` |

`self` / `cls` stay positional parameters with no invented type.

## Class declaration

| Field | Type | When present |
|-------|------|----------------|
| `signature` | string | Collapsed header: name, type parameters, and base types. No parameter list. Example: `class Box<T> extends Base`. |
| `parameters` | — | Never written on class nodes |
| `return_type` | — | Never written on class nodes |

Constructors stay `method` nodes and use the function/method signature rules. Dart `this.value` initializing formals use the formal's name (`value`) and declared type when present.

## Snippet

| Field | Type | When present |
|-------|------|----------------|
| `snippet` | string | Verbatim source from the span in research R3. Omitted when snippets are disabled or the file basename is a secret pattern. |
| `snippet_truncated` | bool | Present whenever `snippet` is present. `true` when line or byte cap cut the source. |

Limits: `1 <= snippet_max_lines <= 40`, `1 <= snippet_max_bytes <= 2048`. Effective values come from config, overridden by the one-run flags. Truncation drops whole lines past the line cap, then drops trailing characters until UTF-8 byte length is at most the byte cap, without splitting a code point.

## Signature payload bound

UTF-8 length of `signature` plus the JSON encoding of `parameters` (and `return_type` when present) is at most 2048 bytes. Shrink by dropping parameters from the end, then truncating `signature` text on a character boundary. Set `signature_truncated` true if anything was removed. Do not drop the node.

## Secret basename

A file is secret when its basename matches any of:

- `.env` or starts with `.env.`
- contains `secret`, `credential`, or `password` (case-insensitive)
- ends with `.pem` or `.key`
- equals `id_rsa`

Directory names do not count. Ignored files are still not indexed.

## Settings

| Name | Default | Surfaces |
|------|---------|----------|
| `snippets` | `true` | config; CLI `--no-snippets` forces false |
| `snippet_max_lines` | `40` | config and `--snippet-max-lines` |
| `snippet_max_bytes` | `2048` | config and `--snippet-max-bytes` |

Invalid values are configuration errors. They do not produce a success graph.

## Validation

- Existing required metadata checks stay.
- If `parameters` is present, every entry has `name` (non-empty string), `kind` in the four values, and `required` boolean. `type`, when present, is a non-empty string.
- If `snippet` is present, `snippet_truncated` is boolean, line count is at most the active line cap, and UTF-8 size is at most the active byte cap.
- `schema_version` remains `6.0.0` for both old graphs (no new keys) and new graphs.

## State

No new lifecycle. A re-index rewrites metadata. Snippets disabled on a later run omit snippet keys in the new artifact. Cache identity includes parser version `tree-sitter-v2` and the effective snippet settings.
