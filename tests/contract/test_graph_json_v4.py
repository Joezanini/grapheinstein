import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from grapheinstein.cli import app_typer
from grapheinstein.core.graph import SCHEMA_VERSION, GraphError, load_artifact
from grapheinstein.core.index import index_project

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "docs_pdf_project"
OLD_V3 = Path(__file__).resolve().parents[1] / "fixtures" / "old_schema_v3_graph.json"
runner = CliRunner()


def test_v4_heading_nodes_and_provenance(tmp_path: Path):
    out = tmp_path / "graph.json"
    index_project(FIXTURE, out, languages=[], include_docs=True, include_pdfs=False)
    data = load_artifact(out)
    assert data["schema_version"] == "4.0.0"
    assert SCHEMA_VERSION == "4.0.0"
    assert data["graph"]["include_docs"] is True
    assert data["graph"]["include_pdfs"] is False

    headings = [n for n in data["nodes"] if n["type"] == "heading"]
    assert headings
    assert any(n["metadata"]["name"] == "Installation" for n in headings)
    assert any(n["metadata"]["source"] == "markdown" for n in headings)

    for link in data["links"]:
        if link["type"] in {"section_of", "mentions"}:
            assert link["provenance"] == "extracted"
    assert any(link["type"] == "section_of" for link in data["links"])
    assert any(link["type"] == "mentions" for link in data["links"])


def test_reject_v3_artifact():
    with pytest.raises(GraphError, match="unsupported|Re-index|schema_version"):
        load_artifact(OLD_V3)


def test_include_flags_metadata_via_cli(tmp_path: Path):
    out = tmp_path / "graph.json"
    result = runner.invoke(
        app_typer,
        ["index", str(FIXTURE), "--include-docs", "--include-pdfs", "-o", str(out)],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text())
    assert data["graph"]["include_docs"] is True
    assert data["graph"]["include_pdfs"] is True
