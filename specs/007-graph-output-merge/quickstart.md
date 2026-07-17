# Quickstart Validation: Valid Graph Output, Compression, Versioning & Merge

**Feature**: `007-graph-output-merge`  
**Date**: 2026-07-17

Use this guide after implementation to prove the feature end-to-end. Contracts: [cli.md](./contracts/cli.md), [graph-json.md](./contracts/graph-json.md). Data model: [data-model.md](./data-model.md).

## Prerequisites

- Python 3.11+
- Repo checkout with this feature implemented
- No cloud services required

## Setup

```bash
cd /path/to/grapheinstein
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Fixture

Use any small project (or `tests/fixtures/` sample). Example:

```bash
FIX=tests/fixtures/llm_project   # or another small fixture
OUT=/tmp/grapheinstein-007
mkdir -p "$OUT"
```

## Scenario A — Valid complete index output

```bash
grapheinstein index "$FIX" --output "$OUT/graph.json"
python -c "import json; d=json.load(open('$OUT/graph.json')); assert d['schema_version']=='6.0.0'; assert 'nodes' in d and 'links' in d; assert all('metadata' in n for n in d['nodes']); assert all(k in d['graph'] for k in ('project_root','generated_at'))"
echo $?
```

**Expected**:
- Exit code `0`
- Valid schema `6.0.0` envelope with nodes/links
- Every node has `metadata`; graph has `project_root` and `generated_at`
- Edges retain `type` and `provenance`

## Scenario B — Compression round-trip

```bash
grapheinstein index "$FIX" --output "$OUT/graph.json" --compress
test -f "$OUT/graph.json.gz"
python -c "import gzip,json; d=json.loads(gzip.open('$OUT/graph.json.gz','rt',encoding='utf-8').read()); assert d['schema_version']=='6.0.0'"
```

**Expected**:
- Writes `$OUT/graph.json.gz` (not plain JSON at the uncompressed path unless also written separately)
- Decompressed JSON validates like Scenario A

## Scenario C — Versioned snapshots

```bash
rm -f "$OUT"/graph_v*.json "$OUT"/graph.json
grapheinstein index "$FIX" --output "$OUT/graph.json" --versioned
grapheinstein index "$FIX" --output "$OUT/graph.json" --versioned
grapheinstein index "$FIX" --output "$OUT/graph.json" --versioned
ls "$OUT"/graph.json "$OUT"/graph_v1.json "$OUT"/graph_v2.json "$OUT"/graph_v3.json
```

**Expected**:
- `graph.json` exists (latest)
- `graph_v1.json` … `graph_v3.json` all exist
- Earlier `graph_vN` files unchanged after later runs (mtime/content stable for v1 after v2/v3)

With compression:

```bash
grapheinstein index "$FIX" --output "$OUT/vcomp/graph.json" --versioned --compress
# expect graph.json.gz and graph_v1.json.gz under $OUT/vcomp/
```

## Scenario D — Merge union

Index two graphs (two fixture dirs, or a second hand-crafted JSON that adds unique node ids). Identical duplicate nodes across inputs are fine (deduped).

```bash
grapheinstein index "$FIX" --output "$OUT/a.json"
# Prepare $OUT/b.json as a second valid schema 6.0.0 graph (disjoint ids preferred for a clear union check)
grapheinstein merge "$OUT/a.json" "$OUT/b.json" --output "$OUT/merged.json"
python -c "import json; d=json.load(open('$OUT/merged.json')); assert d['graph'].get('merged') is True; assert len(d['graph']['merged_from'])==2"
```

**Expected**:
- Exit `0`
- `graph.merged == true`, `merged_from` length 2
- Union of nodes/links; duplicates collapsed

## Scenario E — Merge conflict hard-fail

Prepare two JSON graphs that share a node `id` with different `type` or conflicting `metadata`. Then:

```bash
grapheinstein merge "$OUT/conflict_a.json" "$OUT/conflict_b.json" --output "$OUT/should_not_exist.json"
echo $?
test ! -f "$OUT/should_not_exist.json"
```

**Expected**:
- Non-zero exit
- Clear error naming the conflicting id
- No success file at the output path

## Scenario F — Mixed gzip inputs to merge

```bash
grapheinstein merge "$OUT/a.json" "$OUT/graph.json.gz" --output "$OUT/merged2.json" --compress
test -f "$OUT/merged2.json.gz"
```

**Expected**: Accepts plain + gzip inputs; writes compressed merged output.

## Automated checks

```bash
pytest tests/unit tests/contract tests/integration -q
```

Prefer dedicated unit tests for atomic write, version numbering, and merge conflicts so CI does not rely on manual temp dirs alone.
