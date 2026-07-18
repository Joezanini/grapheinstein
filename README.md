# Grapheinstein

Local-first CLI that maps a project folder into a portable `graph.json` knowledge graph for AI agents.

Offline by design — indexing, explain, path, and query use the local filesystem and optional local models (e.g. Ollama). No cloud APIs required.

Schema version: **6.0.0**.

## Install

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

## Validation

```bash
pytest
ruff check src tests
```

Feature quickstarts live under `specs/*/quickstart.md` (e.g. `specs/011-config-cache-init/quickstart.md`).

## Contributing

Community contributions are welcome — bug fixes, docs, tests, and features that fit the project’s local-first CLI goals.

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, validation, and how to propose a change.
