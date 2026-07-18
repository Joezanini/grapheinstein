# Quickstart Validation: Hybrid Natural-Language Query

**Feature**: `010-hybrid-query`  
**Date**: 2026-07-17

Use this guide after implementation to prove the feature end-to-end. Contracts: [cli.md](./contracts/cli.md), [graph-json.md](./contracts/graph-json.md), [query-answer-json.md](./contracts/query-answer-json.md). Data model: [data-model.md](./data-model.md).

## Prerequisites

- Python 3.11+
- Repo checkout with this feature implemented
- A portable schema `6.0.0` graph with searchable node text (index a small fixture, or use `tests/fixtures/query_graphs/` when present)
- Optional: local Ollama with the configured model for answer scenarios
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
FIX=tests/fixtures/llm_project   # or tests/fixtures/query_graphs
OUT=/tmp/grapheinstein-010
mkdir -p "$OUT"
grapheinstein index "$FIX" --output "$OUT/graph.json"
# Prefer a graph with concept/code names or media text relevant to a known question
```

## Scenario A — Retrieve + subgraph (no LLM required)

```bash
grapheinstein query "How does authentication work?" \
  --input "$OUT/graph.json" --output "$OUT/sub.json" --no-answer \
  > "$OUT/answer.json"
python -c "
import json
sub=json.load(open('$OUT/sub.json'))
ans=json.load(open('$OUT/answer.json'))
assert sub['schema_version']=='6.0.0'
assert 'authentication' in sub['graph']['query_question'].lower()
assert sub['graph']['query_hit_ids']
assert sub['graph']['query_k'] == 20 or isinstance(sub['graph']['query_k'], int)
assert sub['nodes'] and all('metadata' in n for n in sub['nodes'])
assert all(k in e for e in sub['links'] for k in ('type','provenance'))
assert ans['schema_version']=='1.0.0'
assert ans['answer']['status'] in ('skipped','ok','failed')
assert ans['visualization']['node_count'] == len(sub['nodes'])
"
echo $?
```

**Expected**:

- Exit code `0`
- Valid schema `6.0.0` supporting subgraph with query metadata
- Stdout query-answer JSON; answer status `skipped` when `--no-answer`
- Visualization counts match subgraph; edges retain provenance
- No cloud calls

## Scenario B — `--k` bounds primary hits

```bash
grapheinstein query "configuration" -i "$OUT/graph.json" -o "$OUT/k3.json" --k 3 --no-answer > "$OUT/k3-ans.json"
python -c "
import json
d=json.load(open('$OUT/k3.json'))
assert d['graph']['query_k'] == 3
assert len(d['graph']['query_hit_ids']) <= 3
"
```

**Expected**:

- Exit `0`
- `query_hit_ids` length ≤ 3

## Scenario C — No evidence

```bash
rm -f "$OUT/nomatch.json"
grapheinstein query "zzzx_not_a_real_topic_qqq_999" \
  -i "$OUT/graph.json" -o "$OUT/nomatch.json" --no-answer
echo exit:$?
test ! -f "$OUT/nomatch.json"
```

**Expected**:

- Non-zero exit
- No success-looking file at `$OUT/nomatch.json`

## Scenario D — Invalid `--k`

```bash
grapheinstein query "anything" -i "$OUT/graph.json" -o "$OUT/badk.json" --k 0 --no-answer
echo exit:$?
```

**Expected**:

- Non-zero exit (validation error)
- No success subgraph written as a successful run

## Scenario E — Cited answer with local LLM (optional)

```bash
grapheinstein query "How does authentication work?" \
  -i "$OUT/graph.json" -o "$OUT/ans-sub.json" \
  > "$OUT/ans.json"
python -c "
import json
sub=json.load(open('$OUT/ans-sub.json'))
ans=json.load(open('$OUT/ans.json'))
ids={n['id'] for n in sub['nodes']}
if ans['answer']['status']=='ok':
    assert ans['answer']['text']
    assert ans['answer']['citations']
    for c in ans['answer']['citations']:
        if c['kind']=='node':
            assert c['node_id'] in ids
"
```

**Expected**:

- Exit `0` when Ollama is ready
- Answer status `ok` with non-empty citations, each node citation present in subgraph
- If Ollama is down: exit `0`, subgraph written, answer `skipped`/`failed` with clear detail; still no cloud calls

## Scenario F — Visualize supporting subgraph (optional follow-up)

```bash
grapheinstein visualize --input "$OUT/sub.json"
```

**Expected**:

- Existing visualize command accepts the query output without repair

## Automated suite (after tests land)

```bash
pytest tests/unit/test_query_chunks.py \
       tests/unit/test_query_hybrid.py \
       tests/unit/test_query_citations.py \
       tests/unit/test_query_viz.py \
       tests/contract/test_cli_query.py \
       tests/integration/test_cli_query_cmd.py -q
```

**Expected**: all pass without network access for non-LLM cases (LLM cases use fakes/injectables).
