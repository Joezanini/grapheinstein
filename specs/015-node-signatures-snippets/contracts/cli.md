# Contract: CLI snippet controls

**Feature**: `015-node-signatures-snippets`  
**Command**: `grapheinstein index` (and the default index path that accepts the same options)

## Flags

| Flag | Type | Default | Effect |
|------|------|---------|--------|
| `--no-snippets` | bool | false | Omit `snippet` and `snippet_truncated` on code entities. Signatures still written for the four languages. |
| `--snippet-max-lines` | int | 40 | Line cap. Allowed range 1–40 inclusive. |
| `--snippet-max-bytes` | int | 2048 | UTF-8 byte cap. Allowed range 1–2048 inclusive. |

Flags override the same keys in `--config` / user config. Out-of-range values exit with a configuration error and do not write a success graph.

## Config keys

```yaml
snippets: true
snippet_max_lines: 40
snippet_max_bytes: 2048
```

`snippets: false` matches `--no-snippets`. `grapheinstein init` template documents the three keys.

## Unchanged

- `schema_version` written to `graph.json` is `6.0.0`.
- Human-readable logs stay on stderr. The graph stays on the declared output path.
- No new subcommand.

## Version

Product version `0.4.0` in `pyproject.toml`, `grapheinstein.__version__`, and `CHANGELOG.md`. This feature does not publish to PyPI.
