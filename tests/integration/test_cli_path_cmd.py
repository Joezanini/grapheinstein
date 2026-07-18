import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "path_graphs"
CHAIN = FIXTURES / "simple_chain.json"
WEIGHTED = FIXTURES / "weighted_routes.json"
DISCONNECTED = FIXTURES / "disconnected.json"


def _stdout_json(result) -> dict:
    text = result.stdout.strip()
    # Prefer last JSON object if stderr mixed (should not be)
    start = text.find("{")
    assert start >= 0, result.output
    return json.loads(text[start:])


def test_path_happy_stdout_and_output_file(tmp_path: Path):
    out = tmp_path / "path.json"
    result = runner.invoke(
        cli,
        [
            "path",
            "start-concept",
            "end-concept",
            "--input",
            str(CHAIN),
            "--output",
            str(out),
            "--no-llm-explain",
        ],
    )
    assert result.exit_code == 0, result.output
    data = _stdout_json(result)
    assert data["kind"] == "path_answer"
    assert data["nodes"][0] == data["start"]["node_id"]
    assert data["nodes"][-1] == data["end"]["node_id"]
    assert all("provenance" in s for s in data["steps"])
    file_data = json.loads(out.read_text(encoding="utf-8"))
    assert file_data == data


def test_path_weighted_prefers_mid():
    result = runner.invoke(
        cli,
        [
            "path",
            "A",
            "B",
            "-i",
            str(WEIGHTED),
            "--no-llm-explain",
        ],
    )
    assert result.exit_code == 0, result.output
    data = _stdout_json(result)
    assert "func:preferred-mid" in data["nodes"]


def test_path_fuzzy_approximate():
    result = runner.invoke(
        cli,
        [
            "path",
            "start concept",
            "end-concept",
            "-i",
            str(CHAIN),
            "--no-llm-explain",
        ],
    )
    assert result.exit_code == 0, result.output
    data = _stdout_json(result)
    assert "start" in data["start"]["node_id"] or "start" in data["start"]["query"]


def test_path_disconnected_fails():
    result = runner.invoke(
        cli,
        [
            "path",
            "island-a",
            "island-b",
            "-i",
            str(DISCONNECTED),
            "--no-llm-explain",
        ],
    )
    assert result.exit_code != 0
    assert "path_answer" not in (result.stdout or "")


def test_path_same_node(tmp_path: Path):
    out = tmp_path / "same.json"
    result = runner.invoke(
        cli,
        [
            "path",
            "start-concept",
            "start-concept",
            "-i",
            str(CHAIN),
            "-o",
            str(out),
            "--no-llm-explain",
        ],
    )
    assert result.exit_code == 0, result.output
    data = _stdout_json(result)
    assert data["hop_count"] == 0
    assert data["steps"] == []
    assert json.loads(out.read_text(encoding="utf-8")) == data
