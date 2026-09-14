# Grapheinstein

Local-first CLI that maps a project folder into a portable `graph.json` knowledge graph for AI agents.

Offline by design — indexing, explain, path, and query use the local filesystem and optional local models (e.g. Ollama). No cloud APIs required.

Schema version: **6.0.0**.

## Install

```bash
pip install grapheinstein
# Optional local HTTP API:
# pip install 'grapheinstein[serve]'
# Optional OCR / audio extras:
# pip install 'grapheinstein[media]'
```

### From source

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# Optional local HTTP API:
# pip install -e ".[dev,serve]"
```

## Quick start

```bash
# Create a commented starter config (~/.grapheinstein/config.yaml by default)
grapheinstein init
# or: grapheinstein init --output ./grapheinstein.yaml

# Index a project (default command)
grapheinstein /path/to/project --output graph.json

# Explicit index with project config
grapheinstein index /path/to/project -o graph.json --config ./grapheinstein.yaml

# Explain / path / query over an existing graph
grapheinstein explain "authentication" -i graph.json -o explain.json --no-summary
grapheinstein path "login" "database" -i graph.json --no-llm-explain
grapheinstein query "How does auth work?" -i graph.json -o sub.json --no-answer

# Console summary / status
grapheinstein visualize --input graph.json
grapheinstein status --output graph.json

