# CLI Contract: Serve

**Feature**: `012-serve-api`  
**CLI contract version**: `12.0.0` (additive; graph schema remains `6.0.0`; query-answer remains `1.0.0`)

## Entrypoint

- Console script: `grapheinstein`
- Module: `python -m grapheinstein`

## Commands

### `serve` (new)

```text
grapheinstein serve [--port PORT] [--host HOST]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--port` | int | `8000` | TCP port to listen on |
| `--host` | string | `127.0.0.1` | Bind address; default loopback only |

**Behavior**:

1. If optional `[serve]` extras are missing, print actionable install hint (`pip install 'grapheinstein[serve]'`) to stderr and exit non-zero. Do not start a partial server.
2. Attempt to bind `host:port`. If the port is in use (or bind fails), print an error naming the port and exit non-zero; do **not** pick another port silently.
3. Start local HTTP service exposing at least `POST /index` and `POST /query` per [http-api.md](./http-api.md).
4. Log listen URL to stderr (e.g. `http://127.0.0.1:8000`). Remain running until SIGINT/SIGTERM.
5. Help text MUST document purpose, `--port`, default port, `--host` (advanced / non-loopback warning), and point to `docs/agent-integration.md`.

**Exit codes**:

| Code | Meaning |
|------|---------|
| `0` | Clean shutdown after successful run |
| `1` | Missing deps, bind failure, or other startup/runtime error |

**Known commands**: Root dispatcher `_KNOWN_COMMANDS` MUST include `serve`.

## Unchanged commands

`init`, `index`, `status`, `visualize`, `merge`, `explain`, `path`, `query` retain prior contracts. Prefer refactoring CLI index/query bodies to call `grapheinstein.api` so CLI and serve share one path (implementation detail; contract requires behavioral parity).

## Human vs machine streams

- Serve startup/shutdown/logs: **stderr**
- HTTP JSON bodies: HTTP response only (never mixed into stderr as the success payload)
