from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()


def test_init_help_lists_options():
    result = runner.invoke(cli, ["init", "--help"])
    assert result.exit_code == 0
    assert "--output" in result.output
    assert "--force" in result.output


def test_root_help_lists_init():
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.output
