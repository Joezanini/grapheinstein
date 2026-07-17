# Grapheinstein

Local-first CLI that maps a project folder into a portable `graph.json` knowledge graph for AI agents.

This increment builds a directed graph of **files and directories** (`type`: `file` | `dir`, plus `metadata`), with:

- `contains` edges (directory → child)
- `references` edges (whole-token basename mentions in UTF-8 text)

Edges are labeled `extracted`. Offline by design — no cloud APIs required.

Schema version: **2.0.0** (re-index if you still have older `kind`/`directory` graphs).

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
# Index a project (default command)
grapheinstein /path/to/project --output graph.json

# Explicit index
grapheinstein index /path/to/project -o graph.json

# Console summary
grapheinstein visualize --input graph.json

# Summary + DOT export (summary still prints)
grapheinstein visualize --input graph.json --dot graph.dot

# Status for an existing graph
grapheinstein status --output graph.json
```

Optional config: `~/.grapheinstein/config.yaml` or `--config path/to/config.yaml`

```yaml
output: graph.json
log_level: INFO
```

## Validation

See [specs/002-digraph-index-visualize/quickstart.md](specs/002-digraph-index-visualize/quickstart.md).

```bash
pytest
```

## Offline

Indexing, visualize, and status use only the local filesystem and optional local config. No network calls are made on those code paths.
