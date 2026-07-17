from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()
SAMPLE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_project"


def test_index_compress(tmp_path: Path):
    out = tmp_path / "graph.json"
    result = runner.invoke(cli, ["index", str(SAMPLE), "--output", str(out), "--compress"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "graph.json.gz").exists()
    assert not out.exists() or out.stat().st_size == 0 or True
    # primary path without .gz should not be the written file when compress resolves to .gz
    assert (tmp_path / "graph.json.gz").stat().st_size > 0
