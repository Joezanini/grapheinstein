# Contract: Contribution Documentation

**Feature**: `013-contribution-docs`  
**Contract version**: `1.0.0`  
**Kind**: User-facing documentation (not CLI/HTTP)

## Files

| Path | Role | Required |
|------|------|----------|
| `CONTRIBUTING.md` | Full contribution guide | Yes |
| `README.md` | Discovery entry point (`## Contributing`) | Yes (additive section) |
| `.specify/memory/constitution.md` | Principles authority (linked, not modified) | Yes (pre-existing) |

## README Contributing section

MUST include:

1. A level-2 heading matching `/^##\s+Contributing\b/i` (exact title preferred: `## Contributing`).
2. A relative Markdown link whose target resolves to `CONTRIBUTING.md` (e.g. `[...](CONTRIBUTING.md)`).
3. At least one welcoming sentence indicating community contributions are accepted.

MUST NOT:

- Link only to an external wiki as the sole guide (in-repo guide is required).
- Point the primary Contributing link at a different path than `CONTRIBUTING.md`.

## CONTRIBUTING.md required content

The guide MUST address each theme below. Headings may vary; contract tests MAY match on heading text **or** distinctive phrases listed under “Markers”.

| Theme | Intent | Suggested markers (any sufficient) |
|-------|--------|------------------------------------|
| Welcome types | Bug fixes, docs, tests, features in scope | `bug`, `documentation` / `docs`, `test`, `feature` |
| Development setup | How to get a dev environment | `venv` or `pip install`, and `[dev]` |
| Validation | What to run before proposing | `pytest` |
| Propose a change | PR/MR-style community process | `pull request` or `merge request` or `PR` |
| Discuss large changes | Ask before big/architectural work | `discuss` / `issue` + `large` / `architect` |
| Project principles | Local-first CLI tool constraints | `local-first` or `offline`, and `constitution` or `.specify/memory/constitution.md` |
| Optional extras | Core vs optional deps | `[serve]` or `optional` + `serve` |

## Consistency rules

- Setup guidance MUST be compatible with README Install (`pip install -e ".[dev]"` as the core contributor path).
- Validation guidance MUST include the same primary check as README Validation (`pytest`).
- Optional serve/media extras MUST be described as non-blocking for core contributions.
- Graph schema version and CLI behavior are **out of contract** for this feature (unchanged).

## Automated checks

`tests/contract/test_contributing_docs.py` SHOULD enforce:

1. `CONTRIBUTING.md` exists and is non-empty UTF-8 text.
2. Each required theme has at least one matching marker (case-insensitive search acceptable).
3. `README.md` has the Contributing heading and a resolvable relative link to `CONTRIBUTING.md`.

Pattern reference: `tests/contract/test_agent_docs.py`.
