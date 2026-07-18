from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRIBUTING = ROOT / "CONTRIBUTING.md"
README = ROOT / "README.md"


def test_contributing_md_exists():
    assert CONTRIBUTING.is_file(), "CONTRIBUTING.md must exist at repository root"
    text = CONTRIBUTING.read_text(encoding="utf-8")
    assert text.strip(), "CONTRIBUTING.md must be non-empty"


def test_readme_contributing_section_links_to_guide():
    readme = README.read_text(encoding="utf-8")
    assert re.search(r"^##\s+Contributing\b", readme, flags=re.MULTILINE | re.IGNORECASE), (
        "README.md must include a level-2 Contributing heading"
    )
    assert re.search(r"contribut", readme, flags=re.IGNORECASE), (
        "README Contributing section should welcome contributions"
    )
    link = re.search(r"\[[^\]]*\]\(([^)]*CONTRIBUTING\.md)\)", readme)
    assert link, "README.md must link to CONTRIBUTING.md"
    target = (ROOT / link.group(1)).resolve()
    assert target.is_file(), f"README Contributing link must resolve: {link.group(1)}"


def test_contributing_covers_required_themes():
    text = CONTRIBUTING.read_text(encoding="utf-8")
    lower = text.lower()

    # Welcome types
    assert "bug" in lower
    assert "documentation" in lower or "docs" in lower
    assert "test" in lower
    assert "feature" in lower

    # Development setup
    assert "venv" in lower or "pip install" in lower
    assert "[dev]" in lower

    # Validation
    assert "pytest" in lower

    # Propose a change
    assert (
        "pull request" in lower
        or "merge request" in lower
        or re.search(r"\bpr\b", lower)
    )

    # Discuss large changes
    assert "discuss" in lower or "issue" in lower
    assert "large" in lower or "architect" in lower

    # Project principles
    assert "local-first" in lower or "offline" in lower
    assert "constitution" in lower or ".specify/memory/constitution.md" in lower

    # Optional extras
    assert "[serve]" in lower or ("optional" in lower and "serve" in lower)
