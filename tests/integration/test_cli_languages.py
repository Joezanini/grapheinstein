import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "code_project"


def test_languages_python_only(tmp_path: Path):
    out = tmp_path / "graph.json"
    result = runner.invoke(
        cli,
        ["index", str(FIXTURE), "-o", str(out), "--languages", "python"],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["graph"].get("languages") == ["python"]
    code = [n for n in data["nodes"] if n["type"] in {"function", "class", "method"}]
    assert code
    assert all(n["metadata"]["language"] == "python" for n in code)
    assert any(n["id"] == "src/util.go" and n["type"] == "file" for n in data["nodes"])
    assert not any(n["id"].startswith("src/util.go::") for n in data["nodes"])


def test_invalid_language_fails_closed(tmp_path: Path):
    out = tmp_path / "should-not-exist.json"
    result = runner.invoke(
        cli,
        ["index", str(FIXTURE), "-o", str(out), "--languages", "python,brainfuck"],
    )
    assert result.exit_code == 1
    assert "brainfuck" in result.output.lower() or "Unknown" in result.output
    assert not out.exists()


def test_config_languages_and_cli_override(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("languages:\n  - go\n", encoding="utf-8")
    out_go = tmp_path / "go.json"
    result = runner.invoke(
        cli,
        ["index", str(FIXTURE), "-o", str(out_go), "--config", str(cfg)],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out_go.read_text(encoding="utf-8"))
    assert data["graph"].get("languages") == ["go"]
    assert any(n["id"].startswith("src/util.go::") for n in data["nodes"])
    assert not any(
        n["type"] == "function" and n["metadata"].get("language") == "python"
        for n in data["nodes"]
    )

    out_py = tmp_path / "py.json"
    result = runner.invoke(
        cli,
        [
            "index",
            str(FIXTURE),
            "-o",
            str(out_py),
            "--config",
            str(cfg),
            "--languages",
            "python",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out_py.read_text(encoding="utf-8"))
    assert data["graph"].get("languages") == ["python"]
