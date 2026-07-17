from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import app, cli, prepend_index_if_needed

runner = CliRunner()
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_project"


def test_prepend_index_for_bare_path():
    assert prepend_index_if_needed(["/tmp/proj", "-o", "g.json"]) == [
        "index",
        "/tmp/proj",
        "-o",
        "g.json",
    ]
    assert prepend_index_if_needed(["index", "/tmp/proj"]) == ["index", "/tmp/proj"]
    assert prepend_index_if_needed(["status", "-o", "g.json"]) == ["status", "-o", "g.json"]
    assert prepend_index_if_needed(["visualize", "-i", "g.json"]) == [
        "visualize",
        "-i",
        "g.json",
    ]


def test_default_invocation_writes_graph(tmp_path: Path):
    out = tmp_path / "nested" / "graph.json"
    result = runner.invoke(cli, prepend_index_if_needed([str(FIXTURE), "--output", str(out)]))
    assert result.exit_code == 0, result.output
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "schema_version" in text
    assert "README.md" in text
    assert "secret.txt" not in text


def test_index_subcommand_equivalent(tmp_path: Path):
    out = tmp_path / "g.json"
    result = runner.invoke(cli, ["index", str(FIXTURE), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_bad_project_path_fails():
    result = runner.invoke(cli, ["index", "/nonexistent/path/for/grapheinstein"])
    assert result.exit_code == 1
    assert "does not exist" in result.output.lower() or "Error" in result.output


def test_entry_app_callable():
    # Ensure console script target remains callable
    assert callable(app)
