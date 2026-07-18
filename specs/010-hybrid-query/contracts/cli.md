# CLI Contract: grapheinstein query

**Feature**: `010-hybrid-query`  
**CLI contract version**: 10.0.0 (pairs with graph schema_version `6.0.0`; additive `query` subcommand)

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
| `query_k` | int | `20` | Default primary retrieval hit count (`1`–`200`) |
| `query_hops` | int | `1` | Default undirected expansion radius (`1` or `2`) |
| `query_match_threshold` | float | `0.40` | Minimum final hit score |
| `query_node_cap` | int | `500` | Max nodes in supporting subgraph |
| `llm_model` | string | existing default | Local chat/embeddings model |
| `llm_base_url` | string | existing default | Local Ollama base URL |

Prior keys (`explain_*`, `path_*`, `output`, `log_level`, …) unchanged. Unknown keys warned and ignored as today.

## Commands

### `query` (new)

```text
grapheinstein query QUESTION --input PATH --output PATH
    [--k N] [--hops 1|2] [--match-threshold F]
    [--llm-model NAME] [--llm-base-url URL]
    [--no-answer] [--config PATH]
```

| Option / arg | Type | Default | Description |
|--------------|------|---------|-------------|
| `QUESTION` | string | required | Plain-language question (positional) |
| `--input` / `-i` | path | required | Input portable graph (`.json` or `.json.gz`) |
| `--output` / `-o` | path | required | Destination for supporting subgraph |
| `--k` | int | config or `20` | Max primary retrieval hits (`1`–`200`) |
| `--hops` | int | config or `1` | Undirected expansion radius; only `1` or `2` |
| `--match-threshold` | float | config or `0.40` | Minimum score in `[0.0, 1.0]` |
| `--llm-model` | string | config / built-in | Override local model for answer (and embeddings when used) |
| `--llm-base-url` | string | config / built-in | Override local Ollama base URL |
| `--no-answer` | flag | off | Skip local LLM answer; still retrieve + write subgraph + viz |
| `--config` | path | unset | Config file for this run |

**Behavior**:

1. Validate `QUESTION` (non-empty) and option ranges; on failure → non-zero exit, no write.
2. Load `--input` via gzip-aware loader; validate schema `6.0.0`.
3. Build chunk corpus; score candidates (fuzzy always; optional local embeddings when available). Select up to `--k` hits with score ≥ threshold.
4. If no hits → clear human-readable error, non-zero exit, **do not** write a success-looking subgraph at `--output`.
5. Expand undirected neighborhood of radius `hops` around primary hits; apply `query_node_cap`; set truncation metadata/warning if needed.
6. Build artifact with query graph metadata (see [graph-json.md](./graph-json.md)); validate; atomic write to `--output`.
7. Emit visualization summary on the human-readable stream (stderr).
8. Unless `--no-answer`: if local model ready, generate cited answer (validate citations against subgraph); print human answer on stderr; if not ready or generation fails, report skip/failure clearly and still exit `0` after successful write.
9. On success, print query-answer JSON on **stdout** (see [query-answer-json.md](./query-answer-json.md)).

**Success exit**: `0` (subgraph written; answer optional)

**Typical failures** (non-zero): empty question, bad k/hops/threshold, missing/invalid input, empty corpus, no evidence, write/validation error.

### Streams

| Stream | Content |
|--------|---------|
| stdout | Query-answer JSON on success only |
| stderr | Progress, errors, visualization summary, human-readable answer text |
| `--output` file | Supporting subgraph (portable graph JSON) |

### Compatibility

- `index`, `status`, `visualize`, `merge`, `explain`, `path` unchanged by this contract.
- `grapheinstein --help` / `query --help` MUST list the `query` command and its options.

## Non-goals (this contract)

- Re-indexing the project as part of `query`
- Required cloud embeddings or chat APIs
- Interactive/GUI visualization or automatic image export
- Slash-command / MCP wrappers
- Hop depths other than 1 or 2
- `--k` outside `1`–`200`
