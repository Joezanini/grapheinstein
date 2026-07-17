# Quickstart Validation: Tree-sitter Code Parsers

**Feature**: `003-tree-sitter-parsers`  
**Date**: 2026-07-16

Use this guide after implementation to prove the feature end-to-end. Contracts: [cli.md](./contracts/cli.md), [graph-json.md](./contracts/graph-json.md). Data model: [data-model.md](./data-model.md).

## Prerequisites

- Python 3.11+
- Repo checkout with this feature implemented
- No network required after dependencies (including Tree-sitter grammar wheels) are installed

## Setup

```bash
cd /path/to/grapheinstein
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Fixture project

Create/use `tests/fixtures/code_project/` (illustrative layout):

```text
code_project/
├── .gitignore                 # e.g. ignored_dir/
├── src/
│   ├── app.py                 # def greet at a known line
│   ├── main.py                # imports app / calls greet
│   └── util.go                # exported Go function (second language)
├── broken/
│   └── bad.py                 # deliberately invalid Python
└── ignored_dir/
    └── secret.py
```

Document expected entity ids and line numbers in fixture README or test constants.

## Scenario A — Default languages extract structure

```bash
grapheinstein index tests/fixtures/code_project --output /tmp/grapheinstein-v3.json
echo $?
```

**Expected**:
- Exit code `0`
- `schema_version` is `"3.0.0"`
- File/dir inventory still present (`contains` edges)
- Function (and any class/method) nodes for `app.py` / `main.py` with correct `metadata.start_line`
- `defines` edges from files to those entities
- `imports` and/or `calls` edges for the controlled Python pair when uniquely resolvable
- Go function entity present when `util.go` defines one
- Ignored paths contribute no nodes/edges
- `provenance` on new code edges is `"extracted"`

## Scenario B — Restrict languages

```bash
grapheinstein index tests/fixtures/code_project --languages python --output /tmp/grapheinstein-v3-py.json
```

**Expected**:
- Code-entity nodes only from Python files
- `util.go` remains a `file` node but has no Go code-entity children
- Graph metadata MAY list `"languages": ["python"]`

## Scenario C — Invalid language fails closed

```bash
grapheinstein index tests/fixtures/code_project --languages python,brainfuck --output /tmp/should-not-exist.json
echo $?
```

**Expected**:
- Non-zero exit
- Error names the invalid language and valid set
- No success graph written at the output path (or prior file left unchanged if it existed—must not write a new “success” artifact for the failed run)

## Scenario D — Partial parse failure

With `broken/bad.py` present:

```bash
grapheinstein index tests/fixtures/code_project --languages python --output /tmp/grapheinstein-v3-partial.json
echo $?
```

**Expected**:
- Exit code `0`
- Valid entities from good Python files still present
- Warning/log indicates a skipped/failed structure extract
- `bad.py` may appear as a file node without fabricated entities

## Scenario E — Visualize enriched graph

```bash
grapheinstein visualize --input /tmp/grapheinstein-v3.json
echo $?
```

**Expected**:
- Exit code `0`
- Summary includes function/class/method counts and defines/imports/calls counts matching the JSON
- Does not crash on new node/edge kinds

## Scenario F — Reject schema 2.0.0

```bash
grapheinstein visualize --input /path/to/schema-2-graph.json
echo $?
```

**Expected**:
- Non-zero exit
- Unsupported format / re-index message
- No silent acceptance of `2.0.0`

## Scenario G — Config languages

With a temp config:

```yaml
languages:
  - go
```

```bash
grapheinstein index tests/fixtures/code_project --config /tmp/gs-config.yaml --output /tmp/grapheinstein-v3-go.json
```

**Expected**: Only Go structure entities; CLI `--languages` overrides this config when both are supplied.

## Scenario H — Offline

Disconnect network (optional) after install; re-run A–E → still succeeds.

## Done criteria

Scenarios A–G pass; produced artifacts match [graph-json.md](./contracts/graph-json.md) and [data-model.md](./data-model.md).
