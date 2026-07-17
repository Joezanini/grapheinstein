from pathlib import Path

from grapheinstein.core.parsers.docs import extract_docs_structure

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "docs_pdf_project"


def test_extract_markdown_headings_and_links():
    headings, links = extract_docs_structure(FIXTURE / "docs" / "guide.md")
    names = [h.name for h in headings]
    assert names == ["Guide", "Installation", "Steps"]
    assert headings[0].level == 1
    assert headings[1].level == 2
    assert headings[2].level == 3
    assert any("README.md" in link.target for link in links)
    assert all(h.source == "markdown" for h in headings)


def test_extract_txt_underlined_headings():
    headings, _links = extract_docs_structure(FIXTURE / "docs" / "notes.txt")
    names = [h.name for h in headings]
    assert "Notes" in names
    assert "Details" in names
    assert all(h.source == "txt" for h in headings)


def test_extract_rst_headings():
    headings, _links = extract_docs_structure(FIXTURE / "docs" / "overview.rst")
    names = [h.name for h in headings]
    assert "Overview" in names
    assert "Getting Started" in names
    assert all(h.source == "rst" for h in headings)
