from pathlib import Path

import pytest

from grapheinstein.utils import ConfigError, load_config


def test_defaults_without_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    missing = tmp_path / "no-such-config.yaml"
    cfg = load_config(user_config_path=missing)
    assert cfg.output == "graph.json"
    assert cfg.log_level == "INFO"
    assert cfg.llm_model == "qwen3.5-2b-mlx:fp16-8gbGPU"
    assert cfg.llm_base_url == "http://localhost:11434"
    assert cfg.llm_confidence_threshold == 0.5
    assert cfg.compress is False
    assert cfg.versioned is False


def test_compress_versioned_config_and_override(tmp_path: Path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text("compress: true\nversioned: true\n", encoding="utf-8")
    cfg = load_config(config_path=cfg_file)
    assert cfg.compress is True
    assert cfg.versioned is True
    cfg2 = load_config(config_path=cfg_file, compress_override=True, versioned_override=True)
    assert cfg2.compress is True
    assert cfg2.versioned is True


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


def test_llm_config_keys_and_cli_override(tmp_path: Path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(
        "llm_model: from-file\n"
        "llm_base_url: http://127.0.0.1:11434\n"
        "llm_confidence_threshold: 0.7\n",
        encoding="utf-8",
    )
    cfg = load_config(
        config_path=cfg_file,
        llm_model_override="from-cli",
        llm_base_url_override="http://localhost:9999/",
    )
    assert cfg.llm_model == "from-cli"
    assert cfg.llm_base_url == "http://localhost:9999"
    assert cfg.llm_confidence_threshold == 0.7
