"""Test that Dart-heavy repos are not rejected as non-code."""
import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dart_heavy_project"
runner = CliRunner()


def test_dart_repo_not_rejected(tmp_path: Path):
    """A Dart-heavy repo should index successfully with Dart language enabled."""
    out = tmp_path / "dart_graph.json"
    result = runner.invoke(
        cli,
        ["index", str(FIXTURE), "--languages", "dart", "-o", str(out)],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert out.exists()

    data = json.loads(out.read_text(encoding="utf-8"))
    node_ids = {n["id"] for n in data["nodes"]}

    assert any("main.dart" in nid for nid in node_ids)
    assert any("widget.dart" in nid for nid in node_ids)
    assert any("test.dart" in nid for nid in node_ids)
