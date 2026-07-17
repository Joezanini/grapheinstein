from pathlib import Path

import pytest

from grapheinstein.utils import ConfigError, load_config


def test_defaults_without_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    missing = tmp_path / "no-such-config.yaml"
    cfg = load_config(user_config_path=missing)
    assert cfg.output == "graph.json"
    assert cfg.log_level == "INFO"


def test_cli_override_wins(tmp_path: Path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text("output: from-file.json\nlog_level: DEBUG\n", encoding="utf-8")
    cfg = load_config(config_path=cfg_file, output_override="from-cli.json")
    assert cfg.output == "from-cli.json"
    assert cfg.log_level == "DEBUG"


def test_explicit_config_used(tmp_path: Path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text("output: /tmp/from-config.json\n", encoding="utf-8")
    cfg = load_config(config_path=cfg_file, user_config_path=tmp_path / "unused.yaml")
    assert cfg.output == "/tmp/from-config.json"


def test_invalid_yaml_raises(tmp_path: Path):
    cfg_file = tmp_path / "bad.yaml"
    cfg_file.write_text("output: [unterminated\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(config_path=cfg_file)


def test_unknown_keys_ignored(tmp_path: Path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text("output: x.json\nfuture_key: 1\n", encoding="utf-8")
    cfg = load_config(config_path=cfg_file)
    assert cfg.output == "x.json"
