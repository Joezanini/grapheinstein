from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()


def test_help_lists_index_and_status():
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "index" in result.output
    assert "status" in result.output


def test_index_help_lists_enrich_llm_flags():
    result = runner.invoke(cli, ["index", "--help"])
    assert result.exit_code == 0
    assert "--enrich-llm" in result.output
    assert "--llm-model" in result.output
    assert "--llm-base-url" in result.output
    assert "--transcribe-media" in result.output
