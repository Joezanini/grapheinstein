# Quickstart Validation: Contribution Documentation

**Feature**: `013-contribution-docs`  
**Date**: 2026-07-18

Use after implementation to prove the contribution entry point and guide meet the contract. Details: [contracts/docs.md](./contracts/docs.md), [data-model.md](./data-model.md).

## Prerequisites

- Repo checkout with this feature implemented
- Python 3.11+ and a virtualenv with `pip install -e ".[dev]"` (for contract tests)
- No cloud services required
- No local LLM required

## Scenario A — Discover from README

1. Open `README.md`.
2. Locate the `## Contributing` section.
3. Follow the link to `CONTRIBUTING.md`.

**Expected**: Section is easy to find among top-level headings; link opens an existing in-repo contribution guide.

## Scenario B — First-time contributor path (manual)

Read only `CONTRIBUTING.md` (plus any README sections it points to) and answer:

| Question | Expected |
|----------|----------|
| How do I set up? | Clear steps or pointer to Install (`venv` + `pip install -e ".[dev]"`) |
| What do I run to validate? | At least `pytest` |
| How do I submit? | Pull/merge request style process described |
| What can I work on? | Bug fixes, docs, tests, in-scope features listed |
| What is out of scope / needs discussion? | Large/architectural changes need prior discussion; principles bound cloud/CLI direction |

**Expected**: At least 4 of 5 questions answered explicitly (SC-003).

## Scenario C — Contract tests

```bash
cd /path/to/grapheinstein
source .venv/bin/activate   # or create venv + pip install -e ".[dev]"
pytest tests/contract/test_contributing_docs.py -q
```

**Expected**: Exit 0; asserts file existence, README link resolution, and required content markers.

## Scenario D — Optional extras are non-blocking

1. Confirm `CONTRIBUTING.md` states that optional `[serve]` (and similar extras) are not required for core contributions.
2. Confirm core validation path does not require starting `grapheinstein serve`.

**Expected**: A docs-only or core-CLI contributor can follow setup → `pytest` → propose without installing serve extras.

## Scenario E — Principles pointer

1. Open the principles section of `CONTRIBUTING.md`.
2. Follow the link to `.specify/memory/constitution.md`.

**Expected**: Link resolves; guide summarizes local-first / CLI-first / provenance / incremental scope in plain language.
