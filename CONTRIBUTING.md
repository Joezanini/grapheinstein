# Contributing to Grapheinstein

Thanks for your interest in improving Grapheinstein. Community contributions are welcome. Please be respectful and constructive in issues and reviews.

## Welcome / what we accept

Useful contributions include:

- **Bug fixes** — incorrect behavior, crashes, or misleading errors
- **Documentation** — README, guides, comments, and examples that help users and agents
- **Tests** — coverage for parsers, graph contracts, CLI, and regression cases
- **Features** — small, focused improvements aligned with project principles (see below)

If you are unsure whether an idea fits, open an issue first.

## Development setup

Core contributor setup matches the project [README](README.md) Install section:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

You do **not** need optional extras for most contributions. Packages such as `grapheinstein[serve]` (local HTTP) or media-related extras are only required when you are changing those optional surfaces.

## Validate before proposing

Before you open a pull request, run the project’s standard checks from the [README](README.md) Validation section:

```bash
pytest
ruff check src tests
```

Lint rules live in `pyproject.toml` under `[tool.ruff]` / `[tool.ruff.lint]` (Pyflakes, pycodestyle, isort, pyupgrade, bugbear). Auto-fix safe issues with `ruff check src tests --fix`. Optional format check: `ruff format --check src tests`.

Fix failures related to your change. If a failure looks unrelated or flaky, note it in the PR description.

## Propose a change

1. Fork the repository (if you do not have write access) and create a focused branch from an up-to-date `main`.
2. Make your changes with clear commits.
3. Run `pytest` and `ruff check src tests` locally.
4. Open a **pull request** (or merge request) against `main`.

Reviewers typically look for:

- Clear problem statement and scope
- Tests or docs updated when behavior or contracts change
- Alignment with project principles (local-first, CLI-first, no mandatory cloud)
- No unrelated refactors mixed into the same PR

## Discuss large changes first

For **large** or **architectural** work (new required services, major CLI redesign, graph schema breaks, mandatory cloud dependencies), please **discuss** in an **issue** before investing substantial implementation effort. Early feedback saves time and keeps the project direction coherent.

## Project principles

Grapheinstein is a local-first, offline-capable CLI that builds a portable, provenance-labeled knowledge graph. Contributions should respect:

- **Local-first / offline** — core workflows must not require cloud APIs
- **CLI-first** — new capability belongs behind the `grapheinstein` CLI (and shared library APIs), not a divergent parallel interface
- **Provenance-labeled graph** — edges stay typed and labeled `extracted` or `inferred`; keep `graph.json` portable
- **Incremental simplicity** — prefer the thin local stack; justify optional complexity

Authoritative detail: [.specify/memory/constitution.md](.specify/memory/constitution.md).

## Optional extras

Optional dependency groups (for example `[serve]` for `grapheinstein serve`) are **not** required for core CLI, docs, or test contributions. Install them only when your change targets that optional surface:

```bash
pip install -e ".[dev,serve]"
```

## Release (maintainers)

Releases publish to PyPI via GitHub Actions Trusted Publishing when a version tag is pushed.

1. Bump the version in **both** `pyproject.toml` (`[project].version`) and `src/grapheinstein/__init__.py` (`__version__`).
2. Commit the bump (e.g. `Release 0.1.0`).
3. Tag and push:
   ```bash
   git tag v0.1.0
   git push origin main
   git push origin v0.1.0
   ```
4. The [Publish to PyPI](.github/workflows/publish.yml) workflow builds the sdist/wheel, smoke-tests `grapheinstein --help`, and uploads with OIDC.

### One-time PyPI Trusted Publisher setup

Before the first tag publish:

1. On [PyPI](https://pypi.org/), create the `grapheinstein` project (or use a pending publisher).
2. Add a Trusted Publisher:
   - Owner: `Joezanini`
   - Repository: `grapheinstein`
   - Workflow: `publish.yml`
   - Environment: `pypi`
3. In the GitHub repo, create an Environment named `pypi` (optional protection rules as you prefer).
