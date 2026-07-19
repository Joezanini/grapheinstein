# large_repo_guards fixture

Mimics a small Python package beside generated documentation and discovery-cache JSON.

## Layout

- `pkg/a.py`, `pkg/b.py` — source; `a.py` contains a whole-token mention of `b.py`
- `docs/dyn/*.html` — generated HTML dump (many small files)
- `discovery_cache/service.json` — discovery-cache style JSON

## Expected behavior (`--code-only`)

- Inventory includes `pkg/*`
- Inventory excludes `docs/` and `discovery_cache/`
- Graph includes `references` edge `pkg/a.py` → `pkg/b.py`

## Regenerating HTML dump

```bash
python3 -c "
from pathlib import Path
root = Path('tests/fixtures/large_repo_guards/docs/dyn')
root.mkdir(parents=True, exist_ok=True)
for i in range(200):
    (root / f'page_{i:04d}.html').write_text(
        f'<html><body>doc page {i}</body></html>\n', encoding='utf-8')
"
```
