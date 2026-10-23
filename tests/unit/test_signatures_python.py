"""Python callable signatures and snippets."""

from pathlib import Path

from grapheinstein.core.parsers.extract import extract_file

SOURCE = '''
@decorator
async def greet(name: str, *args: int, flag: bool = False, **kwargs: str) -> int:
    return 1

class Child(Base):
    def method(self, x: int) -> str:
        return "a"

def plain(a, b=1):
    return b
'''


def _entities(tmp_path: Path):
    path = tmp_path / "sample.py"
    path.write_text(SOURCE, encoding="utf-8")
    result = extract_file(path, "python", file_id="sample.py")
    assert not result.skipped
    return {(entity.kind, entity.name): entity for entity in result.entities}


def test_python_annotated_signature(tmp_path: Path):
    entities = _entities(tmp_path)
    greet = entities[("function", "greet")]
    by_name = {param["name"]: param for param in greet.parameters or []}
    assert by_name["name"] == {
        "name": "name",
        "type": "str",
        "kind": "positional",
        "required": True,
    }
    assert by_name["args"]["kind"] == "rest"
    assert by_name["args"]["required"] is False
    assert by_name["args"]["type"] == "int"
    assert by_name["flag"]["kind"] == "named"
    assert by_name["flag"]["required"] is False
    assert by_name["flag"]["type"] == "bool"
    assert by_name["kwargs"]["kind"] == "keywords"
    assert by_name["kwargs"]["type"] == "str"
    assert greet.return_type == "int"
    assert greet.signature is not None
    assert greet.signature.startswith("async def greet")
    assert "@decorator" not in greet.signature
    assert "flag: bool = False" in greet.signature


def test_python_untyped_parameters_are_not_invented(tmp_path: Path):
    plain = _entities(tmp_path)[("function", "plain")]
    by_name = {param["name"]: param for param in plain.parameters or []}
    assert "type" not in by_name["a"]
    assert by_name["a"]["required"] is True
    assert by_name["b"]["required"] is False
    assert "type" not in by_name["b"]
    assert plain.return_type is None


def test_python_snippet_includes_decorator_and_class_has_no_parameters(tmp_path: Path):
    entities = _entities(tmp_path)
    greet = entities[("function", "greet")]
    assert greet.snippet is not None
    assert greet.snippet.lstrip().startswith("@decorator")
    assert "return 1" in greet.snippet
    assert greet.snippet_truncated is False
    child = entities[("class", "Child")]
    assert child.parameters is None
    assert child.return_type is None
    assert child.signature == "class Child(Base)"
    assert child.snippet is not None
    assert "def method" in child.snippet
    method = entities[("method", "method")]
    assert method.parameters is not None
    assert {param["name"] for param in method.parameters} >= {"self", "x"}
    assert method.return_type == "str"
    assert method.snippet is not None
    assert "return \"a\"" in method.snippet or "return 'a'" in method.snippet
