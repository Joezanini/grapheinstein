# Quickstart Validation: Serve & Agent API

**Feature**: `012-serve-api`  
**Date**: 2026-07-17

Use after implementation to prove agent surfaces end-to-end. Contracts: [cli.md](./contracts/cli.md), [python-api.md](./contracts/python-api.md), [http-api.md](./contracts/http-api.md). Data model: [data-model.md](./data-model.md). User docs: `docs/agent-integration.md`.

## Prerequisites

- Python 3.11+
- Repo checkout with this feature implemented
- Optional: `pip install -e ".[dev,serve]"` for HTTP scenarios
- No cloud services required
- Local Ollama optional (query `--no-answer` / `no_answer=True` works offline)

## Setup

```bash
cd /path/to/grapheinstein
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
FIX=tests/fixtures/query_graphs   # or any small indexed fixture project
OUT=/tmp/grapheinstein-012
mkdir -p "$OUT"
```

## Scenario A — Python API index + query

```bash
python - <<'PY'
from pathlib import Path
from grapheinstein.api import index, query

out = Path("/tmp/grapheinstein-012")
# Prefer a small source tree; adjust if fixtures differ
project = Path("tests/fixtures/config_cache")
r = index(project, output=out / "api-graph.json", include_docs=True)
assert r.output_path.exists()
assert r.stats is not None
env = query(
    "configuration",
    input=r.output_path,
    output=out / "api-sub.json",
    no_answer=True,
)
assert env["schema_version"] == "1.0.0"
assert "answer" in env
print("OK", r.output_path, env["hit_ids"][:3])
PY
```

**Expected**: Exit 0; graph written; query-answer envelope returned without importing FastAPI.

## Scenario B — CLI parity (same evidence)

```bash
grapheinstein index tests/fixtures/config_cache -o "$OUT/cli-graph.json" --include-docs
grapheinstein query "configuration" -i "$OUT/cli-graph.json" -o "$OUT/cli-sub.json" --no-answer \
  > "$OUT/cli-ans.json"
python - <<'PY'
import json
from pathlib import Path
from grapheinstein.api import query
cli = json.load(open("/tmp/grapheinstein-012/cli-ans.json"))
api = query(
    "configuration",
    input=Path("/tmp/grapheinstein-012/cli-graph.json"),
    output=Path("/tmp/grapheinstein-012/api-parity-sub.json"),
    no_answer=True,
)
assert set(cli["hit_ids"]) == set(api["hit_ids"]), (cli["hit_ids"], api["hit_ids"])
print("parity OK")
PY
```

**Expected**: Identical `hit_ids` sets for the same graph + question (SC-002).

## Scenario C — Serve help + missing extras

```bash
# Without [serve] extras (use a venv that only has .[dev] if testing absence):
grapheinstein serve --help
# Should document --port default 8000 and agent-integration docs

# If extras missing:
# grapheinstein serve --port 8765
# → non-zero exit, install hint mentioning grapheinstein[serve]
```

## Scenario D — HTTP round-trip (requires `[serve]`)

```bash
pip install -e ".[dev,serve]"
grapheinstein serve --port 8765 &
PID=$!
sleep 1
curl -sS -X POST http://127.0.0.1:8765/index \
  -H 'Content-Type: application/json' \
  -d "{\"project_path\":\"tests/fixtures/config_cache\",\"output\":\"$OUT/http-graph.json\",\"include_docs\":true}" \
  | tee "$OUT/http-index.json"
python -c "import json; d=json.load(open('$OUT/http-index.json')); assert d['ok'] is True; assert Path:=__import__('pathlib').Path(d['output']).exists()"
curl -sS -X POST http://127.0.0.1:8765/query \
  -H 'Content-Type: application/json' \
  -d "{\"question\":\"configuration\",\"input\":\"$OUT/http-graph.json\",\"output\":\"$OUT/http-sub.json\",\"no_answer\":true}" \
  | tee "$OUT/http-query.json"
python -c "import json; d=json.load(open('$OUT/http-query.json')); assert d.get('ok') is True; assert d['schema_version']=='1.0.0'"
kill $PID
```

**Expected**: Both POSTs return `ok: true` JSON; graph and subgraph files exist; default bind rejects non-local clients (manual check optional).

## Scenario E — Port in use

```bash
grapheinstein serve --port 8765 &
PID=$!
sleep 1
grapheinstein serve --port 8765 ; echo exit:$?
kill $PID
```

**Expected**: Second serve exits non-zero with a message naming port `8765`.

## Scenario F — Docs exist

```bash
test -f docs/agent-integration.md
grep -q 'grapheinstein.api' docs/agent-integration.md
grep -q '/index' docs/agent-integration.md
grep -qi serve README.md
```

**Expected**: Agent playbook present; README links or mentions agent integration.
