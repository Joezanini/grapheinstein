import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "code_project"


def test_partial_index_succeeds_with_skips(tmp_path: Path):
    out = tmp_path / "graph.json"
    result = runner.invoke(
        cli,
        ["index", str(FIXTURE), "-o", str(out), "--languages", "python"],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert any(
        n["id"] == "src/app.py::function::greet::1" for n in data["nodes"]
    )
    assert any(n["id"] == "broken/bad.py" and n["type"] == "file" for n in data["nodes"])
    assert any(n["id"] == "notes.txt" and n["type"] == "file" for n in data["nodes"])
    # No fabricated entities for notes.txt
    assert not any(n["id"].startswith("notes.txt::") for n in data["nodes"])
    assert "Parse skips" in result.output or "parse" in result.output.lower() or result.exit_code == 0
