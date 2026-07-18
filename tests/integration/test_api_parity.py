import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.api import query
from grapheinstein.cli import cli

runner = CliRunner()
AUTH = Path(__file__).resolve().parents[1] / "fixtures" / "query_graphs" / "auth_chunks.json"


def test_cli_and_api_query_hit_ids_match(tmp_path: Path):
    cli_sub = tmp_path / "cli-sub.json"
    api_sub = tmp_path / "api-sub.json"
    question = "How does authentication work?"
    result = runner.invoke(
        cli,
        [
            "query",
            question,
            "--input",
            str(AUTH),
            "--output",
            str(cli_sub),
            "--no-answer",
            "--match-threshold",
            "0.3",
        ],
    )
    assert result.exit_code == 0, result.output
    cli_env = json.loads(result.stdout)
    api_env = query(
        question,
        input=AUTH,
        output=api_sub,
        no_answer=True,
        match_threshold=0.3,
    )
    assert set(cli_env["hit_ids"]) == set(api_env["hit_ids"])
    assert cli_env["schema_version"] == api_env["schema_version"] == "1.0.0"
