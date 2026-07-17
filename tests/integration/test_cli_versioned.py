from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()
SAMPLE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_project"


def test_index_versioned_three_runs(tmp_path: Path):
    out = tmp_path / "graph.json"
    for _ in range(3):
        result = runner.invoke(
            cli,
            ["index", str(SAMPLE), "--output", str(out), "--versioned"],
        )
        assert result.exit_code == 0, result.output
    assert out.exists()
    assert (tmp_path / "graph_v1.json").exists()
    assert (tmp_path / "graph_v2.json").exists()
    assert (tmp_path / "graph_v3.json").exists()
    v1 = (tmp_path / "graph_v1.json").read_text(encoding="utf-8")
    # fourth run should not change v1
    result = runner.invoke(cli, ["index", str(SAMPLE), "--output", str(out), "--versioned"])
    assert result.exit_code == 0
    assert (tmp_path / "graph_v1.json").read_text(encoding="utf-8") == v1
    assert (tmp_path / "graph_v4.json").exists()
