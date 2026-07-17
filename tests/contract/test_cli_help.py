from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()


def test_help_lists_index_and_status():
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "index" in result.output
    assert "status" in result.output
    assert "merge" in result.output
    assert "explain" in result.output


def test_explain_help_lists_key_options():
    result = runner.invoke(cli, ["explain", "--help"])
    assert result.exit_code == 0
    assert "--input" in result.output
    assert "--output" in result.output
    assert "--hops" in result.output


def test_index_help_lists_enrich_llm_flags():
    result = runner.invoke(cli, ["index", "--help"])
    assert result.exit_code == 0
    assert "--enrich-llm" in result.output
    assert "--llm-model" in result.output
    assert "--llm-base-url" in result.output
    assert "--transcribe-media" in result.output
    assert "--compress" in result.output
    assert "--versioned" in result.output
