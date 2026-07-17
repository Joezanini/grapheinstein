import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "code_project"


def test_index_code_project_entities(tmp_path: Path):
    out = tmp_path / "graph.json"
    result = runner.invoke(
        cli,
        ["index", str(FIXTURE), "-o", str(out), "--languages", "python,go"],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "6.0.0"

    ids = {n["id"] for n in data["nodes"]}
    assert "src/app.py::function::greet::1" in ids
    assert "src/app.py::class::Greeter::5" in ids
    assert "src/app.py::method::hello::6" in ids
    assert "src/main.py::function::run::4" in ids
    assert "src/util.go::function::Add::3" in ids
    assert "ignored_dir/secret.py" not in ids

    links = data["links"]
    assert any(
        link["type"] == "imports"
        and link["source"] == "src/main.py"
        and "greet" in link["target"]
        for link in links
    )
    assert any(
        link["type"] == "calls"
        and link["source"] == "src/main.py::function::run::4"
        and link["target"] == "src/app.py::function::greet::1"
        for link in links
    )
    assert "Functions" in result.output
    assert "Defines edges" in result.output
