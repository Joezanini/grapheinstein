"""JavaScript callable signatures without invented types."""

from pathlib import Path

from grapheinstein.core.parsers.extract import extract_file

SOURCE = """
async function greet(name, ...rest) {
  return 1;
}
class Child extends Base {
  createTask(listId, data = {}) {
    return data;
  }
}
"""


def _entities(tmp_path: Path):
    path = tmp_path / "sample.js"
    path.write_text(SOURCE, encoding="utf-8")
    result = extract_file(path, "javascript", file_id="sample.js")
    assert not result.skipped
    return {(entity.kind, entity.name): entity for entity in result.entities}


def test_javascript_parameters_have_no_invented_types(tmp_path: Path):
    greet = _entities(tmp_path)[("function", "greet")]
    by_name = {param["name"]: param for param in greet.parameters or []}
    assert by_name["name"]["kind"] == "positional"
    assert by_name["name"]["required"] is True
    assert "type" not in by_name["name"]
    assert by_name["rest"]["kind"] == "rest"
    assert by_name["rest"]["required"] is False
    assert "type" not in by_name["rest"]
    assert greet.return_type is None
    assert greet.signature is not None
    assert greet.signature.startswith("async function greet")


def test_javascript_default_parameter_and_class_declaration(tmp_path: Path):
    entities = _entities(tmp_path)
    method = entities[("method", "createTask")]
    by_name = {param["name"]: param for param in method.parameters or []}
    assert by_name["listId"]["required"] is True
    assert by_name["data"]["required"] is False
    assert "type" not in by_name["data"]
    child = entities[("class", "Child")]
    assert child.parameters is None
    assert child.signature == "class Child extends Base"
    assert child.snippet is not None
    assert "createTask" in child.snippet
