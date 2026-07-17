"""Per-file Tree-sitter extraction of code entities and import/call facts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger
from tree_sitter import Node, Query, QueryCursor

from grapheinstein.core.parsers.queries import get_query
from grapheinstein.core.parsers.registry import get_parser_for_file


@dataclass
class CodeEntity:
    kind: str  # function | class | method
    name: str
    start_line: int
    end_line: int | None = None
    parent_class: str | None = None


@dataclass
class ImportFact:
    module: str | None = None
    names: list[str] = field(default_factory=list)
    is_relative: bool = False
    raw: str = ""


@dataclass
class CallFact:
    name: str
    start_line: int
    enclosing: str | None = None  # entity id hint: kind:name:line of enclosing fn/method


@dataclass
class ExtractResult:
    entities: list[CodeEntity] = field(default_factory=list)
    imports: list[ImportFact] = field(default_factory=list)
    calls: list[CallFact] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _line(node: Node) -> int:
    return node.start_point[0] + 1


def _find_enclosing_callable(node: Node, source: bytes) -> str | None:
    current = node.parent
    while current is not None:
        if current.type in {
            "function_definition",
            "function_declaration",
            "function_item",
            "method_definition",
            "method_declaration",
        }:
            name_node = current.child_by_field_name("name")
            if name_node is None:
                for child in current.children:
                    if child.type in {"identifier", "property_identifier", "field_identifier"}:
                        name_node = child
                        break
            if name_node is not None:
                kind = "method" if "method" in current.type else "function"
                return f"{kind}:{_node_text(name_node, source)}:{_line(current)}"
        current = current.parent
    return None


def _parse_python_import(node: Node, source: bytes) -> ImportFact:
    text = _node_text(node, source)
    fact = ImportFact(raw=text)
    if node.type == "import_from_statement":
        module_node = node.child_by_field_name("module_name")
        if module_node is not None:
            fact.module = _node_text(module_node, source)
            fact.is_relative = fact.module.startswith(".")
        names: list[str] = []
        for child in node.children:
            if child.type == "dotted_name" and module_node is not None and child.id == module_node.id:
                continue
            if child.type in {"dotted_name", "identifier"}:
                names.append(_node_text(child, source))
            elif child.type == "aliased_import":
                name = child.child_by_field_name("name")
                if name is not None:
                    names.append(_node_text(name, source))
        # Filter module duplicates
        if fact.module and names and names[0] == fact.module:
            names = names[1:]
        fact.names = names
    elif node.type == "import_statement":
        names = []
        for child in node.children:
            if child.type == "dotted_name":
                names.append(_node_text(child, source))
            elif child.type == "aliased_import":
                name = child.child_by_field_name("name")
                if name is not None:
                    names.append(_node_text(name, source))
        if names:
            fact.module = names[0]
            fact.names = names
    return fact


def _parse_generic_import(node: Node, source: bytes) -> ImportFact:
    text = _node_text(node, source).strip()
    fact = ImportFact(raw=text)
    # JS/TS: import x from './mod'
    if " from " in text:
        after = text.split(" from ", 1)[1].strip().rstrip(";").strip().strip("'\"")
        fact.module = after
        fact.is_relative = after.startswith(".")
    elif text.startswith("import "):
        # Go/Java style — take last path segment-ish
        rest = text[len("import ") :].strip().rstrip(";").strip().strip('"')
        fact.module = rest.strip('"').strip("'")
    elif text.startswith("#include"):
        include = text.split(None, 1)[-1].strip().strip("<>\"")
        fact.module = include
    elif text.startswith("use "):
        fact.module = text[4:].rstrip(";").strip()
    return fact


def extract_file(file_path: Path, language_id: str, *, file_id: str) -> ExtractResult:
    """Extract entities/facts from one source file. Never raises for parse issues."""
    _ = file_id  # reserved for future qualified names
    result = ExtractResult()
    try:
        raw = file_path.read_bytes()
    except OSError as exc:
        logger.warning("Skipping unreadable file {}: {}", file_id, exc)
        result.skipped = True
        result.skip_reason = str(exc)
        return result

    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError:
        logger.warning("Skipping non-UTF-8 file {} for structure extraction", file_id)
        result.skipped = True
        result.skip_reason = "utf-8 decode failed"
        return result

    source_bytes = source.encode("utf-8")
    query_src = get_query(language_id)
    if not query_src.strip():
        return result

    try:
        parser, language = get_parser_for_file(language_id, file_path)
        tree = parser.parse(source_bytes)
        query = Query(language, query_src)
        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Structure extract failed for {}: {}", file_id, exc)
        result.skipped = True
        result.skip_reason = str(exc)
        return result

    # Tree-sitter is error-tolerant; flag files with parse errors for skip accounting
    # but still keep any entities that were confidently extracted.
    if tree.root_node.has_error:
        logger.warning(
            "Parse errors in {}; extracting best-effort structure",
            file_id,
        )
        result.skip_reason = "parse errors"

    # Track class ranges for method parent association
    class_spans: list[tuple[int, int, str]] = []

    for _pattern_index, captures in matches:
        if "class.name" in captures:
            for node in captures["class.name"]:
                name = _node_text(node, source_bytes)
                start = _line(node)
                # Prefer @class.def for end if present
                end = None
                def_nodes = captures.get("class.def") or []
                for d in def_nodes:
                    if d.start_byte <= node.start_byte <= d.end_byte:
                        end = d.end_point[0] + 1
                        class_spans.append((d.start_byte, d.end_byte, name))
                        break
                result.entities.append(
                    CodeEntity(kind="class", name=name, start_line=start, end_line=end)
                )

        if "function.name" in captures:
            for node in captures["function.name"]:
                # Skip if this function is nested as method capture in same match
                if "method.name" in captures:
                    continue
                name = _node_text(node, source_bytes)
                start = _line(node)
                end = None
                for d in captures.get("function.def") or []:
                    if d.start_byte <= node.start_byte <= d.end_byte:
                        end = d.end_point[0] + 1
                        break
                # Detect method via parent class span
                parent = None
                kind = "function"
                for start_b, end_b, cname in class_spans:
                    # Will fill on second pass if needed
                    _ = (start_b, end_b, cname)
                result.entities.append(
                    CodeEntity(kind=kind, name=name, start_line=start, end_line=end, parent_class=parent)
                )

        if "method.name" in captures:
            for node in captures["method.name"]:
                name = _node_text(node, source_bytes)
                start = _line(node)
                end = None
                for d in captures.get("method.def") or []:
                    if d.start_byte <= node.start_byte <= d.end_byte:
                        end = d.end_point[0] + 1
                        break
                parent = None
                for start_b, end_b, cname in class_spans:
                    if start_b <= node.start_byte <= end_b:
                        parent = cname
                        break
                result.entities.append(
                    CodeEntity(
                        kind="method",
                        name=name,
                        start_line=start,
                        end_line=end,
                        parent_class=parent,
                    )
                )

        if "import" in captures:
            for node in captures["import"]:
                if language_id == "python":
                    result.imports.append(_parse_python_import(node, source_bytes))
                else:
                    result.imports.append(_parse_generic_import(node, source_bytes))

        call_nodes = []
        if "call.name" in captures:
            call_nodes.extend(("name", n) for n in captures["call.name"])
        if "call.attr" in captures:
            call_nodes.extend(("attr", n) for n in captures["call.attr"])
        for _kind, node in call_nodes:
            name = _node_text(node, source_bytes)
            result.calls.append(
                CallFact(
                    name=name,
                    start_line=_line(node),
                    enclosing=_find_enclosing_callable(node, source_bytes),
                )
            )

    # Second pass: mark functions that fall inside class spans as methods (Python nested query may miss)
    if class_spans:
        revised: list[CodeEntity] = []
        for ent in result.entities:
            if ent.kind == "function":
                # Find byte position approximately via line — re-check against class entities
                for other in result.entities:
                    if other.kind == "class" and other.end_line and other.start_line <= ent.start_line <= other.end_line:
                        ent = CodeEntity(
                            kind="method",
                            name=ent.name,
                            start_line=ent.start_line,
                            end_line=ent.end_line,
                            parent_class=other.name,
                        )
                        break
            revised.append(ent)
        # Dedupe method duplicates
        seen: set[tuple[str, str, int]] = set()
        deduped: list[CodeEntity] = []
        for ent in revised:
            key = (ent.kind, ent.name, ent.start_line)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(ent)
        result.entities = deduped

    return result
