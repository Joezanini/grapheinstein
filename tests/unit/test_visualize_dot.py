from pathlib import Path

from grapheinstein.core.visualize import artifact_to_dot, write_dot

SAMPLE = {
    "schema_version": "5.0.0",
    "nodes": [
        {"id": ".", "type": "dir", "metadata": {}},
        {"id": "x.py", "type": "file", "metadata": {}},
        {
            "id": "x.py::function::f::1",
            "type": "function",
            "metadata": {
                "name": "f",
                "language": "python",
                "file": "x.py",
                "start_line": 1,
            },
        },
    ],
    "links": [
        {"source": ".", "target": "x.py", "type": "contains", "provenance": "extracted"},
        {
            "source": "x.py",
            "target": "x.py::function::f::1",
            "type": "defines",
            "provenance": "extracted",
        },
    ],
}


def test_dot_escape_quotes():
    data = {
        "nodes": [{"id": 'weird"name', "type": "file", "metadata": {}}],
        "links": [],
    }
    dot = artifact_to_dot(data)
    assert '\\"' in dot


def test_write_dot_overwrites(tmp_path: Path):
    path = tmp_path / "out.dot"
    path.write_text("old", encoding="utf-8")
    written = write_dot(SAMPLE, path)
    text = written.read_text(encoding="utf-8")
    assert "digraph G" in text
    assert '"x.py"' in text
    assert "defines" in text
    assert "old" not in text
