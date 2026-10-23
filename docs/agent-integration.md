# Agent integration

Grapheinstein exposes the same index and query semantics through three surfaces:

| Surface | When to use |
|---------|-------------|
| CLI (`grapheinstein index` / `query`) | Shell scripts, humans, CI |
| Python API (`grapheinstein.api`) | Cursor slash-commands, in-process agents |
| HTTP (`grapheinstein serve`) | Non-Python local clients |

All three share one core implementation. Install:

```bash
pip install -e ".[dev]"                 # core + tests
pip install -e ".[dev,serve]"           # + optional local HTTP
# or: pip install 'grapheinstein[serve]'
```

## Python API (recommended for Cursor)

```python
from pathlib import Path
from grapheinstein.api import index, query

# Index a project folder → portable graph.json
result = index(
    Path("/path/to/project"),
    output=Path("graph.json"),
    include_docs=True,
)
print(result.output_path, result.stats.total_nodes)

# Query an existing graph (same envelope as CLI stdout)
envelope = query(
    "How does authentication work?",
    input=result.output_path,
    output=Path("subgraph.json"),
    no_answer=True,  # skip local LLM answer
)
print(envelope["schema_version"], envelope["hit_ids"])
print(envelope["answer"]["status"])
```

Hard failures raise exceptions (`FileNotFoundError`, `ConfigError`, `NoEvidenceError`, …) — they never return an empty success graph.

Canonical import: `from grapheinstein.api import index, query`.

## Optional HTTP serve

```bash
grapheinstein serve --port 8000
# listens on http://127.0.0.1:8000 by default (loopback only)
```

### `POST /index`

```bash
curl -sS -X POST http://127.0.0.1:8000/index \
  -H 'Content-Type: application/json' \
  -d '{"project_path":".","output":"graph.json","include_docs":true}'
```

Success includes `"ok": true`, `"output"`, and `"stats"`.

### `POST /query`

```bash
curl -sS -X POST http://127.0.0.1:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"How does auth work?","input":"graph.json","output":"sub.json","no_answer":true}'
```

Success is the query-answer envelope (`schema_version` `1.0.0`) plus `"ok": true` at the top level.

Errors look like:

```json
{"ok": false, "error": "…", "code": "not_found"}
```

Advanced: `--host 0.0.0.0` binds beyond loopback **without authentication** — only on trusted networks.

## Code entity signatures and snippets

Index results for Python, JavaScript, TypeScript, and Dart may add optional metadata on `function`, `method`, and `class` nodes. `schema_version` stays `6.0.0`. Missing keys mean "not captured".

| Key | Nodes | Meaning |
|-----|--------|---------|
| `signature` | function, method, class | Readable declaration. Class nodes are the declaration line only. |
| `parameters` | function, method | Ordered `{name, type?, kind, required}`. `kind` is `positional`, `named`, `rest`, or `keywords`. |
| `return_type` | function, method | Declared return type text. Omitted when the source has none. |
| `signature_truncated` | function, method | Present and `true` only when the signature payload was cut at 2048 bytes. |
| `snippet` | function, method, class | Verbatim excerpt, at most 40 lines and 2048 bytes by default. |
| `snippet_truncated` | same as `snippet` | `true` when the excerpt was cut. |

Explain, path, and query views that return these nodes keep the metadata. Turn excerpts off with `index(..., snippets=False)`, CLI `--no-snippets`, or `POST /index` field `"snippets": false`. `snippet_max_lines` and `snippet_max_bytes` accept 1–40 and 1–2048. Secret-pattern file names (`.env`, `.env.*`, `secret`, `credential`, `password`, `.pem`, `.key`, `id_rsa`) do not receive `snippet`.

## Parity

| Action | CLI | Python | HTTP |
|--------|-----|--------|------|
| Index project | `grapheinstein index DIR -o graph.json` | `index(DIR, output=…)` | `POST /index` |
| Skip snippets | `--no-snippets` | `index(..., snippets=False)` | `{"snippets": false}` |
| Query graph | `grapheinstein query Q -i g -o s` | `query(Q, input=…, output=…)` | `POST /query` |

For the same inputs, Python and CLI query produce the same `hit_ids` evidence set.

## Out of scope here

- Cursor marketplace plugins
- Full MCP graph-library hosting
- Auth / TLS / multi-tenant remote APIs
