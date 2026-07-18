# Research: Contribution Documentation

**Feature**: `013-contribution-docs`  
**Date**: 2026-07-18

## R1 — Contribution guide location

**Decision**: Add a top-level `CONTRIBUTING.md` at the repository root. Link it from a new `## Contributing` section in `README.md`.

**Rationale**: Spec FR-001/FR-002 need a dedicated guide plus a README entry point. Root `CONTRIBUTING.md` is the de-facto open-source convention and is auto-linked by major git hosts on the repository homepage. The project already uses `docs/` for specialized playbooks (`docs/agent-integration.md`); contribution discovery benefits more from the conventional root filename than from nesting under `docs/`.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| `docs/contributing.md` only | Works, but weaker host auto-discovery; inconsistent with “standard community” expectation for `CONTRIBUTING.md` |
| Inline all contribution content in README | Bloats README; harder to keep a focused contributor path |
| Both root + docs duplicate | Violates FR-008 (single consistent destination) |

## R2 — Content outline (required sections)

**Decision**: `CONTRIBUTING.md` MUST include these sections (exact headings may vary slightly but content must be present and findable):

1. **Welcome / what we accept** — bug fixes, docs, tests, features aligned with project principles
2. **Development setup** — point to or briefly restate Install (`python -m venv`, `pip install -e ".[dev]"`); note optional `[serve]` is not required for core contributions
3. **Validate before proposing** — at minimum `pytest`, aligned with README Validation
4. **Propose a change** — fork/branch → pull/merge request style workflow in plain language; what reviewers look for at a high level
5. **Discuss large changes first** — advise opening an issue/discussion before large or architectural work
6. **Project principles** — short summary (local-first, CLI-first, provenance-labeled graph, incremental scope) plus link to `.specify/memory/constitution.md`
7. **Optional extras** — clarify that `grapheinstein[serve]` / media-related extras are only needed when contributing to those surfaces

**Rationale**: Maps directly to FR-002–FR-007 and User Stories 2–3. Mirrors the five SC-003 first-time questions.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Minimal “PRs welcome” stub | Fails SC-002/SC-003 and FR-002 depth |
| Full developer handbook (architecture deep-dive) | Out of scope; Spec Kit / `specs/*` already hold design depth |
| Formal Code of Conduct + security policy in this feature | Spec assumptions exclude new CoC/security channel unless already present (none today) |

## R3 — README Contributing section shape

**Decision**: Add a short `## Contributing` section near the end of `README.md` (after Validation is a natural placement), containing:

- One or two sentences welcoming contributions
- A link to [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Optional one-line pointer that `pytest` remains the standard check (already under Validation; do not duplicate the full install block)

**Rationale**: Matches FR-001 and the existing Agent integration pattern (short README blurb + link to dedicated doc). Keeps README skim-friendly (SC-001).

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Only a footer link without a heading | Harder to discover; weak against SC-001 |
| Duplicate the entire guide in README | Redundant; maintenance drift risk (FR-008) |

## R4 — Verification approach

**Decision**: Add `tests/contract/test_contributing_docs.py` modeled on `tests/contract/test_agent_docs.py`:

- Assert `CONTRIBUTING.md` exists
- Assert required content markers / section themes are present (setup, pytest/validation, propose/PR, principles/constitution, welcome contribution types)
- Assert `README.md` contains a Contributing heading and a relative link to `CONTRIBUTING.md`
- Resolve the README link target and assert the file exists (SC-004)

**Rationale**: Spec success criteria are documentation outcomes; a lightweight contract test prevents silent link rot and missing sections without inventing a docs site build.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Manual review only | Regresses easily; project already contracts agent docs |
| Full markdown lint / link-checker CI suite | Heavier than this feature needs; can come later |

## R5 — Principles reference (no constitution edit)

**Decision**: Contribution docs **link to** `.specify/memory/constitution.md` and summarize the four contributor-relevant constraints in plain language. Do **not** amend constitution version or templates in this feature.

**Rationale**: FR-006 requires pointing contributors at published principles; governance amendments are a separate process. Summarizing in CONTRIBUTING avoids forcing every first-time contributor to read the full Spec Kit constitution first, while still naming the authority document.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Copy entire constitution into CONTRIBUTING | Drift risk; wrong ownership |
| Omit constitution link | Fails FR-006 / User Story 3 |
