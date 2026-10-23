# Contract: Python API and serve index body

**Feature**: `015-node-signatures-snippets`  
**Parity**: `grapheinstein.api.index` and `POST /index` accept the same snippet controls as the CLI.

## `index()` keyword arguments

| Argument | Type | Default | Notes |
|----------|------|---------|-------|
| `snippets` | bool | `True` | `False` omits snippet metadata. |
| `snippet_max_lines` | int \| None | None (use config, else 40) | 1–40 when set. |
| `snippet_max_bytes` | int \| None | None (use config, else 2048) | 1–2048 when set. |

Invalid values raise `ConfigError` before a success graph is written. Other `index()` behavior is unchanged.

Explain, path, and query responses that embed code-entity nodes keep whatever metadata the graph stored, including the new keys. They do not add a second copy of the source.

## `POST /index` JSON

Optional fields on the index body:

| Field | Type | Default |
|-------|------|---------|
| `snippets` | bool | `true` |
| `snippet_max_lines` | int | config / 40 |
| `snippet_max_bytes` | int | config / 2048 |

Out-of-range values return HTTP 400 `code: "config"`.
