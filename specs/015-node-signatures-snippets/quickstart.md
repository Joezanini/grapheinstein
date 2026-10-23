# Quickstart: Signatures and snippets

Local validation only. Do not clone external repositories and do not publish the package.

## Prerequisites

```bash
pip install -e ".[dev]"
```

Python 3.11+. No network during `pytest`.

## Unit checks

```bash
pytest tests/unit/test_signatures_python.py \
       tests/unit/test_signatures_javascript.py \
       tests/unit/test_signatures_typescript.py \
       tests/unit/test_signatures_dart.py \
       tests/unit/test_snippet_policy.py -q
```

Expected:

- Python: annotated parameters, keyword-only, `*args`, `**kwargs`, return annotation, decorator included in the snippet and excluded from `signature`.
- JavaScript: parameter names and `rest`, no invented types.
- TypeScript: `createTask`, `setCustomFieldValue`, and `createWebhook` keep positional kinds, collapsed object/union types, and declared return types. Overloads appear in `signature` in source order; `parameters` follow the implementation.
- Dart: positional, required named, optional named, optional positional, and a constructor. Class `signature` has type parameters and the base type, and no parameter list.
- Policy: default excerpt ≤ 40 lines and ≤ 2048 bytes; a tighter cap is honored; `--no-snippets` / `snippets: false` drops excerpts and keeps signatures; a secret basename has no `snippet`.

## Graph compatibility

Index a tiny fixture and confirm `schema_version` is `6.0.0`. Load a previously valid graph that has only `name`, `language`, `file`, and `start_line` and confirm it still loads.

## Operator surfaces

```bash
grapheinstein index ./fixture -o graph.json --no-snippets
grapheinstein index ./fixture -o graph.json --snippet-max-lines 10 --snippet-max-bytes 512
```

Config equivalent:

```yaml
snippets: false
snippet_max_lines: 10
snippet_max_bytes: 512
```

Values above 40 or 2048 fail configuration validation.

## Docs

- `README.md` describes the optional fields, defaults, disable switch, caps, and secret basenames.
- `docs/agent-integration.md` names `signature`, `parameters`, `return_type`, `snippet`, `snippet_truncated`, and `signature_truncated`.
- `CHANGELOG.md` has a `0.4.0` entry. `pyproject.toml` version is `0.4.0`.
