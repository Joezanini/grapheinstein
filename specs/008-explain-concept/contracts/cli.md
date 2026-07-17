# CLI Contract: grapheinstein explain

**Feature**: `008-explain-concept`  
**CLI contract version**: 8.0.0 (pairs with graph schema_version `6.0.0`; additive `explain` subcommand)

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
| `explain_hops` | int | `2` | Default hop radius (`1` or `2`) |
| `explain_top_n` | int | `3` | Max primary matches |
| `explain_match_threshold` | float | `0.55` | Minimum final match score |
| `explain_node_cap` | int | `500` | Max nodes in explanation subgraph |
| `llm_model` | string | existing default | Local chat/embeddings model |
| `llm_base_url` | string | existing default | Local Ollama base URL |

Prior keys (`output`, `log_level`, `languages`, `compress`, `versioned`, `llm_confidence_threshold`, …) unchanged. Unknown keys warned and ignored as today.

## Commands

### `explain` (new)

```text
grapheinstein explain CONCEPT --input PATH --output PATH
    [--hops 1|2] [--top-n N] [--match-threshold F]
    [--llm-model NAME] [--llm-base-url URL]
    [--no-summary] [--config PATH]
```

| Option / arg | Type | Default | Description |
|--------------|------|---------|-------------|
| `CONCEPT` | string | required | Concept phrase to match (positional) |
| `--input` / `-i` | path | required | Input portable graph (`.json` or `.json.gz`) |
| `--output` / `-o` | path | required | Destination for explanation subgraph |
| `--hops` | int | config or `2` | Undirected neighborhood radius; only `1` or `2` |
| `--top-n` | int | config or `3` | Max primary matches (≥ 1) |
| `--match-threshold` | float | config or `0.55` | Minimum score in `[0.0, 1.0]` |
| `--llm-model` | string | config / built-in | Override local model for summary (and embeddings when used) |
| `--llm-base-url` | string | config / built-in | Override local Ollama base URL |
| `--no-summary` | flag | off | Skip local LLM summary; still match + write subgraph |
| `--config` | path | unset | Config file for this run |

**Behavior**:

1. Validate `CONCEPT` (non-empty) and option ranges; on failure → non-zero exit, no write.
2. Load `--input` via gzip-aware loader; validate schema `6.0.0`.
3. Score nodes (fuzzy always; optional local embeddings when available). Select up to `top-n` matches with score ≥ threshold.
4. If no matches → clear human-readable error, non-zero exit, **do not** write a success-looking subgraph at `--output`.
5. Extract undirected neighborhood of radius `hops` around primary matches; apply `explain_node_cap`; set truncation metadata/warning if needed.
6. Build artifact with explain graph metadata (see [graph-json.md](./graph-json.md)); validate; atomic write to `--output`.
7. Unless `--no-summary`: if local model ready, generate natural-language summary to the human-readable stream (stderr); if not ready or generation fails, report skip/failure clearly and still exit `0` after successful write.
8. Print a short match summary (match ids, scores, hops, output path, truncation flag) on the human-readable stream.

**Success exit**: `0` (subgraph written; summary optional)

**Typical failures** (non-zero): empty concept, bad hops/threshold, missing/invalid input, no match, write/validation error.

### Compatibility

- `index`, `status`, `visualize`, `merge` unchanged by this contract.
- `grapheinstein --help` / `explain --help` MUST list the `explain` command and its options.

## Non-goals (this contract)

- Re-indexing the project as part of `explain`
- Required cloud embeddings or chat APIs
- Writing the narrative summary as a second required file
- Slash-command / MCP wrappers
- Hop depths other than 1 or 2
