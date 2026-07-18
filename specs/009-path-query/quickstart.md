# Quickstart Validation: Path Between Concepts

**Feature**: `009-path-query`  
**Date**: 2026-07-17

Use this guide after implementation to prove the feature end-to-end. Contracts: [cli.md](./contracts/cli.md), [path-json.md](./contracts/path-json.md). Data model: [data-model.md](./data-model.md).

## Prerequisites

- Python 3.11+
- Repo checkout with this feature implemented
- A portable schema `6.0.0` graph with at least one directed route between two resolvable nodes (use `tests/fixtures/path_graphs/` when present, or index a small project)
- Optional: local Ollama for LLM explanation polish / embeddings
- No cloud services required

## Setup

```bash
cd /path/to/grapheinstein
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Fixture

```bash
FIX=tests/fixtures/path_graphs   # preferred when present
OUT=/tmp/grapheinstein-009
mkdir -p "$OUT"
# If using a project fixture instead:
# grapheinstein index tests/fixtures/llm_project --output "$OUT/graph.json"
GRAPH="${FIX}/weighted_routes.json"   # or "$OUT/graph.json"
```

## Scenario A — Preferred weighted path (no LLM required)

```bash
grapheinstein path "start-concept" "end-concept" \
  --input "$GRAPH" --no-llm-explain > "$OUT/path.json"
python -c "
import json
d=json.load(open('$OUT/path.json'))
assert d['kind']=='path_answer'
assert d['version']=='1.0.0'
assert d['input_schema_version']=='6.0.0'
assert d['nodes'][0]==d['start']['node_id']
assert d['nodes'][-1]==d['end']['node_id']
assert d['hop_count']==len(d['steps'])
assert all(k in s for s in d['steps'] for k in ('type','provenance','cost'))
assert d['explanation']
"
echo $?
```

**Expected**:

- Exit code `0`
- Valid path-answer JSON on stdout
- Each step has `type` and `provenance`
- Explanation present; offline-capable

## Scenario B — Competing routes prefer trustworthy weights

Use a fixture with two routes where the hop-count-shorter route is low-confidence/`inferred`-heavy and the preferred route wins under the documented cost policy.

```bash
grapheinstein path "A" "B" -i "$GRAPH" --no-llm-explain > "$OUT/preferred.json"
python -c "
import json
d=json.load(open('$OUT/preferred.json'))
# Fixture-specific: preferred route node midpoints / edge types
assert 'preferred-mid' in d['nodes'] or any(s['provenance']=='extracted' for s in d['steps'])
"
```

**Expected**:

- Returned path matches the weighting policy winner (see fixture README), not the discarded alternate

## Scenario C — Fuzzy endpoint phrases

```bash
grapheinstein path "strt" "end-concept" -i "$GRAPH" --no-llm-explain > "$OUT/fuzzy.json"
test -s "$OUT/fuzzy.json"
```

**Expected**:

- Exit `0` when the near-miss clearly maps to the intended start node
- `start.query` retains the user phrase; `start.node_id` is the resolved id

## Scenario D — No path / unresolved endpoint

```bash
# Disconnected pair (fixture-defined)
if grapheinstein path "island-a" "island-b" -i "$GRAPH" --no-llm-explain >"$OUT/nop.json" 2>"$OUT/nop.err"; then
  echo "expected failure" >&2; exit 1
fi
# Unresolved
if grapheinstein path "zzzz-no-such" "end-concept" -i "$GRAPH" --no-llm-explain >"$OUT/miss.json" 2>"$OUT/miss.err"; then
  echo "expected failure" >&2; exit 1
fi
test ! -s "$OUT/nop.json"
test ! -s "$OUT/miss.json"
```

**Expected**:

- Non-zero exit
- Empty/no success JSON on stdout
- Clear stderr message

## Scenario E — Optional file output + trivial same-node

```bash
grapheinstein path "start-concept" "start-concept" -i "$GRAPH" \
  --output "$OUT/same.json" --no-llm-explain > "$OUT/same-stdout.json"
python -c "
import json
a=json.load(open('$OUT/same.json'))
b=json.load(open('$OUT/same-stdout.json'))
assert a==b
assert a['hop_count']==0 and a['steps']==[]
assert len(a['nodes'])==1
"
```

**Expected**:

- File and stdout documents identical
- Trivial path with empty steps

## Offline check

```bash
# With network disabled (example): run Scenario A again
grapheinstein path "start-concept" "end-concept" -i "$GRAPH" --no-llm-explain >/dev/null
```

**Expected**: Success without cloud services when the graph file is local.

## Notes

- Replace fixture node phrases with the names documented in `tests/fixtures/path_graphs/README.md` once that fixture lands during implementation.
- Do not pass path-answer JSON to `load_artifact`; it is not a graph envelope.
