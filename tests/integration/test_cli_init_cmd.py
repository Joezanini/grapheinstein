from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()


def test_init_create_refuse_and_force(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    first = runner.invoke(cli, ["init", "--output", str(cfg)])
    assert first.exit_code == 0, first.output
    assert cfg.exists()
    text = cfg.read_text(encoding="utf-8")
    for key in (
        "ignored_patterns",
        "embedding_model",
        "llm_model",
        "max_file_size",
        "cache_dir",
    ):
        assert key in text

    second = runner.invoke(cli, ["init", "--output", str(cfg)])
    assert second.exit_code != 0
    assert "already exists" in (second.output + (second.stderr or "")).lower() or "force" in (
        second.output + (second.stderr or "")
    ).lower()

    third = runner.invoke(cli, ["init", "--output", str(cfg), "--force"])
    assert third.exit_code == 0, third.output
    assert cfg.exists()
