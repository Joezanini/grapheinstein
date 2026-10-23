"""Dart signatures, including named and optional parameters."""

from pathlib import Path

from grapheinstein.core.parsers.extract import extract_file

SOURCE = """
class Box<T> extends Base {
  Box(this.value) {}
  void named({required String title, int? count}) {}
  Future<String> fetch(String id, [int? page]) async {
    return id;
  }
}
String top(String name) {
  return name;
}
"""


def _entities(tmp_path: Path):
    path = tmp_path / "sample.dart"
    path.write_text(SOURCE, encoding="utf-8")
    result = extract_file(path, "dart", file_id="sample.dart")
    assert not result.skipped
    return {(entity.kind, entity.name): entity for entity in result.entities}


def test_dart_named_and_optional_parameters(tmp_path: Path):
    entities = _entities(tmp_path)
    named = entities[("method", "named")]
    by_name = {param["name"]: param for param in named.parameters or []}
    assert by_name["title"]["kind"] == "named"
    assert by_name["title"]["required"] is True
    assert by_name["title"]["type"] == "String"
    assert by_name["count"]["kind"] == "named"
    assert by_name["count"]["required"] is False
    assert by_name["count"]["type"] == "int?"
    assert named.return_type == "void"

    fetch = entities[("method", "fetch")]
    fetch_params = {param["name"]: param for param in fetch.parameters or []}
    assert fetch_params["id"]["kind"] == "positional"
    assert fetch_params["id"]["required"] is True
    assert fetch_params["id"]["type"] == "String"
    assert fetch_params["page"]["kind"] == "positional"
    assert fetch_params["page"]["required"] is False
    assert fetch_params["page"]["type"] == "int?"
    assert fetch.return_type == "Future<String>"
    assert fetch.signature is not None
    assert fetch.signature.endswith("async")
    assert fetch.snippet is not None
    assert "return id;" in fetch.snippet

    top = entities[("function", "top")]
    assert top.return_type == "String"
    assert top.parameters == [
        {"name": "name", "type": "String", "kind": "positional", "required": True}
    ]


def test_dart_constructor_and_class_declaration(tmp_path: Path):
    entities = _entities(tmp_path)
    ctor = entities[("method", "Box")]
    assert ctor.parameters == [
        {"name": "value", "kind": "positional", "required": True}
    ]
    assert ctor.return_type is None
    assert ctor.signature is not None
    assert "Box(this.value)" in ctor.signature
    box = entities[("class", "Box")]
    assert box.parameters is None
    assert box.signature is not None
    assert "Box<T>" in box.signature
    assert "extends Base" in box.signature
