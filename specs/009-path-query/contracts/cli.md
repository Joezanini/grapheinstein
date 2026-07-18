# CLI Contract: grapheinstein path

**Feature**: `009-path-query`  
**CLI contract version**: 9.0.0 (pairs with input graph schema_version `6.0.0`; additive `path` subcommand)

## Entrypoint

- Console script: `grapheinstein`
- Module: `python -m grapheinstein`

## Global / shared options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config` | path | unset | YAML config path; overrides user config for this run |
| `--help` | flag | — | Show help |

Config precedence: CLI flags > `--config` file > `~/.grapheinstein/config.yaml` > built-ins.

User config path: `~/.grapheinstein/config.yaml`

### Config keys (additions for this feature)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `path_match_threshold` | float | `0.55` | Minimum final match score per endpoint (falls back to shared match threshold if implemented as alias) |
| `path_max_hops` | int | `32` | Maximum accepted path edge count |
| `path_confidence_default` | float | `0.5` | Assumed confidence when edge omits it |
| `path_confidence_floor` | float | `0.35` | ε floor for confidence in cost formula |
| `path_provenance_inferred_factor` | float | `1.75` | Multiplier for `inferred` edges (`extracted` = 1.0) |
| `llm_model` | string | existing default | Local model for optional explanation polish / embeddings |
| `llm_base_url` | string | existing default | Local Ollama base URL |

Prior keys unchanged. Unknown keys warned and ignored as today.

Shared match threshold key from explain (`explain_match_threshold`) MAY be reused as the default source when `path_match_threshold` is unset; CLI `--match-threshold` always wins for the path command.

## Commands

### `path` (new)

```text
grapheinstein path START END --input PATH
    [--output PATH] [--match-threshold F] [--max-hops N]
    [--llm-model NAME] [--llm-base-url URL]
    [--no-llm-explain] [--config PATH]
```

| Option / arg | Type | Default | Description |
|--------------|------|---------|-------------|
| `START` | string | required | Start concept phrase (positional) |
| `END` | string | required | End concept phrase (positional) |
| `--input` / `-i` | path | required | Input portable graph (`.json` or `.json.gz`) |
| `--output` / `-o` | path | unset | Optional file for path-answer JSON (same document as stdout) |
| `--match-threshold` | float | config or `0.55` | Minimum score in `[0.0, 1.0]` per endpoint |
| `--max-hops` | int | config or `32` | Max edges in accepted path |
| `--llm-model` | string | config / built-in | Override local model for polish/embeddings |
| `--llm-base-url` | string | config / built-in | Override local Ollama base URL |
| `--no-llm-explain` | flag | off | Skip LLM polish; keep deterministic explanation |
| `--config` | path | unset | Config file for this run |

**Behavior**:

1. Validate `START` / `END` (non-empty) and option ranges; on failure → non-zero exit.
2. Load `--input` via gzip-aware loader; validate schema `6.0.0`.
3. Resolve each endpoint to the single best match ≥ threshold (fuzzy always; optional local embeddings).
4. If either endpoint unresolved → clear human-readable error naming the failed side(s), non-zero exit, no success JSON.
5. Compute directed weighted shortest path (research R3–R4). Same node → trivial path.
6. If no path or hop count > `max_hops` → clear error, non-zero exit.
7. Build path-answer JSON (see [path-json.md](./path-json.md)); print to **stdout**.
8. If `--output` set → atomic write of the same JSON to that path.
9. Print human-oriented explanation (and brief match/path summary) on the **human-readable stream (stderr)**. Optionally polish explanation with local LLM unless `--no-llm-explain`.
10. Progress/errors never mix into stdout JSON on success.

**Success exit**: `0` (path answer emitted)

**Typical failures** (non-zero): empty endpoints, bad threshold/hops, missing/invalid input, unresolved start/end, no path, path too long, write/validation error.

### Compatibility

- `index`, `status`, `visualize`, `merge`, `explain` unchanged by this contract.
- `grapheinstein --help` / `path --help` MUST list the `path` command and its options.

## Streams

| Stream | Content |
|--------|---------|
| stdout | Path-answer JSON only (success) |
| stderr | Progress, errors, human explanation, match summary |

## Non-goals (this contract)

- Re-indexing the project as part of `path`
- Required cloud embeddings or chat APIs
- Returning k alternate paths
- Writing a schema `6.0.0` graph subgraph as the primary answer (path-answer JSON is primary)
- Slash-command / MCP wrappers
