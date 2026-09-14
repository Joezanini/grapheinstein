"""Integration tests for structured failure output."""

import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "large_repo_guards"
runner = CliRunner()


def test_large_repo_failure_writes_structured_output(tmp_path: Path):
    """Verify that large-repo preflight failures write .failure.json."""
    cfg = tmp_path / "c.yaml"
    cfg.write_text("max_reference_scan_ops: 5\n", encoding="utf-8")
    out = tmp_path / "graph.json"
    failure_file = tmp_path / "graph.json.failure.json"

    result = runner.invoke(
        cli,
        ["index", str(FIX), "--config", str(cfg), "-o", str(out)],
    )
    assert result.exit_code == 2
    assert not out.exists()
    assert failure_file.exists()

    failure_info = json.loads(failure_file.read_text(encoding="utf-8"))
    assert failure_info["success"] is False
    assert failure_info["exit_code"] == 2
    assert failure_info["error_category"] == "large_repo"
    assert "details" in failure_info
    details = failure_info["details"]
    assert "failure_codes" in details
    assert "large_repo_preflight_max_reference_scan_ops" in details["failure_codes"]
    assert "metrics" in details
    assert "estimated_scan_ops" in details["metrics"]
    assert "thresholds" in details
    assert details["thresholds"]["max_reference_scan_ops"] == 5
    assert "suggested_flags" in details


def test_config_error_writes_structured_output(tmp_path: Path):
    """Verify that config errors write .failure.json."""
    cfg = tmp_path / "bad.yaml"
    cfg.write_text("languages: [nosuchlang]\n", encoding="utf-8")
    out = tmp_path / "graph.json"
    failure_file = tmp_path / "graph.json.failure.json"

    result = runner.invoke(
        cli,
        ["index", str(FIX), "--config", str(cfg), "-o", str(out)],
    )
    assert result.exit_code == 1
    assert failure_file.exists()

    failure_info = json.loads(failure_file.read_text(encoding="utf-8"))
    assert failure_info["success"] is False
    assert failure_info["exit_code"] == 1
    assert failure_info["error_category"] == "config"
    assert "Configuration error" in failure_info["error_message"]


def test_file_not_found_writes_structured_output(tmp_path: Path):
    """Verify that file-not-found errors write .failure.json."""
    out = tmp_path / "graph.json"
    failure_file = tmp_path / "graph.json.failure.json"

    result = runner.invoke(
        cli,
        ["index", "/nonexistent/path", "-o", str(out)],
    )
    assert result.exit_code == 1
    assert failure_file.exists()

    failure_info = json.loads(failure_file.read_text(encoding="utf-8"))
    assert failure_info["success"] is False
    assert failure_info["exit_code"] == 1
    assert failure_info["error_category"] == "file_not_found"


def test_success_does_not_write_failure_file(tmp_path: Path):
    """Verify that successful indexing does not write .failure.json."""
    out = tmp_path / "graph.json"
    failure_file = tmp_path / "graph.json.failure.json"

    result = runner.invoke(
        cli,
        ["index", str(FIX), "--allow-large-repo", "-o", str(out)],
    )
    assert result.exit_code == 0
    assert out.exists()
    assert not failure_file.exists()
