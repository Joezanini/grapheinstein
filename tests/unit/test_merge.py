import json
from pathlib import Path

from grapheinstein.core.graph import load_artifact
from grapheinstein.core.merge import MergeConflictError, merge_artifacts, merge_paths
import pytest


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "merge_graphs"


def test_merge_union_disjoint(tmp_path: Path):
    a = load_artifact(FIXTURES / "a.json")
    b = load_artifact(FIXTURES / "b.json")
    merged = merge_artifacts([a, b], source_paths=[FIXTURES / "a.json", FIXTURES / "b.json"])
    assert merged["graph"]["merged"] is True
    assert len(merged["graph"]["merged_from"]) == 2
    assert "project_roots" in merged["graph"]
    ids = {n["id"] for n in merged["nodes"]}
    assert "a.txt" in ids and "b.txt" in ids
    out = tmp_path / "m.json"
    written = merge_paths([FIXTURES / "a.json", FIXTURES / "b.json"], output_path=out)
    assert written.exists()
    assert json.loads(written.read_text(encoding="utf-8"))["graph"]["merged"] is True


def test_merge_conflict_hard_fail(tmp_path: Path):
    out = tmp_path / "should_not_exist.json"
    with pytest.raises(MergeConflictError):
        merge_paths(
            [FIXTURES / "conflict_a.json", FIXTURES / "conflict_b.json"],
            output_path=out,
        )
    assert not out.exists()


def test_merge_requires_two_inputs():
    with pytest.raises(Exception):
        merge_artifacts([load_artifact(FIXTURES / "a.json")], source_paths=[FIXTURES / "a.json"])
