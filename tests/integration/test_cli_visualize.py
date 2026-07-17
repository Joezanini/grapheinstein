import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli, prepend_index_if_needed

runner = CliRunner()
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_project"
OLD = Path(__file__).resolve().parents[1] / "fixtures" / "old_schema_v1_graph.json"


def test_visualize_summary_success(tmp_path: Path):
    out = tmp_path / "graph.json"
    indexed = runner.invoke(cli, ["index", str(FIXTURE), "-o", str(out)])
    assert indexed.exit_code == 0, indexed.output

    result = runner.invoke(cli, ["visualize", "--input", str(out)])
    assert result.exit_code == 0, result.output
    assert "Files" in result.output
    assert "Contains edges" in result.output
    assert "References edges" in result.output


def test_visualize_missing_input(tmp_path: Path):
    missing = tmp_path / "nope.json"
    result = runner.invoke(cli, ["visualize", "--input", str(missing)])
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "Error" in result.output


def test_visualize_rejects_old_schema():
    result = runner.invoke(cli, ["visualize", "--input", str(OLD)])
    assert result.exit_code == 1
    assert "unsupported" in result.output.lower() or "re-index" in result.output.lower()


def test_visualize_dot_export_and_overwrite(tmp_path: Path):
    graph_path = tmp_path / "graph.json"
    dot_path = tmp_path / "g.dot"
    dot_path.write_text("stale", encoding="utf-8")

    indexed = runner.invoke(cli, ["index", str(FIXTURE), "-o", str(graph_path)])
    assert indexed.exit_code == 0, indexed.output

    result = runner.invoke(
        cli,
        ["visualize", "--input", str(graph_path), "--dot", str(dot_path)],
    )
    assert result.exit_code == 0, result.output
    assert "Files" in result.output
    assert "DOT written" in result.output
    text = dot_path.read_text(encoding="utf-8")
    assert "digraph G" in text
    assert "stale" not in text
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    for node in data["nodes"]:
        assert f'"{node["id"]}"' in text
    for link in data["links"]:
        assert f'"{link["source"]}"' in text
        assert f'"{link["target"]}"' in text


def test_visualize_not_swallowed_by_default_path_rewrite():
    assert prepend_index_if_needed(["visualize", "--input", "g.json"]) == [
        "visualize",
        "--input",
        "g.json",
    ]
