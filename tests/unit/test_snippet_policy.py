"""Snippet caps, the disable switch, secret paths, and schema compatibility."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from grapheinstein.cli import cli
from grapheinstein.core.graph import (
    SCHEMA_VERSION,
    add_code_entity,
    add_node,
    load_artifact,
    new_inventory_graph,
    save_graph,
)
from grapheinstein.core.index import index_project
from grapheinstein.core.parsers.extract import extract_file
from grapheinstein.core.parsers.signatures import SnippetSettings, is_secret_basename
from grapheinstein.utils import ConfigError, load_config

RUNNER = CliRunner()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_line_and_byte_caps(tmp_path: Path):
    body = "\n".join(f"    value_{i} = {i}" for i in range(60))
    path = tmp_path / "big.py"
    _write(path, f"def big():\n{body}\n")
    result = extract_file(path, "python", file_id="big.py")
    entity = next(item for item in result.entities if item.name == "big")
    assert entity.snippet is not None
    assert len(entity.snippet.splitlines()) <= 40
    assert len(entity.snippet.encode("utf-8")) <= 2048
    assert entity.snippet_truncated is True
    assert entity.signature is not None

    wide = tmp_path / "wide.py"
    _write(wide, "def wide():\n    return '" + ("a" * 3000) + "'\n")
    wide_entity = next(
        item
        for item in extract_file(wide, "python", file_id="wide.py").entities
        if item.name == "wide"
    )
    assert wide_entity.snippet is not None
    assert len(wide_entity.snippet.encode("utf-8")) <= 2048
    assert wide_entity.snippet_truncated is True

    tight = extract_file(
        path,
        "python",
        file_id="big.py",
        snippet_settings=SnippetSettings(max_lines=2, max_bytes=2048),
    )
    tight_entity = next(item for item in tight.entities if item.name == "big")
    assert tight_entity.snippet is not None
    assert len(tight_entity.snippet.splitlines()) <= 2
    assert tight_entity.snippet_truncated is True


def test_disabled_snippets_keep_signatures(tmp_path: Path):
    path = tmp_path / "sample.py"
    _write(path, "def add(x: int) -> int:\n    return x\n")
    result = extract_file(
        path,
        "python",
        file_id="sample.py",
        snippet_settings=SnippetSettings(enabled=False),
    )
    entity = next(item for item in result.entities if item.name == "add")
    assert entity.snippet is None
    assert entity.signature is not None
    assert entity.parameters
    assert entity.parameters[0]["name"] == "x"
    assert entity.return_type == "int"


@pytest.mark.parametrize(
    "file_id",
    [
        ".env",
        ".env.local",
        "secrets.py",
        "api_secret.ts",
        "credentials.py",
        "db_password.py",
        "token.pem",
        "private.key",
        "id_rsa",
    ],
)
def test_secret_basename_omits_snippet(tmp_path: Path, file_id: str):
    assert is_secret_basename(file_id) is True
    path = tmp_path / Path(file_id).name
    _write(path, "def hidden(token: str) -> str:\n    return token\n")
    result = extract_file(path, "python", file_id=file_id)
    entity = next(item for item in result.entities if item.name == "hidden")
    assert entity.snippet is None
    assert entity.signature is not None
    assert entity.parameters
    assert entity.parameters[0]["type"] == "str"


def test_directory_named_secret_does_not_suppress_snippets(tmp_path: Path):
    assert is_secret_basename("src/secrets/client.ts") is False
    path = tmp_path / "client.py"
    _write(path, "def visible():\n    return 1\n")
    result = extract_file(path, "python", file_id="src/secrets/client.py")
    entity = next(item for item in result.entities if item.name == "visible")
    assert entity.snippet is not None
    assert "return 1" in entity.snippet


def test_other_languages_do_not_gain_signatures(tmp_path: Path):
    path = tmp_path / "A.java"
    _write(path, "class A { void run(String name) { return; } }\n")
    result = extract_file(path, "java", file_id="A.java")
    methods = [item for item in result.entities if item.kind == "method"]
    assert methods
    assert all(item.signature is None and item.snippet is None for item in methods)


def test_config_caps_and_disable(tmp_path: Path):
    cfg_path = tmp_path / "gs.yaml"
    cfg_path.write_text(
        "snippets: false\nsnippet_max_lines: 10\nsnippet_max_bytes: 512\n",
        encoding="utf-8",
    )
    cfg = load_config(config_path=cfg_path, user_config_path=tmp_path / "absent.yaml")
    assert cfg.snippets is False
    assert cfg.snippet_max_lines == 10
    assert cfg.snippet_max_bytes == 512

    bad = tmp_path / "bad.yaml"
    bad.write_text("snippet_max_lines: 41\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(config_path=bad, user_config_path=tmp_path / "absent.yaml")
    bad.write_text("snippet_max_bytes: 2049\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(config_path=bad, user_config_path=tmp_path / "absent.yaml")


def test_index_project_schema_and_no_snippets_flag(tmp_path: Path):
    root = tmp_path / "proj"
    _write(root / "src" / "app.py", "def add(x: int) -> int:\n    return x\n")
    _write(root / "secrets.py", "def hidden():\n    return 'nope'\n")
    out = tmp_path / "graph.json"
    index_project(
        root,
        out,
        languages=["python"],
        cache_dir=tmp_path / "cache",
        include_docs=False,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "6.0.0"
    functions = [node for node in data["nodes"] if node["type"] == "function"]
    by_file = {node["metadata"]["file"]: node for node in functions}
    visible = by_file["src/app.py"]["metadata"]
    assert visible["parameters"][0]["name"] == "x"
    assert visible["return_type"] == "int"
    assert "return x" in visible["snippet"]
    assert "snippet" not in by_file["secrets.py"]["metadata"]
    assert "signature" in by_file["secrets.py"]["metadata"]

    quiet = tmp_path / "quiet.json"
    index_project(
        root,
        quiet,
        languages=["python"],
        cache_dir=tmp_path / "cache2",
        snippets=False,
    )
    quiet_data = json.loads(quiet.read_text(encoding="utf-8"))
    for node in quiet_data["nodes"]:
        if node["type"] in {"function", "class", "method"}:
            assert "snippet" not in node["metadata"]
            assert "snippet_truncated" not in node["metadata"]
    add = next(
        node
        for node in quiet_data["nodes"]
        if node["type"] == "function" and node["metadata"]["name"] == "add"
    )
    assert add["metadata"]["signature"].startswith("def add")


def test_old_graph_without_new_keys_still_loads(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, "a.py", "file")
    add_code_entity(
        graph,
        file_id="a.py",
        kind="function",
        name="legacy",
        start_line=1,
        language="python",
    )
    out = tmp_path / "graph.json"
    save_graph(graph, out)
    loaded = load_artifact(out)
    assert loaded["schema_version"] == SCHEMA_VERSION == "6.0.0"
    legacy = next(node for node in loaded["nodes"] if node["type"] == "function")
    assert "signature" not in legacy["metadata"]
    assert legacy["metadata"]["name"] == "legacy"


def test_cli_help_lists_snippet_flags():
    result = RUNNER.invoke(cli, ["index", "--help"])
    assert result.exit_code == 0
    assert "--no-snippets" in result.stdout
    assert "--snippet-max-lines" in result.stdout
    assert "--snippet-max-bytes" in result.stdout
