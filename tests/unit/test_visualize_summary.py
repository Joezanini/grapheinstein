from pathlib import Path

from grapheinstein.core.graph import stats_from_artifact
from grapheinstein.core.visualize import artifact_to_dot


SAMPLE = {
    "schema_version": "3.0.0",
    "directed": True,
    "multigraph": False,
    "graph": {"project_root": "/tmp/p", "generated_at": "2026-07-16T00:00:00Z"},
    "nodes": [
        {"id": ".", "type": "dir", "metadata": {}},
        {"id": "a.py", "type": "file", "metadata": {}},
        {"id": "b.py", "type": "file", "metadata": {}},
        {
            "id": "a.py::function::foo::1",
            "type": "function",
            "metadata": {
                "name": "foo",
                "language": "python",
                "file": "a.py",
                "start_line": 1,
            },
        },
    ],
    "links": [
        {"source": ".", "target": "a.py", "type": "contains", "provenance": "extracted"},
        {"source": ".", "target": "b.py", "type": "contains", "provenance": "extracted"},
        {"source": "a.py", "target": "b.py", "type": "references", "provenance": "extracted"},
        {
            "source": "a.py",
            "target": "a.py::function::foo::1",
            "type": "defines",
            "provenance": "extracted",
        },
    ],
}


def test_stats_from_artifact_counts():
    stats = stats_from_artifact(SAMPLE, Path("/tmp/graph.json"))
    assert stats.file_count == 2
    assert stats.directory_count == 1
    assert stats.function_count == 1
    assert stats.total_nodes == 4
    assert stats.contains_count == 2
    assert stats.references_count == 1
    assert stats.defines_count == 1


def test_artifact_to_dot_includes_nodes_and_edges():
    dot = artifact_to_dot(SAMPLE)
    assert "digraph G" in dot
    assert '"a.py"' in dot
    assert '"b.py"' in dot
    assert "contains" in dot
    assert "references" in dot
    assert "defines" in dot
    assert "a.py::function::foo::1" in dot
