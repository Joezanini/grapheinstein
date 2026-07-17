# Quickstart Validation: Local LLM Entity & Relation Extraction

**Feature**: `006-ollama-llm-extraction`  
**Date**: 2026-07-17

Use this guide after implementation to prove the feature end-to-end. Contracts: [cli.md](./contracts/cli.md), [graph-json.md](./contracts/graph-json.md). Data model: [data-model.md](./data-model.md).

## Prerequisites

- Python 3.11+
- Repo checkout with this feature implemented
- **Ollama** installed and running locally (`http://localhost:11434` by default)
- A local model tag available (prefer `qwen3.5-2b-mlx:fp16-8gbGPU`, or pass `--llm-model` for any pulled tag)
- No cloud LLM APIs required

## Setup

```bash
cd /path/to/grapheinstein
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Ensure Ollama is up and the model exists (example):
ollama list
# ollama pull <your-model-tag>   # if needed
```

## Fixture project

Create/use `tests/fixtures/llm_project/` (illustrative layout):

```text
llm_project/
├── .gitignore                 # e.g. ignored/
├── src/
│   └── auth.py                # function validate_token (AST-extracted)
├── docs/
│   └── auth.md                # names "Auth Middleware"; describes validate_token role
└── ignored/
    └── secret.md              # must not be enriched
```

Suggested `docs/auth.md` content should literally include a distinctive phrase such as `Auth Middleware` and reference the validation behavior. Suggested `src/auth.py` should define `validate_token` and optionally `import jwt` / mention PyJWT for a `depends_on` case.

Unit/CI tests SHOULD inject a fake LLM responder so they do not require a live daemon; this quickstart assumes a real local Ollama for manual validation.

## Scenario A — Flag off (no LLM enrichment)

```bash
grapheinstein index tests/fixtures/llm_project --output /tmp/grapheinstein-v6-default.json
echo $?
```

**Expected**:
- Exit code `0`
- `schema_version` is `"6.0.0"`
- AST `function` nodes present for `auth.py` when languages include Python
- **No** `concept` nodes from this feature
- **No** `implements` / `depends_on` edges
- Zero Ollama calls (Ollama may be stopped; run must still succeed)
- `graph.enrich_llm` is false/absent

## Scenario B — `--enrich-llm` with local model

```bash
grapheinstein index tests/fixtures/llm_project \
  --include-docs \
  --enrich-llm \
  --llm-model qwen3.5-2b-mlx:fp16-8gbGPU \
  --output /tmp/grapheinstein-v6-llm.json
```

(If that model tag is not installed, substitute `--llm-model` with a tag from `ollama list`.)

**Expected**:
- Exit code `0`
- At least one `concept` node (e.g. Auth Middleware → `concept::auth-middleware`)
- At least one `implements` or enrichment `mentions` edge with `provenance`, `confidence` ∈ `[0,1]`, and non-empty `evidence`
- Ignored `secret.md` contributes no enrichment
- `graph.enrich_llm` is `true`; `graph.llm_model` reflects the model used
- Progress messages appear on stderr during enrichment for multi-file runs

## Scenario C — Missing model / Ollama down

```bash
grapheinstein index tests/fixtures/llm_project \
  --enrich-llm \
  --llm-model definitely-missing-model-tag-xyz \
  --output /tmp/grapheinstein-v6-skip.json
```

**Expected**:
- Exit code `0` (structural graph still written)
- Clear warning on stderr that enrichment was skipped / model unavailable
- Valid schema `6.0.0` graph with inventory/code structure
- No fabricated concept edges claiming enrichment succeeded

## Scenario D — Confidence / evidence contract sample

Inspect `/tmp/grapheinstein-v6-llm.json` (from Scenario B):

```bash
python - <<'PY'
import json
from pathlib import Path
g = json.loads(Path("/tmp/grapheinstein-v6-llm.json").read_text())
assert g["schema_version"] == "6.0.0"
enrichment_types = {"implements", "depends_on"}
for link in g["links"]:
    if link["type"] in enrichment_types or (
        link["type"] == "mentions"
        and "confidence" in link
    ):
        assert link["provenance"] in {"extracted", "inferred"}
        assert 0.0 <= float(link["confidence"]) <= 1.0
        assert isinstance(link["evidence"], str) and link["evidence"].strip()
print("enrichment edge contract ok")
PY
```

**Expected**: Script prints `enrichment edge contract ok` with no assertion failures.

## Scenario E — Load rejection of schema 5

```bash
# If you have a leftover schema 5 artifact:
grapheinstein status --graph /tmp/some-v5-graph.json
```

**Expected**: Non-zero or clear error instructing re-index for schema `6.0.0` (per existing status/load behavior).

## Done criteria

- [ ] Scenario A passes without Ollama
- [ ] Scenario B produces concept + enrichment edges with confidence/evidence offline
- [ ] Scenario C skips enrichment gracefully
- [ ] Scenario D contract assertions pass
- [ ] Scenario E rejects old schema artifacts
