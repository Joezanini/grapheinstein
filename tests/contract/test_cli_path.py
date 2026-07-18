from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()
FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "path_graphs" / "simple_chain.json"
)


def test_path_help_lists_key_options():
    result = runner.invoke(cli, ["path", "--help"])
    assert result.exit_code == 0
    assert "--input" in result.output
    assert "--output" in result.output
    assert "--no-llm-explain" in result.output
    assert "--match-threshold" in result.output
    assert "--max-hops" in result.output


def test_path_requires_input():
    result = runner.invoke(cli, ["path", "a", "b"])
    assert result.exit_code != 0


def test_path_empty_start(tmp_path: Path):
    result = runner.invoke(
        cli,
        [
            "path",
            "   ",
            "end-concept",
            "--input",
            str(FIXTURE),
            "--no-llm-explain",
        ],
    )
    assert result.exit_code != 0


def test_path_no_match(tmp_path: Path):
    result = runner.invoke(
        cli,
        [
            "path",
            "zzzz-no-such",
            "end-concept",
            "--input",
            str(FIXTURE),
            "--no-llm-explain",
        ],
    )
    assert result.exit_code != 0
    # stdout should not be a success path_answer
    assert "path_answer" not in (result.stdout or "")


def test_path_missing_input():
    result = runner.invoke(
        cli,
        [
            "path",
            "a",
            "b",
            "--input",
            "/no/such/graph.json",
            "--no-llm-explain",
        ],
    )
    assert result.exit_code != 0
