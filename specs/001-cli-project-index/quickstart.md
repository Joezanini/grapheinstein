# Quickstart Validation: CLI Project Index Skeleton

**Feature**: `001-cli-project-index`  
**Date**: 2026-07-16

Use this guide after implementation to prove the feature end-to-end. Contracts: [cli.md](./contracts/cli.md), [graph-json.md](./contracts/graph-json.md). Data model: [data-model.md](./data-model.md).

## Prerequisites

- Python 3.11+
- Repo checkout with this feature implemented
- No network required after dependencies are installed

## Setup

```bash
cd /path/to/grapheinstein
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

If extras differ, install the package editable with pytest available.

## Fixture project

Create or use `tests/fixtures/sample_project/`:

```text
sample_project/
├── .gitignore          # contains: ignored_dir/
├── README.md
├── src/
│   └── main.py
└── ignored_dir/
    └── secret.txt
```

## Scenario A — Default index invocation

```bash
grapheinstein tests/fixtures/sample_project --output /tmp/grapheinstein-sample.json
echo $?
```

**Expected**:
- Exit code `0`
- File `/tmp/grapheinstein-sample.json` exists
- JSON has `schema_version` `1.0.0`
- Nodes include `README.md` and `src/main.py` (and directory nodes)
- Nodes do **not** include `ignored_dir` or `ignored_dir/secret.txt`
- Links use `type: contains` and `provenance: extracted`

## Scenario B — Explicit `index` subcommand

```bash
grapheinstein index tests/fixtures/sample_project -o /tmp/grapheinstein-sample2.json
```

**Expected**: Same inventory semantics as Scenario A (equivalent outcome).

## Scenario C — Status after index

```bash
grapheinstein status --output /tmp/grapheinstein-sample.json
echo $?
```

**Expected**:
- Exit code `0`
- Human summary shows file count, directory count, total nodes
- Counts match the JSON node list filtered by `kind`

## Scenario D — Status when missing

```bash
grapheinstein status --output /tmp/does-not-exist-graph.json
echo $?
```

**Expected**:
- Exit code `2`
- Message indicates no index / file not found
- Process does not crash

## Scenario E — Defaults without user config

```bash
# Ensure ~/.grapheinstein/config.yaml is absent or temporarily moved
grapheinstein index tests/fixtures/sample_project
```

**Expected**:
- Exit code `0`
- `graph.json` written under the current working directory
- Command succeeds with only project path (and optional `-o`)

## Scenario F — Explicit config

```bash
mkdir -p /tmp/gcfg
cat > /tmp/gcfg/config.yaml <<'EOF'
output: /tmp/from-config.json
log_level: DEBUG
EOF
grapheinstein index tests/fixtures/sample_project --config /tmp/gcfg/config.yaml
```

**Expected**:
- Graph written to `/tmp/from-config.json` unless `-o` overrides
- Invalid YAML in config path → exit `1` with clear error

## Scenario G — Offline check

```bash
# Optional: disable network in the environment, then re-run Scenario A
grapheinstein index tests/fixtures/sample_project -o /tmp/offline-graph.json
```

**Expected**: Succeeds with no network access.

## Scenario H — Automated tests

```bash
pytest
```

**Expected**: Unit, integration, and contract tests pass (ignore rules, graph shape, CLI exit codes).

## Pass criteria

All scenarios A–F and H pass; G passes when offline tooling is available. This matches success criteria SC-001–SC-006 in [spec.md](./spec.md) at a practical validation level.
