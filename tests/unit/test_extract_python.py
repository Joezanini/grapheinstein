from pathlib import Path

from grapheinstein.core.parsers.extract import extract_file

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "code_project"


def test_extract_python_app():
    path = FIXTURE / "src" / "app.py"
    result = extract_file(path, "python", file_id="src/app.py")
    assert not result.skipped
    kinds = {(e.kind, e.name, e.start_line) for e in result.entities}
    assert ("function", "greet", 1) in kinds
    assert ("class", "Greeter", 5) in kinds
    assert ("method", "hello", 6) in kinds
    assert any(c.name == "greet" for c in result.calls)


def test_extract_python_main_imports():
    path = FIXTURE / "src" / "main.py"
    result = extract_file(path, "python", file_id="src/main.py")
    assert result.imports
    assert any(i.module == "app" or "greet" in i.names for i in result.imports)
    assert any(e.name == "run" and e.kind == "function" for e in result.entities)
