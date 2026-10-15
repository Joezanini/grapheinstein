from pathlib import Path

from grapheinstein.core.parsers.extract import extract_file

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dart_project"


def test_extract_dart_simple():
    path = FIXTURE / "simple.dart"
    result = extract_file(path, "dart", file_id="simple.dart")
    assert not result.skipped
    kinds = {(e.kind, e.name, e.start_line) for e in result.entities}
    assert ("function", "topLevelFunction", 1) in kinds
    assert ("class", "SimpleClass", 5) in kinds
    assert ("method", "instanceMethod", 6) in kinds
    assert ("method", "staticMethod", 7) in kinds
    assert ("method", "SimpleClass", 9) in kinds  # Default constructor
    assert ("method", "named", 10) in kinds  # Named constructor


def test_extract_dart_advanced():
    path = FIXTURE / "advanced.dart"
    result = extract_file(path, "dart", file_id="advanced.dart")
    assert not result.skipped

    kinds = {(e.kind, e.name) for e in result.entities}
    assert ("class", "MyMixin") in kinds
    assert ("method", "mixinMethod") in kinds
    assert ("method", "anotherMixinMethod") in kinds
    assert ("class", "MyExtension") in kinds
    assert ("method", "extensionMethod") in kinds
    assert ("class", "Status") in kinds
    assert ("class", "GenericClass") in kinds
    assert ("method", "setValue") in kinds
    assert ("method", "getValue") in kinds
    assert ("function", "callSomeFunction") in kinds

    assert result.imports
    assert any("flutter/material.dart" in i.raw for i in result.imports)
    assert any("dart:async" in i.raw for i in result.imports)
    assert any("simple.dart" in i.raw for i in result.imports)
    assert any("part_file.dart" in i.raw for i in result.imports)


def test_extract_dart_part_file():
    path = FIXTURE / "part_file.dart"
    result = extract_file(path, "dart", file_id="part_file.dart")
    assert not result.skipped

    kinds = {(e.kind, e.name) for e in result.entities}
    assert ("function", "partFunction") in kinds

    assert result.imports
    assert any("part of" in i.raw for i in result.imports)
