# CLI Contract: grapheinstein (local LLM enrichment)

**Feature**: `006-ollama-llm-extraction`  
**CLI contract version**: 6.0.0 (paired with graph schema_version `6.0.0`)

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

Supported keys:

| Key | Type | Description |
|-----|------|-------------|
| `output` | string | Default graph output path |
| `log_level` | string | Logging level |
| `languages` | list of strings | Enabled code structure-extraction languages |
| `llm_model` | string | Ollama model tag (default `qwen3.5-2b-mlx:fp16-8gbGPU`) |
| `llm_base_url` | string | Ollama API base URL (default `http://localhost:11434`) |
| `llm_confidence_threshold` | number | Min confidence to keep enrichment edges (default `0.5`) |

Canonical language ids unchanged: `python`, `javascript`, `typescript`, `java`, `go`, `rust`, `cpp`, `sql`.

## Commands

### Default (no subcommand)

```text
grapheinstein PROJECT_PATH [--output PATH] [--languages LIST] [--include-docs] [--include-pdfs] [--transcribe-media] [--enrich-llm] [--llm-model NAME] [--llm-base-url URL] [--config PATH]
```

**Behavior**: Same as `grapheinstein index PROJECT_PATH ...`  
**Success exit**: `0`

### `index`

```text
grapheinstein index PROJECT_PATH [--output PATH] [--languages LIST] [--include-docs] [--include-pdfs] [--transcribe-media] [--enrich-llm] [--llm-model NAME] [--llm-base-url URL] [--config PATH]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `PROJECT_PATH` | path | required | Project folder to index |
| `--output` / `-o` | path | config or `graph.json` | Destination graph artifact |
| `--languages` | string | unset | Comma-separated language ids; when set, replaces config/default for this run |
| `--include-docs` | flag | off | Enable Markdown / TXT / RST enrichment |
| `--include-pdfs` | flag | off | Enable PDF section enrichment |
| `--transcribe-media` | flag | off | Enable image OCR + A/V transcription + media linking |
| `--enrich-llm` | flag | off | Enable local LLM concept/relation enrichment |
| `--llm-model` | string | config or `qwen3.5-2b-mlx:fp16-8gbGPU` | Ollama model tag for this run |
| `--llm-base-url` | string | config or `http://localhost:11434` | Ollama base URL for this run |

**Behavior**:
1. Validate `PROJECT_PATH` and resolve config (languages, LLM settings)
2. If any language id is unknown → exit non-zero; do not write a success graph
3. If `--transcribe-media` and required Python media extras are not importable → exit non-zero with install hint (unchanged from schema 5)
4. Discover files/dirs respecting `.gitignore`; do not follow symlinks
5. Build inventory: `contains` + basename `references` (`extracted`)
6. Code structure extract for enabled languages; per-file failures warn and continue
7. If `--include-docs` / `--include-pdfs` / `--transcribe-media`: prior modality enrichment (schema 5 behavior retained)
8. If `--enrich-llm`:
   - Resolve model name and base URL from CLI/config/defaults
   - If Ollama unreachable or model not available locally → warn on stderr, **skip** enrichment, continue to write structural graph (exit still `0` if rest succeeded)
   - Else, for each eligible non-ignored text-bearing file/chunk: call local chat API; merge `concept` nodes and enrichment edges; per-chunk failures warn and continue
   - Emit periodic progress on the human-readable stream while enriching
9. Without `--enrich-llm`, make zero Ollama HTTP calls
10. Write graph artifact per [graph-json.md](./graph-json.md) schema `6.0.0` (overwrite if exists)
11. Print success summary including prior counts plus `concept`, `implements`, and `depends_on` counts when enrichment ran

**Exit codes**:

| Code | Meaning |
|------|---------|
| 0 | Success (including when enrichment skipped due to missing model, or some chunks skipped) |
| non-zero | Invalid args, unknown language, media extras missing with `--transcribe-media`, unreadable project path, or write failure |

### `status` / `visualize`

Unchanged UX except they load schema `6.0.0` and MAY report concept / implements / depends_on counts. Reject schema ≤ `5.0.0` with re-index message.

## Machine vs human output

- Human progress/warnings/errors → stderr (Loguru/Rich as existing)
- Graph artifact → `--output` path (default `graph.json`)
- Success summary → stderr or stdout consistent with existing index summary style

## Compatibility notes

- Default index without `--enrich-llm` still writes schema `6.0.0` (same major as enriched runs) so loaders have a single current version; enrichment node/edge counts may be zero
- Older `5.0.0` artifacts MUST be rejected on load with a re-index message
