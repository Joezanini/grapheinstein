# Quickstart Validation: Config, Cache & Init Polish

**Feature**: `011-config-cache-init`  
**Date**: 2026-07-17

Use this guide after implementation to prove the feature end-to-end. Contract: [cli.md](./contracts/cli.md). Data model: [data-model.md](./data-model.md).

## Prerequisites

- Python 3.11+
- Repo checkout with this feature implemented
- Writable temp directories (do not use a real `~/.grapheinstein` if you want isolation — point `--output` / `--config` / `cache_dir` at `/tmp`)
- No cloud services required

## Setup

```bash
cd /path/to/grapheinstein
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Scenario A — `init` creates starter config

```bash
OUT=/tmp/grapheinstein-011
mkdir -p "$OUT"
rm -f "$OUT/config.yaml"
grapheinstein init --output "$OUT/config.yaml"
test -f "$OUT/config.yaml"
grep -E 'ignored_patterns|embedding_model|llm_model|max_file_size|cache_dir' "$OUT/config.yaml"
grapheinstein init --output "$OUT/config.yaml"; echo exit:$?
grapheinstein init --output "$OUT/config.yaml" --force
```

**Expected**:

- First init exit `0`; file contains the five keys (with comments)
- Second init without `--force` exits non-zero and does not truncate the file unexpectedly
- `--force` overwrites successfully

## Scenario B — Config drives ignores, size limit, and cache dir

```bash
FIX=tests/fixtures/sample_project   # or tests/fixtures/config_cache when present
cat > "$OUT/config.yaml" <<EOF
ignored_patterns:
  - "secret_dir/"
  - "*.skipme"
max_file_size: 100
embedding_model: "qwen3.5-2b-mlx:fp16-8gbGPU"
llm_model: "qwen3.5-2b-mlx:fp16-8gbGPU"
cache_dir: "$OUT/cache"
output: "$OUT/graph.json"
log_level: "INFO"
EOF
# Ensure fixture has a path matching ignored_patterns and a file > 100 bytes, or use config_cache fixture
grapheinstein index "$FIX" --config "$OUT/config.yaml"
python -c "
import json, pathlib
p=pathlib.Path('$OUT/graph.json')
assert p.exists()
d=json.load(open(p))
ids=[n['id'] for n in d['nodes']]
assert not any('secret_dir' in i for i in ids)
oversized=[n for n in d['nodes'] if n.get('metadata',{}).get('skipped')=='oversize']
# If fixture includes an oversize file, expect at least one skipped marker
print('nodes', len(d['nodes']), 'oversize_marked', len(oversized))
assert pathlib.Path('$OUT/cache').exists()
"
```

**Expected**:

- Exit `0`
- Config-ignored paths absent from node ids
- `cache_dir` created and populated after index
- Oversize files (when present in fixture) marked `metadata.skipped: "oversize"` without structure children

## Scenario C — Cache hit on unchanged re-index

```bash
/usr/bin/time -p grapheinstein index "$FIX" --config "$OUT/config.yaml" --output "$OUT/graph2.json" 2>"$OUT/cold.txt"
/usr/bin/time -p grapheinstein index "$FIX" --config "$OUT/config.yaml" --output "$OUT/graph3.json" 2>"$OUT/warm.txt"
# Inspect stderr summaries for cache hits; warm wall time should be lower on a ≥200-file project
grep -i cache "$OUT/warm.txt" || true
```

**Expected**:

- Both runs exit `0`
- Warm run reports cache hits (or equivalent) and is faster on a large enough tree (SC-002 target on ≥200 files)

## Scenario D — Help completeness and bad config errors

```bash
grapheinstein --help | grep -i init
grapheinstein init --help
grapheinstein index --help
printf 'max_file_size: 0\n' > "$OUT/bad.yaml"
grapheinstein index "$FIX" --config "$OUT/bad.yaml"; echo exit:$?
```

**Expected**:

- Help lists `init` and documents options/defaults
- Invalid `max_file_size` → non-zero exit; error names the key; no stack-only failure

## Scenario E — Offline / no cloud

```bash
# With network disabled if available in your environment, or simply without configuring any remote API:
grapheinstein init --output "$OUT/offline.yaml" --force
grapheinstein index "$FIX" --config "$OUT/offline.yaml" --output "$OUT/offline-graph.json"
```

**Expected**: Success without any required cloud service.

## Automated tests (after implementation)

```bash
pytest tests/unit/test_config.py tests/unit/test_cache.py tests/contract/test_cli_init.py tests/integration/test_cli_config_cache.py -q
```
