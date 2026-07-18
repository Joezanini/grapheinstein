# config_cache fixture

Used by feature 011 (config/cache/init).

| Path | Expectation |
|------|-------------|
| `src/main.py` | Indexed normally |
| `secret_dir/` | Excluded when config has `ignored_patterns: ["secret_dir/"]` |
| `*.skipme` | Excluded when config has `ignored_patterns: ["*.skipme"]` |
| `ignored_by_git/` | Excluded by fixture `.gitignore` |
| `big_blob.bin` (250 bytes) | Marked `metadata.skipped: "oversize"` when `max_file_size: 100` |

Example config for tests:

```yaml
ignored_patterns:
  - "secret_dir/"
  - "*.skipme"
max_file_size: 100
cache_dir: "/tmp/gs-cache-test"
```
