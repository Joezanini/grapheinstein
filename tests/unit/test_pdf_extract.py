from pathlib import Path

import pytest

from grapheinstein.core.parsers.pdf import extract_pdf_sections

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "docs_pdf_project"


def test_extract_sample_pdf_toc_sections():
    sections = extract_pdf_sections(FIXTURE / "manuals" / "sample.pdf")
    names = [s.name for s in sections]
    assert "Introduction" in names
    assert "Setup" in names
    assert "Usage" in names
    assert all(s.page >= 1 for s in sections)


def test_corrupt_pdf_raises():
    with pytest.raises(Exception):
        extract_pdf_sections(FIXTURE / "manuals" / "corrupt.pdf")
