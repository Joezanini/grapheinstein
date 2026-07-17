from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "merge_graphs"


def test_merge_help_lists_output_and_compress():
    result = runner.invoke(cli, ["merge", "--help"])
    assert result.exit_code == 0
    assert "--output" in result.output
    assert "--compress" in result.output


def test_merge_success_writes_metadata(tmp_path: Path):
    out = tmp_path / "merged.json"
    result = runner.invoke(
        cli,
        [
            "merge",
            str(FIXTURES / "a.json"),
            str(FIXTURES / "b.json"),
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert '"merged": true' in text
    assert "merged_from" in text
