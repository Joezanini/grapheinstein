from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()


def test_help_lists_index_and_status():
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "index" in result.output
    assert "status" in result.output
