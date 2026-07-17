from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_project"


def test_config_output_path_honored(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    out = tmp_path / "from-config.json"
    cfg.write_text(f"output: {out.as_posix()}\nlog_level: INFO\n", encoding="utf-8")

    result = runner.invoke(cli, ["index", str(FIXTURE), "--config", str(cfg)])
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_invalid_config_exits_1(tmp_path: Path):
    cfg = tmp_path / "bad.yaml"
    cfg.write_text("output: [\n", encoding="utf-8")
    result = runner.invoke(cli, ["index", str(FIXTURE), "--config", str(cfg)])
    assert result.exit_code == 1
    assert "Error" in result.output
