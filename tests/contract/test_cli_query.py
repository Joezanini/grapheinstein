import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()
FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "query_graphs" / "auth_chunks.json"
)
NOISE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "query_graphs" / "noise_sparse.json"
)


def test_query_help_lists_key_options():
    result = runner.invoke(cli, ["query", "--help"])
    assert result.exit_code == 0
    assert "--input" in result.output
    assert "--output" in result.output
    assert "--k" in result.output
    assert "--no-answer" in result.output
    assert "--hops" in result.output
    assert "--match-threshold" in result.output


def test_query_requires_input_output():
    result = runner.invoke(cli, ["query", "authentication"])
    assert result.exit_code != 0


def test_query_rejects_invalid_k(tmp_path: Path):
    out = tmp_path / "out.json"
    result = runner.invoke(
        cli,
        [
            "query",
            "authentication",
            "--input",
            str(FIXTURE),
            "--output",
            str(out),
            "--k",
            "0",
            "--no-answer",
        ],
    )
    assert result.exit_code != 0
    assert not out.exists()


def test_query_empty_question(tmp_path: Path):
    out = tmp_path / "out.json"
    result = runner.invoke(
        cli,
        [
            "query",
            "   ",
            "--input",
            str(FIXTURE),
            "--output",
            str(out),
            "--no-answer",
        ],
    )
    assert result.exit_code != 0
    assert not out.exists()


def test_query_no_evidence_leaves_no_file(tmp_path: Path):
    out = tmp_path / "nomatch.json"
    result = runner.invoke(
        cli,
        [
            "query",
            "zzzx_not_a_real_topic_qqq_999",
            "--input",
            str(NOISE),
            "--output",
            str(out),
            "--no-answer",
            "--match-threshold",
            "0.95",
        ],
    )
    assert result.exit_code != 0
    assert not out.exists()
    # No success JSON on stdout
    stdout = (result.stdout or "").strip()
    if stdout:
        assert "schema_version" not in stdout or result.exit_code != 0
