from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()
FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "explain_graphs" / "auth_neighborhood.json"
)


def test_explain_help_lists_key_options():
    result = runner.invoke(cli, ["explain", "--help"])
    assert result.exit_code == 0
    assert "--input" in result.output
    assert "--output" in result.output
    assert "--hops" in result.output
    assert "--no-summary" in result.output
    assert "--top-n" in result.output
    assert "--match-threshold" in result.output


def test_explain_requires_input_output():
    result = runner.invoke(cli, ["explain", "auth"])
    assert result.exit_code != 0


def test_explain_rejects_invalid_hops(tmp_path: Path):
    out = tmp_path / "out.json"
    result = runner.invoke(
        cli,
        [
            "explain",
            "auth",
            "--input",
            str(FIXTURE),
            "--output",
            str(out),
            "--hops",
            "3",
            "--no-summary",
        ],
    )
    assert result.exit_code != 0
    assert not out.exists()


def test_explain_empty_concept(tmp_path: Path):
    out = tmp_path / "out.json"
    result = runner.invoke(
        cli,
        [
            "explain",
            "   ",
            "--input",
            str(FIXTURE),
            "--output",
            str(out),
            "--no-summary",
        ],
    )
    assert result.exit_code != 0
    assert not out.exists()


def test_explain_no_match_leaves_no_file(tmp_path: Path):
    out = tmp_path / "nomatch.json"
    result = runner.invoke(
        cli,
        [
            "explain",
            "zzzx_not_a_real_concept_qqq",
            "--input",
            str(FIXTURE),
            "--output",
            str(out),
            "--no-summary",
        ],
    )
    assert result.exit_code != 0
    assert not out.exists()
