from pathlib import Path

import pytest

from grapheinstein.utils import (
    DEFAULT_CACHE_DIR,
    DEFAULT_IGNORED_PATTERNS,
    DEFAULT_MAX_FILE_SIZE,
    ConfigError,
    load_config,
    write_config_template,
)


def test_defaults_without_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    missing = tmp_path / "no-such-config.yaml"
    cfg = load_config(user_config_path=missing)
    assert cfg.output == "graph.json"
    assert cfg.log_level == "INFO"
    assert cfg.llm_model == "qwen3.5-2b-mlx:fp16-8gbGPU"
    assert cfg.embedding_model == "qwen3.5-2b-mlx:fp16-8gbGPU"
    assert cfg.llm_base_url == "http://localhost:11434"
    assert cfg.llm_confidence_threshold == 0.5
    assert cfg.compress is False
    assert cfg.versioned is False
    assert cfg.explain_hops == 2
    assert cfg.explain_top_n == 3
    assert cfg.explain_match_threshold == 0.55
    assert cfg.explain_node_cap == 500
    assert cfg.path_match_threshold == 0.55
    assert cfg.path_max_hops == 32
    assert cfg.path_confidence_default == 0.5
    assert cfg.path_confidence_floor == 0.35
    assert cfg.path_provenance_inferred_factor == 1.75
    assert cfg.query_k == 20
    assert cfg.query_hops == 1
    assert cfg.query_match_threshold == 0.40
    assert cfg.query_node_cap == 500
    assert cfg.max_file_size == DEFAULT_MAX_FILE_SIZE
    assert cfg.cache_dir == DEFAULT_CACHE_DIR
    assert cfg.ignored_patterns == DEFAULT_IGNORED_PATTERNS


def test_query_config_keys_and_override(tmp_path: Path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(
        "query_k: 10\n"
        "query_hops: 2\n"
        "query_match_threshold: 0.5\n"
        "query_node_cap: 100\n",
        encoding="utf-8",
    )
    cfg = load_config(config_path=cfg_file)
    assert cfg.query_k == 10
    assert cfg.query_hops == 2
    assert cfg.query_match_threshold == 0.5
    assert cfg.query_node_cap == 100
    cfg2 = load_config(
        config_path=cfg_file,
        query_k_override=7,
        query_hops_override=1,
        query_match_threshold_override=0.35,
        query_node_cap_override=50,
    )
    assert cfg2.query_k == 7
    assert cfg2.query_hops == 1
    assert cfg2.query_match_threshold == 0.35
    assert cfg2.query_node_cap == 50


def test_path_config_keys_and_override(tmp_path: Path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(
        "path_match_threshold: 0.7\n"
        "path_max_hops: 10\n"
        "path_confidence_default: 0.6\n"
        "path_confidence_floor: 0.4\n"
        "path_provenance_inferred_factor: 2.0\n",
        encoding="utf-8",
    )
    cfg = load_config(config_path=cfg_file)
    assert cfg.path_match_threshold == 0.7
    assert cfg.path_max_hops == 10
    assert cfg.path_confidence_default == 0.6
    assert cfg.path_confidence_floor == 0.4
    assert cfg.path_provenance_inferred_factor == 2.0
    cfg2 = load_config(
        config_path=cfg_file,
        path_match_threshold_override=0.65,
        path_max_hops_override=5,
    )
    assert cfg2.path_match_threshold == 0.65
    assert cfg2.path_max_hops == 5


def test_path_match_threshold_inherits_explain_when_unset(tmp_path: Path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text("explain_match_threshold: 0.8\n", encoding="utf-8")
    cfg = load_config(config_path=cfg_file)
    assert cfg.explain_match_threshold == 0.8
    assert cfg.path_match_threshold == 0.8


def test_explain_config_keys_and_override(tmp_path: Path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(
        "explain_hops: 1\n"
        "explain_top_n: 5\n"
        "explain_match_threshold: 0.7\n"
        "explain_node_cap: 100\n",
        encoding="utf-8",
    )
    cfg = load_config(config_path=cfg_file)
    assert cfg.explain_hops == 1
    assert cfg.explain_top_n == 5
    assert cfg.explain_match_threshold == 0.7
    assert cfg.explain_node_cap == 100
    cfg2 = load_config(
        config_path=cfg_file,
        explain_hops_override=2,
        explain_top_n_override=4,
        explain_match_threshold_override=0.6,
        explain_node_cap_override=50,
    )
    assert cfg2.explain_hops == 2
    assert cfg2.explain_top_n == 4
    assert cfg2.explain_match_threshold == 0.6
    assert cfg2.explain_node_cap == 50


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


def test_new_config_keys_and_embedding_fallback(tmp_path: Path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(
        "llm_model: only-llm\n"
        "ignored_patterns:\n"
        "  - \"build/\"\n"
        "max_file_size: 2048\n"
        f"cache_dir: \"{tmp_path / 'mycache'}\"\n",
        encoding="utf-8",
    )
    cfg = load_config(config_path=cfg_file)
    assert cfg.llm_model == "only-llm"
    assert cfg.embedding_model == "only-llm"
    assert cfg.ignored_patterns == ("build/",)
    assert cfg.max_file_size == 2048
    assert cfg.cache_dir == (tmp_path / "mycache").expanduser().resolve()

    cfg2 = load_config(
        config_path=cfg_file,
        embedding_model_override="embed-cli",
        max_file_size_override=4096,
    )
    assert cfg2.embedding_model == "embed-cli"
    assert cfg2.max_file_size == 4096


def test_invalid_max_file_size_raises(tmp_path: Path):
    cfg_file = tmp_path / "bad.yaml"
    cfg_file.write_text("max_file_size: 0\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="max_file_size"):
        load_config(config_path=cfg_file)


def test_empty_embedding_model_raises(tmp_path: Path):
    cfg_file = tmp_path / "bad.yaml"
    cfg_file.write_text('embedding_model: ""\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="embedding_model"):
        load_config(config_path=cfg_file)


def test_write_config_template_creates_and_refuses(tmp_path: Path):
    dest = tmp_path / "nested" / "config.yaml"
    written = write_config_template(dest)
    assert written.exists()
    assert "ignored_patterns" in written.read_text(encoding="utf-8")
    with pytest.raises(ConfigError, match="already exists"):
        write_config_template(dest, force=False)
    write_config_template(dest, force=True)
