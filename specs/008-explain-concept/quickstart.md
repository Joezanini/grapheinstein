# Quickstart Validation: Explain Concept Subgraph

**Feature**: `008-explain-concept`  
**Date**: 2026-07-17

Use this guide after implementation to prove the feature end-to-end. Contracts: [cli.md](./contracts/cli.md), [graph-json.md](./contracts/graph-json.md). Data model: [data-model.md](./data-model.md).

## Prerequisites

- Python 3.11+
- Repo checkout with this feature implemented
- A portable schema `6.0.0` graph (index a small fixture, or use `tests/fixtures/explain_graphs/` when present)
- Optional: local Ollama with the configured model for summary scenarios
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
FIX=tests/fixtures/llm_project   # or tests/fixtures/explain_graphs
OUT=/tmp/grapheinstein-008
mkdir -p "$OUT"
grapheinstein index "$FIX" --output "$OUT/graph.json"
# Prefer a graph that contains a known concept node (e.g. after --enrich-llm) or clear symbol names
```

## Scenario A — Match + subgraph (no LLM required)

```bash
grapheinstein explain "auth" --input "$OUT/graph.json" --output "$OUT/sub.json" --no-summary
python -c "
import json
d=json.load(open('$OUT/sub.json'))
assert d['schema_version']=='6.0.0'
assert d['graph']['explained_concept'].lower()=='auth'
assert d['graph']['explain_match_ids']
assert d['graph']['explain_hops'] in (1,2)
assert d['nodes'] and all('metadata' in n for n in d['nodes'])
assert all(k in e for e in d['links'] for k in ('type','provenance'))
"
echo $?
```

**Expected**:
- Exit code `0`
- Valid schema `6.0.0` subgraph with explain metadata
- At least one match id; edges retain provenance
- No cloud calls

## Scenario B — Hop depth 1 vs 2

```bash
grapheinstein explain "auth" -i "$OUT/graph.json" -o "$OUT/h1.json" --hops 1 --no-summary
grapheinstein explain "auth" -i "$OUT/graph.json" -o "$OUT/h2.json" --hops 2 --no-summary
python -c "
import json
n1=len(json.load(open('$OUT/h1.json'))['nodes'])
n2=len(json.load(open('$OUT/h2.json'))['nodes'])
assert n2 >= n1
"
```

**Expected**:
- Both succeed
- Hop-2 node count ≥ hop-1 for the same seed on a connected fixture

## Scenario C — Fuzzy approximate phrase

```bash
# Use a near-miss / partial for a known node label in the fixture
grapheinstein explain "autentication" -i "$OUT/graph.json" -o "$OUT/fuzzy.json" --no-summary
test -f "$OUT/fuzzy.json"
```

**Expected**:
- Exit `0` when the intended node is clearly best (fixture-dependent)
- Match ids include the intended target

## Scenario D — No match

```bash
rm -f "$OUT/nomatch.json"
grapheinstein explain "zzzx_not_a_real_concept_qqq" -i "$OUT/graph.json" -o "$OUT/nomatch.json" --no-summary
echo exit:$?
test ! -f "$OUT/nomatch.json"
```

**Expected**:
- Non-zero exit
- No success-looking file at `$OUT/nomatch.json`

## Scenario E — Summary with local LLM (optional)

```bash
# Requires Ollama + configured model locally
grapheinstein explain "auth" -i "$OUT/graph.json" -o "$OUT/sum.json"
# Summary text appears on the human-readable stream (stderr); subgraph still valid JSON
python -c "import json; json.load(open('$OUT/sum.json'))"
```

**Expected**:
- Exit `0` with subgraph written
- Natural-language summary on stderr grounded in neighborhood
- With Ollama stopped: subgraph still written; clear skip/fail message for summary; exit `0`

## Scenario F — Help surface

```bash
grapheinstein --help | grep -i explain
grapheinstein explain --help
```

**Expected**:
- `explain` listed; options include `--input`, `--output`, `--hops`

## Offline note

Scenarios A–D and F require no network. Scenario E uses localhost Ollama only when testing summaries.
