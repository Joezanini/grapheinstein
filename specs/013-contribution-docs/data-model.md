# Data Model: Contribution Documentation

**Feature**: `013-contribution-docs`  
**Graph schema version**: `6.0.0` (unchanged — no graph entities affected)

This feature models **documentation artifacts**, not runtime graph nodes.

## Entities

### Contribution Guide

The dedicated community contribution document (`CONTRIBUTING.md`).

| Attribute | Rules |
|-----------|-------|
| `path` | Repository-relative `CONTRIBUTING.md` at root |
| `audience` | First-time and returning open-source contributors |
| `required_themes` | Welcome types; setup; validation; propose-change; large-change discussion; principles; optional extras note |
| `tone` | Plain language; ordered steps; no requirement to reverse-engineer source to learn the process |

**Validation**:

- File MUST exist at merge time.
- Each required theme MUST be present as a clear section or subsection (see [contracts/docs.md](./contracts/docs.md)).
- MUST NOT contradict README Install / Validation for core setup and `pytest`.

### README Contributing Entry Point

Short orientation block in `README.md`.

| Attribute | Rules |
|-----------|-------|
| `heading` | `## Contributing` (or equivalent level-2 heading with that label) |
| `body` | Brief welcome + link to Contribution Guide |
| `link_target` | Relative path `CONTRIBUTING.md` that resolves to an existing file |

**Validation**:

- Heading and working relative link MUST be present.
- MUST NOT introduce a second conflicting contribution destination.

### Project Principles Reference

Pointer from the Contribution Guide to published governance.

| Attribute | Rules |
|-----------|-------|
| `authority_path` | `.specify/memory/constitution.md` |
| `summary_topics` | Local-first / offline; CLI-first; provenance-labeled graph; incremental simplicity / no mandatory cloud |
| `mutation` | This feature does not edit the constitution |

**Relationships**:

```text
README Contributing Entry Point --links-to--> Contribution Guide
Contribution Guide --references--> Project Principles Reference
Contribution Guide --aligns-with--> README Install & Validation (content consistency)
```

## State Transitions

Documentation lifecycle for this feature (human/process, not runtime):

1. **Missing** → implementer adds `CONTRIBUTING.md` + README section → **Present**.
2. **Present** → contract tests pass → **Verified**.
3. **Verified** → later edits MUST keep README link and required themes (enforced by contract tests).

No runtime entity states.
