# Query fixture graphs

| File | Purpose |
|------|---------|
| `auth_chunks.json` | Chunk-rich graph: `media_text` about authentication linked to `auth.py::check_auth` and `concept::authentication`. Question: "How does authentication work?" Expected primary hit includes `docs/auth.md::media_text::0`. With hops=1, subgraph should include the function neighbor. |
| `composed_only.json` | No `metadata.text` bodies — query via composed search text. Question: "configuration" / "How is configuration loaded?" Expected hit: `concept::configuration` or `config.py::load_settings`. |
| `noise_sparse.json` | Sparse unrelated symbols for no-evidence cases (e.g. nonsense questions). |

Defaults for validation: `--k 20`, `--hops 1`, `--match-threshold 0.40`, `--no-answer` for offline runs.
