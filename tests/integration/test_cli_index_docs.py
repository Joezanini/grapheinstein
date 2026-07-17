import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import app_typer

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "docs_pdf_project"
runner = CliRunner()


def test_index_include_docs(tmp_path: Path):
    out = tmp_path / "graph.json"
    result = runner.invoke(
        app_typer,
        ["index", str(FIXTURE), "--include-docs", "--languages", "", "-o", str(out)],
    )
    # empty languages may fail - use a valid language or skip languages
    if result.exit_code != 0:
        result = runner.invoke(
            app_typer,
            ["index", str(FIXTURE), "--include-docs", "-o", str(out)],
        )
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text())
    headings = [n for n in data["nodes"] if n["type"] == "heading"]
    assert any(n["metadata"].get("file") == "docs/guide.md" for n in headings)
    assert any(n["metadata"].get("file") == "docs/notes.txt" for n in headings)
    assert any(n["metadata"].get("file") == "docs/overview.rst" for n in headings)
    assert not any("secret.md" in n["id"] for n in headings)
    assert any(link["type"] == "mentions" for link in data["links"])
    # PDF headings should not appear without --include-pdfs
    assert not any(n.get("metadata", {}).get("source") == "pdf" for n in headings)
