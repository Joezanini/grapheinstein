# Quickstart: Large Repo Guards

**Feature**: `014-large-repo-guards`  
**Purpose**: Validate end-to-end that code-only scoping, bounded references, and preflight reject work as specified.

## Prerequisites

- Installable local checkout of grapheinstein (editable install fine)
- `pytest` available
- No network required

## Fixture

Create (or use tests fixture) `tests/fixtures/large_repo_guards/`:

```text
large_repo_guards/
├── pkg/
│   ├── __init__.py
│   ├── a.py          # contains whole-token mention of b.py
│   └── b.py
├── docs/
│   └── dyn/
│       └── page_0001.html … page_N.html   # many small HTML files
└── discovery_cache/
    └── service.json                       # bulky JSON
```

Aim for thousands of HTML files under `docs/dyn/` so the tree resembles the incident proportions while staying small enough for CI (generate in test setup if needed).

## Scenario A — Code-only completes fast

```bash
grapheinstein index tests/fixtures/large_repo_guards \
  --code-only \
  --output /tmp/guards-code-only.json
```

**Expect**:
- Exit `0`
- Graph written; nodes include `pkg/a.py`, `pkg/b.py`
- No nodes under `docs/` or `discovery_cache/`
- `references` edge `pkg/a.py` → `pkg/b.py` when mention present
- Wall clock well under 2 minutes on a laptop

## Scenario B — Opt in to generated docs

```bash
grapheinstein index tests/fixtures/large_repo_guards \
  --code-only \
  --include-generated-docs \
  --allow-large-repo \
  --output /tmp/guards-with-docs.json
```

**Expect**:
- Generated paths may appear in inventory (subject to size/ops gates)
- Without `--allow-large-repo`, a sufficiently large dump SHOULD exit with preflight reject (`2`) instead of hanging

## Scenario C — Preflight reject without override

Use a config that disables code-only default ignores but keeps a low `max_reference_scan_ops` (e.g. `1000`), indexing the fixture **without** `--code-only` so HTML is eligible:

```bash
grapheinstein index tests/fixtures/large_repo_guards \
  --config /path/to/low-ops.yaml \
  --output /tmp/should-not-write.json
```

**Expect**:
- Non-zero exit (preflight / large-repo reject)
- Clear stderr mentioning scan cost or non-code share and remediation
- No successful complete graph at the output path
- Completes in under 30 seconds

## Scenario D — Oversize / cap bounds

Add one huge UTF-8 file marked oversize via low `max_file_size`, and one eligible code file larger than `max_reference_scan_bytes` with a mention only past the cap.

**Expect**:
- Oversize file not fully read for references
- Mention only beyond the byte cap does not create an edge; mention within the cap does

## Scenario E — Regression happy path

Small project without doc dumps (existing code fixture):

```bash
grapheinstein index tests/fixtures/<existing-code-fixture> -o /tmp/guards-regression.json
```

**Expect**: Existing reference edges among unique basenames still appear (SC-006).

## Automated checks

```bash
pytest tests/unit/test_references.py \
       tests/unit/test_ignore_patterns.py \
       tests/unit/test_preflight_scan_cost.py \
       tests/integration/test_cli_large_repo_guards.py \
       tests/contract/test_cli_index_guards.py -q
```

See [contracts/cli.md](./contracts/cli.md) and [data-model.md](./data-model.md) for thresholds and entity rules.
