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
    assert "path" in result.output
    assert "query" in result.output
    assert "init" in result.output
    assert "serve" in result.output


def test_all_subcommand_help_non_empty():
    for name in (
        "init",
        "index",
        "status",
        "visualize",
        "merge",
        "explain",
        "path",
        "query",
        "serve",
    ):
        result = runner.invoke(cli, [name, "--help"])
        assert result.exit_code == 0, name
        assert len(result.output.strip()) > 40, name
        assert "--help" in result.output or "Usage" in result.output


def test_explain_help_lists_key_options():
    result = runner.invoke(cli, ["explain", "--help"])
    assert result.exit_code == 0
    assert "--input" in result.output
    assert "--output" in result.output
    assert "--hops" in result.output


def test_path_help_lists_key_options():
    result = runner.invoke(cli, ["path", "--help"])
    assert result.exit_code == 0
    assert "--input" in result.output
    assert "--no-llm-explain" in result.output
    assert "--max-hops" in result.output


def test_query_help_lists_key_options():
    result = runner.invoke(cli, ["query", "--help"])
    assert result.exit_code == 0
    assert "--input" in result.output
    assert "--output" in result.output
    assert "--k" in result.output
    assert "--no-answer" in result.output


def test_index_help_lists_enrich_llm_flags():
    result = runner.invoke(cli, ["index", "--help"])
    assert result.exit_code == 0
    assert "--enrich-llm" in result.output
    assert "--llm-model" in result.output
    assert "--llm-base-url" in result.output
    assert "--transcribe-media" in result.output
    assert "--compress" in result.output
    assert "--versioned" in result.output
    assert "--embedding-model" in result.output
