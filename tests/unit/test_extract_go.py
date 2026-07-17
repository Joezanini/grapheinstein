from pathlib import Path

from grapheinstein.core.parsers.extract import extract_file

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "code_project"


def test_extract_go_add():
    path = FIXTURE / "src" / "util.go"
    result = extract_file(path, "go", file_id="src/util.go")
    assert not result.skipped
    assert any(e.kind == "function" and e.name == "Add" and e.start_line == 3 for e in result.entities)
