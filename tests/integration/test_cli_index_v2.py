import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli, prepend_index_if_needed

runner = CliRunner()
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_project"


def test_index_writes_v2_with_references(tmp_path: Path):
    out = tmp_path / "graph.json"
    result = runner.invoke(cli, ["index", str(FIXTURE), "-o", str(out)])
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "3.0.0"
    assert any(n["id"] == "README.md" and n["type"] == "file" for n in data["nodes"])
    refs = [link for link in data["links"] if link["type"] == "references"]
    assert any(link["source"] == "README.md" and link["target"] == "src/main.py" for link in refs)


def test_default_path_writes_v2(tmp_path: Path):
    out = tmp_path / "g.json"
    result = runner.invoke(cli, prepend_index_if_needed([str(FIXTURE), "-o", str(out)]))
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "3.0.0"


def test_index_overwrites_without_prompt(tmp_path: Path):
    out = tmp_path / "graph.json"
    out.write_text(" stale ", encoding="utf-8")
    result = runner.invoke(cli, ["index", str(FIXTURE), "-o", str(out)])
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "3.0.0"
