"""Unit tests for large-repo scan-cost preflight."""

from pathlib import Path

import networkx as nx
import pytest

from grapheinstein.core.graph import add_node, new_inventory_graph
from grapheinstein.core.index import build_inventory_graph
from grapheinstein.core.preflight import (
    compute_scan_cost_estimate,
    enforce_large_repo_gates,
)
from grapheinstein.utils import IndexTimeoutError, LargeRepoError


def _estimate_graph(tmp_path: Path) -> nx.DiGraph:
    root = tmp_path / "p"
    root.mkdir()
    (root / "a.py").write_text("print(1)\n", encoding="utf-8")
    (root / "note.html").write_text("<html>a.py</html>\n", encoding="utf-8")
    graph = new_inventory_graph(root)
    add_node(graph, "a.py", "file", metadata={"size_bytes": 10})
    add_node(graph, "note.html", "file", metadata={"size_bytes": 90})
    return graph


def test_compute_scan_cost_estimate(tmp_path: Path):
    graph = _estimate_graph(tmp_path)
    est = compute_scan_cost_estimate(graph, code_only=False)
    assert est.file_count == 2
    assert est.total_bytes == 100
    assert est.non_code_share == pytest.approx(0.9)
    assert est.unique_basenames == 2
    assert est.eligible_scan_files == 2
    assert est.estimated_scan_ops == 4

    est_code = compute_scan_cost_estimate(graph, code_only=True)
    assert est_code.eligible_scan_files == 1
    assert est_code.estimated_scan_ops == 2


def test_enforce_ops_reject_and_allow():
    from grapheinstein.core.preflight import ScanCostEstimate

    estimate = ScanCostEstimate(
        eligible_scan_files=100,
        unique_basenames=100,
        estimated_scan_ops=10_000,
        non_code_share=0.1,
        total_bytes=1000,
        file_count=10,
    )
    with pytest.raises(LargeRepoError) as excinfo:
        enforce_large_repo_gates(
            estimate,
            code_only=False,
            max_total_bytes=10_000_000,
            max_file_count=20_000,
            max_reference_scan_ops=100,
            max_non_code_share=0.85,
            large_repo_policy="reject",
        )
    assert "max_reference_scan_ops" in str(excinfo.value)

    ok = enforce_large_repo_gates(
        estimate,
        code_only=False,
        max_total_bytes=10_000_000,
        max_file_count=20_000,
        max_reference_scan_ops=100,
        max_non_code_share=0.85,
        large_repo_policy="allow",
    )
    assert ok.estimated_scan_ops == 10_000


def test_hard_byte_cap_wins_over_allow():
    from grapheinstein.core.preflight import ScanCostEstimate

    estimate = ScanCostEstimate(
        eligible_scan_files=1,
        unique_basenames=1,
        estimated_scan_ops=1,
        non_code_share=0.0,
        total_bytes=9999,
        file_count=1,
    )
    with pytest.raises(LargeRepoError) as excinfo:
        enforce_large_repo_gates(
            estimate,
            code_only=False,
            max_total_bytes=100,
            max_file_count=20_000,
            max_reference_scan_ops=5_000_000,
            max_non_code_share=0.85,
            large_repo_policy="allow",
        )
    assert "max_total_bytes" in str(excinfo.value)


def test_non_code_share_gate_under_code_only():
    from grapheinstein.core.preflight import ScanCostEstimate

    estimate = ScanCostEstimate(
        eligible_scan_files=1,
        unique_basenames=1,
        estimated_scan_ops=1,
        non_code_share=0.95,
        total_bytes=1000,
        file_count=10,
    )
    with pytest.raises(LargeRepoError):
        enforce_large_repo_gates(
            estimate,
            code_only=True,
            max_total_bytes=10_000_000,
            max_file_count=20_000,
            max_reference_scan_ops=5_000_000,
            max_non_code_share=0.85,
            large_repo_policy="reject",
        )


def test_timeout_raises_index_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    # Make deadline already expired
    monkeypatch.setattr(
        "grapheinstein.core.index.time.monotonic",
        lambda: 1000.0,
    )
    # start deadline = monotonic() + timeout → if we patch after start it's hard.
    # Instead set timeout_seconds=1 and patch monotonic to jump forward mid-run.
    calls = {"n": 0}
    real_mono = 0.0

    def fake_mono():
        calls["n"] += 1
        # First few calls for deadline setup + discovery, then jump past deadline
        if calls["n"] < 3:
            return 0.0
        return 10.0

    monkeypatch.setattr("grapheinstein.core.index.time.monotonic", fake_mono)
    monkeypatch.setattr("grapheinstein.core.references.time.monotonic", fake_mono)

    with pytest.raises(IndexTimeoutError) as excinfo:
        build_inventory_graph(
            root,
            timeout_seconds=1,
            show_progress=False,
            cache_dir=None,
            max_reference_scan_ops=5_000_000,
        )
    assert excinfo.value.phase
