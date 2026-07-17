# Quickstart Validation: Directed File Graph Index & Visualize

**Feature**: `002-digraph-index-visualize`  
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

## Fixture project

Use/extend `tests/fixtures/sample_project/`:

```text
sample_project/
├── .gitignore          # contains: ignored_dir/
├── README.md           # whole-token mention of unique file basename, e.g. main.py
├── src/
│   └── main.py
└── ignored_dir/
    └── secret.txt
```

Optional: add a symlink file under the fixture (or create in a temp copy during the scenario) to verify symlink-as-file / no follow.

## Scenario A — Index with contains + references

```bash
grapheinstein index tests/fixtures/sample_project --output /tmp/grapheinstein-v2.json
echo $?
```

**Expected**:
- Exit code `0`
- File exists with `schema_version` `"2.0.0"`
- Nodes use `type` of `file` or `dir` and include `metadata`
- Nodes include `README.md` and `src/main.py`; exclude ignored paths
- Links include `contains` edges for the directory tree
- Links include a `references` edge from `README.md` to `src/main.py` when README contains a whole-token `main.py`
- Re-running the same command overwrites `/tmp/grapheinstein-v2.json` without prompting

## Scenario B — Visualize console summary

```bash
grapheinstein visualize --input /tmp/grapheinstein-v2.json
echo $?
```

**Expected**:
- Exit code `0`
- Summary shows file/dir/total node counts matching the JSON
- Summary shows `contains` and `references` edge counts matching the JSON `links`

## Scenario C — Visualize with DOT export

```bash
grapheinstein visualize --input /tmp/grapheinstein-v2.json --dot /tmp/grapheinstein-v2.dot
echo $?
```

**Expected**:
- Exit code `0`
- Console summary still printed
- `/tmp/grapheinstein-v2.dot` exists and contains every node id and every edge from the JSON (by label/endpoints)
- Re-run overwrites the DOT file without prompting

## Scenario D — Reject old schema

Given a v1-shaped graph (e.g. nodes with `kind` / `directory`, `schema_version` `1.0.0`):

```bash
grapheinstein visualize --input /path/to/old-graph.json
echo $?
```

**Expected**:
- Non-zero exit
- Error message indicates unsupported format / re-index required
- No silent coercion of fields

## Scenario E — Whole-token negative case

In a temp fixture, put text that only contains a basename as a substring inside a longer token (e.g. file `main` mentioned only inside `domain` or ensure `main` is not a whole token). Index and confirm **no** spurious `references` edge for that pair.

## Scenario F — Symlink not followed

In a temp project, create `link_to_elsewhere` → a directory outside or a nested tree that would add many nodes if followed. Index and confirm:
- `link_to_elsewhere` appears as `type: file` (optionally `metadata.symlink: true`)
- Nodes from the symlink target are **not** added via the link

## Scenario G — Offline / errors

- Index with missing project path → non-zero, clear error, no success graph written
- Visualize with missing `--input` file → non-zero, clear error
- Disconnect network (optional) and re-run A–C → still succeeds once installed

## Done criteria

All scenarios A–F pass; contracts and data model rules hold for produced artifacts.
