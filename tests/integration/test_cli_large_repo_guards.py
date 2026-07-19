"""Integration tests for large-repo guards CLI."""

import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "large_repo_guards"
runner = CliRunner()


def test_code_only_excludes_dumps_and_keeps_reference(tmp_path: Path):
    out = tmp_path / "g.json"
    result = runner.invoke(
        cli,
        ["index", str(FIX), "--code-only", "-o", str(out)],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    ids = {n["id"] for n in data["nodes"]}
    assert "pkg/a.py" in ids
    assert "pkg/b.py" in ids
    assert not any(i.startswith("docs/") for i in ids)
    assert not any(i.startswith("discovery_cache") for i in ids)
    refs = [
        (e["source"], e["target"])
        for e in data["links"]
        if e.get("type") == "references"
    ]
    assert ("pkg/a.py", "pkg/b.py") in refs
    assert data["schema_version"] == "6.0.0"


def test_include_generated_docs_with_allow(tmp_path: Path):
    out = tmp_path / "g.json"
    result = runner.invoke(
        cli,
        [
            "index",
            str(FIX),
            "--code-only",
            "--include-generated-docs",
            "--allow-large-repo",
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    ids = {n["id"] for n in data["nodes"]}
    assert any(i.startswith("docs/") for i in ids)
    assert any(i.startswith("discovery_cache") for i in ids)


def test_preflight_reject_fast(tmp_path: Path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("max_reference_scan_ops: 5\n", encoding="utf-8")
    out = tmp_path / "nope.json"
    result = runner.invoke(
        cli,
        ["index", str(FIX), "--config", str(cfg), "-o", str(out)],
    )
    assert result.exit_code == 2
    assert "preflight" in (result.stdout + result.stderr).lower() or "scan" in (
        result.stdout + result.stderr
    ).lower()
    assert not out.exists()
