import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import app_typer

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "docs_pdf_project"
runner = CliRunner()


def test_index_include_pdfs(tmp_path: Path):
    out = tmp_path / "graph.json"
    result = runner.invoke(
        app_typer,
        ["index", str(FIXTURE), "--include-pdfs", "-o", str(out)],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text())
    headings = [n for n in data["nodes"] if n["type"] == "heading"]
    pdf_headings = [n for n in headings if n["metadata"].get("source") == "pdf"]
    assert pdf_headings
    assert any(n["metadata"]["name"] == "Introduction" for n in pdf_headings)
    assert any(link["type"] == "section_of" for link in data["links"])
    # docs structure off
    assert not any(n["metadata"].get("source") == "markdown" for n in headings)
    assert data["graph"].get("parse_skips", 0) >= 1  # corrupt.pdf
