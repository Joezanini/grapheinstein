import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import app, app_typer

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "docs_pdf_project"
runner = CliRunner()


def _heading_sources(data: dict) -> set[str]:
    return {
        n["metadata"]["source"]
        for n in data["nodes"]
        if n["type"] == "heading"
    }


def test_default_no_structure(tmp_path: Path):
    out = tmp_path / "default.json"
    result = runner.invoke(app_typer, ["index", str(FIXTURE), "-o", str(out)])
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text())
    assert data["schema_version"] == "4.0.0"
    assert not any(n["type"] == "heading" for n in data["nodes"])
    assert data["graph"]["include_docs"] is False
    assert data["graph"]["include_pdfs"] is False


def test_docs_only(tmp_path: Path):
    out = tmp_path / "docs.json"
    result = runner.invoke(
        app_typer, ["index", str(FIXTURE), "--include-docs", "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    sources = _heading_sources(json.loads(out.read_text()))
    assert "markdown" in sources or "txt" in sources or "rst" in sources
    assert "pdf" not in sources


def test_pdfs_only(tmp_path: Path):
    out = tmp_path / "pdfs.json"
    result = runner.invoke(
        app_typer, ["index", str(FIXTURE), "--include-pdfs", "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    sources = _heading_sources(json.loads(out.read_text()))
    assert "pdf" in sources
    assert "markdown" not in sources


def test_both_flags(tmp_path: Path):
    out = tmp_path / "both.json"
    result = runner.invoke(
        app_typer,
        ["index", str(FIXTURE), "--include-docs", "--include-pdfs", "-o", str(out)],
    )
    assert result.exit_code == 0, result.output
    sources = _heading_sources(json.loads(out.read_text()))
    assert "pdf" in sources
    assert sources & {"markdown", "txt", "rst"}


def test_default_path_alias_with_flags(tmp_path: Path):
    out = tmp_path / "alias.json"
    # Use app() rewriter path
    from grapheinstein.cli import prepend_index_if_needed

    args = prepend_index_if_needed(
        [str(FIXTURE), "--include-docs", "-o", str(out)]
    )
    assert args[0] == "index"
    assert "--include-docs" in args
    result = runner.invoke(app_typer, args)
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text())
    assert any(n["type"] == "heading" for n in data["nodes"])


def test_ignored_docs_not_structured(tmp_path: Path):
    out = tmp_path / "ign.json"
    result = runner.invoke(
        app_typer, ["index", str(FIXTURE), "--include-docs", "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text())
    assert not any("ignored_docs" in n["id"] for n in data["nodes"])
