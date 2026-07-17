from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_project"


def test_status_success_after_index(tmp_path: Path):
    out = tmp_path / "graph.json"
    indexed = runner.invoke(cli, ["index", str(FIXTURE), "-o", str(out)])
    assert indexed.exit_code == 0, indexed.output

    result = runner.invoke(cli, ["status", "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert "Files" in result.output
    assert "Directories" in result.output
    assert "Total nodes" in result.output


def test_status_missing_graph_exit_2(tmp_path: Path):
    missing = tmp_path / "missing.json"
    result = runner.invoke(cli, ["status", "--output", str(missing)])
    assert result.exit_code == 2
    assert "not found" in result.output.lower() or "No index" in result.output