# Optional local HTTP (requires: pip install 'grapheinstein[serve]')
grapheinstein serve --port 8000
```

## Agent integration

Agents and Cursor slash-commands should call the Python API (same semantics as the CLI):

```python
from grapheinstein.api import index, query
```

Optional HTTP: `POST /index` and `POST /query` via `grapheinstein serve` (loopback by default).

See [docs/agent-integration.md](docs/agent-integration.md) for copy-paste examples and CLI ↔ Python ↔ HTTP parity.

## Configuration

Config precedence: CLI flags > `--config` file > `~/.grapheinstein/config.yaml` > built-ins.

Key settings (see `grapheinstein init` for a full commented template):

| Key | Purpose |
|-----|---------|
| `ignored_patterns` | Extra gitignore-style paths beyond `.gitignore` |
| `embedding_model` | Local model for embeddings |
| `llm_model` | Local model for enrichment / answers |
| `max_file_size` | Skip parsing files larger than this (bytes; default 10 MiB) |
| `cache_dir` | Local cache for ASTs / chunks / embeddings (default `~/.grapheinstein/cache`) |

Re-indexing an unchanged project reuses the cache under `cache_dir` for faster runs.

## Troubleshooting

### Empty or sparse graphs

If indexing succeeds but produces an empty or nearly-empty graph:

- **Check warnings in output**: Grapheinstein warns when no entities are extracted or when many files fail to parse
- **Common causes**:
  - All files matched by `.gitignore` or `ignored_patterns`
  - Files are too large (exceed `max_file_size`, default 10 MiB)
  - Unsupported file types or encoding issues (non-UTF-8)
  - Parse failures (check logs at `INFO` or `DEBUG` level)

### High parse skip ratio

When many files fail to parse, grapheinstein logs warnings and reports skip counts in the summary. Common causes:

- Non-code files in the project (binaries, images, data files) — use `.gitignore` or `ignored_patterns` to exclude them
- Syntax errors in source files (especially in actively developed code)
- Unsupported language features or dialects

### Timeouts

Indexing large repositories may exceed the default timeout (disabled by default). To configure:

```yaml
# In ~/.grapheinstein/config.yaml or custom config
timeout_seconds: 300  # 5 minutes
```

Grapheinstein checks the timeout at phase boundaries (discovery, inventory, preflight, references, parsing, enrichment) and warns when 80% of the budget is consumed. Note that timeout is a cooperative limit — long-running individual operations (like parsing a huge file) may exceed it.

### Exit codes

- **0**: Success (graph created, even if empty or sparse)
- **1**: General error (config, I/O, parse validation, etc.)
- **2**: Large repository rejected (use `--allow-large-repo` to bypass advisory limits)
- **3**: Timeout exceeded

Error messages indicate the category (e.g., "Configuration error", "I/O error (may be transient)") to help distinguish permanent failures from transient issues like network or filesystem errors.

### Upstream git clone failures

If you're rebuilding graphs from upstream git repositories (e.g., in CI or with Librarian):

- Ensure git is installed and accessible
- Check network connectivity and authentication
- For transient failures (network, rate limits), implement retry logic with exponential backoff
- For permanent failures (404, auth errors), log and skip the repository

### Large-repo preflight failures

When indexing a catalog of diverse repositories (e.g., for a library directory), some repos may trip advisory large-repo gates:

**Exit code 2 scenarios:**
- `max_non_code_share` (default 0.85): repo has >85% non-code files
- `max_reference_scan_ops` (default 5M): estimated reference scan operations exceed threshold

**For library catalogs with SDK/docs-heavy repos:**

1. Use `--code-only` flag to exclude docs/discovery_cache by default:
   ```bash
   grapheinstein index /path/to/repo --code-only -o graph.json
   ```

2. Or adjust thresholds in config for catalog-friendly defaults:
   ```yaml
   # ~/.grapheinstein/config.yaml
   max_non_code_share: 0.90  # Allow up to 90% non-code
   max_reference_scan_ops: 10000000  # 10M ops
   ```

3. Or bypass advisory gates per-repo (hard caps still apply):
   ```bash
   grapheinstein index /path/to/repo --allow-large-repo -o graph.json
   ```

**Structured failure output:**

When indexing fails with exit code 2, grapheinstein writes `<output>.failure.json` with:
- `exit_code`, `error_category`, `error_message`
- `details.failure_codes` (e.g., `large_repo_preflight_max_non_code_share`)
- `details.metrics` (actual values: `non_code_share`, `estimated_scan_ops`, etc.)
- `details.thresholds` (configured limits)
- `details.suggested_flags` (e.g., `--code-only`)

Automation scripts can parse this file instead of scraping stderr.

### Empty stderr in automation

If grapheinstein fails but produces no stderr output (seen in some CI/automation environments):

This can happen when:
- Process is killed externally (OOM, timeout) before stderr is flushed
- Stderr is not captured correctly by the calling process
- Buffering issues in subprocess invocation

**Debugging steps:**

1. Enable debug logging to a file:
```bash
export GRAPHEINSTEIN_DEBUG_LOG=/tmp/grapheinstein-debug.log
grapheinstein index /path/to/project
```

2. Check if the process completes:
```bash
timeout 300 grapheinstein index /path/to/project -o graph.json
echo "Exit code: $?"
```

3. Check for structured failure output:
```bash
# If graph.json write was attempted, check graph.json.failure.json
if [ -f graph.json.failure.json ]; then
  cat graph.json.failure.json
fi
```

4. Ensure stderr is flushed in Python subprocess calls:
```python
result = subprocess.run(
    ["grapheinstein", "index", repo_path, "-o", "graph.json"],
    capture_output=True,
    text=True,
    timeout=300,
)
# Check both exit code and structured failure output
if result.returncode != 0:
    failure_file = Path("graph.json.failure.json")
    if failure_file.exists():
        failure_info = json.loads(failure_file.read_text())
        # Parse structured failure details
        print(f"Category: {failure_info['error_category']}")
        print(f"Details: {failure_info.get('details', {})}")
```

## Validation

```bash
pytest
ruff check src tests
```

Feature quickstarts live under `specs/*/quickstart.md` (e.g. `specs/011-config-cache-init/quickstart.md`).

## Contributing

Community contributions are welcome — bug fixes, docs, tests, and features that fit the project’s local-first CLI goals.

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, validation, and how to propose a change.
