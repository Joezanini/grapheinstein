"""Optional function, method, and class signatures plus capped source snippets.

Captured only for Python, JavaScript, TypeScript, and Dart. Other languages
are left unchanged. New metadata is optional and schema_version stays 6.0.0.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from loguru import logger
from tree_sitter import Node

SIGNATURE_LANGUAGES = frozenset({"python", "javascript", "typescript", "dart"})
DEFAULT_SNIPPET_MAX_LINES = 40
DEFAULT_SNIPPET_MAX_BYTES = 2048
SIGNATURE_MAX_BYTES = 2048
_PARAM_KINDS = frozenset({"positional", "named", "rest", "keywords"})
_SECRET_TOKENS = ("secret", "credential", "password")
_SKIP_PARAM_TYPES = frozenset({",", "(", ")", ";", "comment"})


@dataclass(frozen=True)
class SnippetSettings:
    """Effective snippet capture limits for one index run."""

    enabled: bool = True
    max_lines: int = DEFAULT_SNIPPET_MAX_LINES
    max_bytes: int = DEFAULT_SNIPPET_MAX_BYTES


def collapse_ws(text: str) -> str:
    return " ".join(text.split())


def is_secret_basename(file_id: str) -> bool:
    """True when the file name matches the spec's secret patterns.

    Directory names are ignored. Matching is case-insensitive.
    """
    name = PurePosixPath(file_id.replace("\\", "/")).name.lower()
    if name == ".env" or name.startswith(".env."):
        return True
    if name == "id_rsa" or name.endswith(".pem") or name.endswith(".key"):
        return True
    return any(token in name for token in _SECRET_TOKENS)


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def truncate_text(text: str, max_lines: int, max_bytes: int) -> tuple[str, bool]:
    """Cut at the first of the line cap and the UTF-8 byte cap."""
    truncated = False
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True
    snippet = "\n".join(lines)
    raw = snippet.encode("utf-8")
    if len(raw) > max_bytes:
        truncated = True
        cut = raw[:max_bytes]
        while cut:
            try:
                snippet = cut.decode("utf-8")
                break
            except UnicodeDecodeError:
                cut = cut[:-1]
        else:
            snippet = ""
    return snippet, truncated


def _payload_size(
    signature: str,
    parameters: list[dict[str, Any]] | None,
    return_type: str | None,
) -> int:
    payload: dict[str, Any] = {"signature": signature}
    if parameters is not None:
        payload["parameters"] = parameters
    if return_type is not None:
        payload["return_type"] = return_type
    return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _shrink_text_to_fit(
    signature: str,
    parameters: list[dict[str, Any]] | None,
    return_type: str | None,
    *,
    which: str,
) -> str:
    """Binary-search a string field so the signature payload fits the byte budget."""
    text = signature if which == "signature" else (return_type or "")
    best = ""
    lo = 0
    hi = len(text)
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = text[:mid]
        sig = candidate if which == "signature" else signature
        ret = candidate if which == "return_type" else return_type
        if which == "return_type" and candidate == "":
            ret = None
        if _payload_size(sig, parameters, ret) <= SIGNATURE_MAX_BYTES:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def fit_signature(
    signature: str,
    parameters: list[dict[str, Any]] | None,
    return_type: str | None,
) -> tuple[str, list[dict[str, Any]] | None, str | None, bool]:
    """Keep signature text + parameters + return type within 2048 UTF-8 bytes."""
    truncated = False
    params = list(parameters) if parameters is not None else None
    ret = return_type
    while params and _payload_size(signature, params, ret) > SIGNATURE_MAX_BYTES:
        params.pop()
        truncated = True
    if _payload_size(signature, params, ret) > SIGNATURE_MAX_BYTES:
        truncated = True
        signature = _shrink_text_to_fit(signature, params, ret, which="signature")
    if _payload_size(signature, params, ret) > SIGNATURE_MAX_BYTES and ret is not None:
        truncated = True
        shrunk = _shrink_text_to_fit(signature, params, ret, which="return_type")
        ret = shrunk or None
    return signature, params, ret, truncated


def _param(name: str, kind: str, required: bool, type_text: str | None) -> dict[str, Any]:
    if kind not in _PARAM_KINDS:
        raise ValueError(f"Unknown parameter kind: {kind}")
    if type_text:
        return {"name": name, "type": type_text, "kind": kind, "required": required}
    return {"name": name, "kind": kind, "required": required}


def _header_until(node: Node, source: bytes, body_types: frozenset[str]) -> str:
    end = node.end_byte
    for child in node.children:
        if child.type in body_types:
            end = child.start_byte
            break
    text = source[node.start_byte : end].decode("utf-8", errors="replace")
    return collapse_ws(text).rstrip(":").rstrip("{").strip()


def _direct_children(node: Node, type_name: str) -> list[Node]:
    return [child for child in node.children if child.type == type_name]


def _strip_colon(text: str) -> str:
    collapsed = collapse_ws(text)
    if collapsed.startswith(":"):
        collapsed = collapsed[1:].strip()
    return collapsed


def _py_type_text(node: Node, source: bytes) -> str | None:
    for child in node.children:
        if child.type == "type":
            text = collapse_ws(_node_text(child, source))
            return text or None
    return None


def _py_name_from(node: Node, source: bytes) -> str | None:
    if node.type == "identifier":
        return _node_text(node, source)
    for child in node.children:
        if child.type == "identifier":
            return _node_text(child, source)
        found = _py_name_from(child, source)
        if found and child.type in {
            "list_splat_pattern",
            "dictionary_splat_pattern",
            "typed_parameter",
            "default_parameter",
            "typed_default_parameter",
        }:
            return found
    return None


def _python_parameters(params: Node, source: bytes) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    keyword_only = False
    for child in params.children:
        if child.type in _SKIP_PARAM_TYPES or child.type == "positional_separator":
            continue
        if child.type == "list_splat_pattern":
            name = _py_name_from(child, source)
            if name:
                result.append(_param(name, "rest", False, None))
            keyword_only = True
            continue
        if child.type == "dictionary_splat_pattern":
            name = _py_name_from(child, source)
            if name:
                result.append(_param(name, "keywords", False, None))
            continue
        if child.type == "identifier":
            kind = "named" if keyword_only else "positional"
            result.append(_param(_node_text(child, source), kind, True, None))
            continue
        if child.type in {"typed_parameter", "default_parameter", "typed_default_parameter"}:
            splat_list = [
                grand
                for grand in child.children
                if grand.type in {"list_splat_pattern", "dictionary_splat_pattern"}
            ]
            type_text = _py_type_text(child, source)
            has_default = child.type in {"default_parameter", "typed_default_parameter"} or any(
                grand.type == "=" for grand in child.children
            )
            if splat_list and splat_list[0].type == "list_splat_pattern":
                name = _py_name_from(splat_list[0], source)
                if name:
                    result.append(_param(name, "rest", False, type_text))
                keyword_only = True
                continue
            if splat_list and splat_list[0].type == "dictionary_splat_pattern":
                name = _py_name_from(splat_list[0], source)
                if name:
                    result.append(_param(name, "keywords", False, type_text))
                continue
            name = None
            for grand in child.children:
                if grand.type == "identifier":
                    name = _node_text(grand, source)
                    break
            if not name:
                continue
            kind = "named" if keyword_only else "positional"
            result.append(_param(name, kind, not has_default, type_text))
    return result


def _python_return(node: Node, source: bytes) -> str | None:
    seen_params = False
    for child in node.children:
        if child.type == "parameters":
            seen_params = True
            continue
        if seen_params and child.type == "type":
            text = collapse_ws(_node_text(child, source))
            return text or None
    return None


def _js_name(node: Node, source: bytes) -> str | None:
    if node.type in {"identifier", "property_identifier"}:
        return _node_text(node, source)
    if node.type in {"object_pattern", "array_pattern"}:
        text = collapse_ws(_node_text(node, source))
        return text or None
    if node.type in {"rest_pattern", "assignment_pattern", "required_parameter", "optional_parameter"}:
        for child in node.children:
            if child.type in {
                "identifier",
                "property_identifier",
                "rest_pattern",
                "object_pattern",
                "array_pattern",
                "assignment_pattern",
            }:
                found = _js_name(child, source)
                if found:
                    return found
    return None


def _js_type(node: Node, source: bytes) -> str | None:
    for child in node.children:
        if child.type == "type_annotation":
            text = _strip_colon(_node_text(child, source))
            return text or None
    for child in node.children:
        if child.type in {"required_parameter", "optional_parameter", "rest_pattern", "assignment_pattern"}:
            found = _js_type(child, source)
            if found:
                return found
    return None


def _is_rest(node: Node) -> bool:
    if node.type == "rest_pattern":
        return True
    return any(child.type == "rest_pattern" or _is_rest(child) for child in node.children if child.type != "type_annotation")


def _js_parameters(formal: Node, source: bytes) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for child in formal.children:
        if child.type in _SKIP_PARAM_TYPES:
            continue
        name = _js_name(child, source)
        if not name:
            continue
        type_text = _js_type(child, source)
        rest = child.type == "rest_pattern" or _is_rest(child)
        has_default = child.type == "assignment_pattern" or any(
            grand.type == "=" for grand in child.children
        )
        optional = child.type == "optional_parameter"
        if rest:
            result.append(_param(name, "rest", False, type_text))
            continue
        required = not optional and not has_default
        result.append(_param(name, "positional", required, type_text))
    return result


def _js_return(node: Node, source: bytes) -> str | None:
    for child in node.children:
        if child.type == "type_annotation":
            text = _strip_colon(_node_text(child, source))
            return text or None
    return None


def _dart_formal_name_and_type(node: Node, source: bytes) -> tuple[str | None, str | None]:
    for child in node.children:
        if child.type == "constructor_param":
            identifiers = [grand for grand in child.children if grand.type == "identifier"]
            name = _node_text(identifiers[-1], source) if identifiers else None
            return name, None
    identifiers = [child for child in node.children if child.type == "identifier"]
    if not identifiers:
        return None, None
    name_node = identifiers[-1]
    raw = _node_text(node, source)
    name = _node_text(name_node, source)
    type_text = raw[: raw.rfind(name)].strip() if name and name in raw else ""
    type_text = collapse_ws(type_text)
    return name, type_text or None


def _dart_optional_group(node: Node, source: bytes) -> list[dict[str, Any]]:
    text = _node_text(node, source).lstrip()
    kind = "named" if text.startswith("{") else "positional"
    result: list[dict[str, Any]] = []
    children = [child for child in node.children if child.type not in {"{", "}", "[", "]", ","}]
    index = 0
    pending_required = False
    while index < len(children):
        child = children[index]
        if child.type == "required":
            pending_required = True
            index += 1
            continue
        if child.type != "formal_parameter":
            index += 1
            continue
        has_default = index + 1 < len(children) and children[index + 1].type == "="
        name, type_text = _dart_formal_name_and_type(child, source)
        if name:
            result.append(_param(name, kind, pending_required and not has_default, type_text))
        pending_required = False
        index += 1
        if has_default:
            index += 1
            if index < len(children) and children[index].type not in {"formal_parameter", "required"}:
                index += 1
    return result


def _dart_parameters(param_list: Node, source: bytes) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for child in param_list.children:
        if child.type in _SKIP_PARAM_TYPES:
            continue
        if child.type == "formal_parameter":
            name, type_text = _dart_formal_name_and_type(child, source)
            if name:
                result.append(_param(name, "positional", True, type_text))
        elif child.type == "optional_formal_parameters":
            result.extend(_dart_optional_group(child, source))
    return result


def _dart_inner_signature(node: Node) -> Node:
    if node.type == "method_signature":
        for child in node.children:
            if child.type in {"function_signature", "constructor_signature"}:
                return child
    return node


def _dart_return(sig_node: Node, source: bytes) -> str | None:
    parts: list[str] = []
    for child in sig_node.children:
        if child.type in {"identifier", "formal_parameter_list", "formal_parameters"}:
            break
        if child.type in {".", "static", "const", "factory", "external"}:
            continue
        parts.append(_node_text(child, source))
    text = collapse_ws("".join(parts))
    return text or None


def _dart_param_list(sig_node: Node) -> Node | None:
    for child in sig_node.children:
        if child.type == "formal_parameter_list":
            return child
    return None


def _body_is_async(node: Node) -> bool:
    nxt = node.next_sibling
    if node.type == "function_signature" and node.parent is not None and node.parent.type == "method_signature":
        nxt = node.parent.next_sibling
    if node.type == "method_signature":
        nxt = node.next_sibling
    if nxt is None or nxt.type != "function_body":
        # Python/JS/TS encode async on the declaration itself.
        return any(child.type == "async" for child in node.children)
    return any(child.type == "async" for child in nxt.children)


def _decl_name(node: Node, source: bytes) -> str | None:
    for child in node.children:
        if child.type in {"function_signature", "constructor_signature"}:
            found = _decl_name(child, source)
            if found:
                return found
    identifiers = [
        child
        for child in node.children
        if child.type in {"identifier", "property_identifier"}
    ]
    if not identifiers:
        return None
    # Named constructors expose the class name and the constructor name.
    # The callable name is the last identifier on the signature node.
    return _node_text(identifiers[-1], source)


def _overload_prefixes(node: Node, source: bytes, name: str) -> list[str]:
    prefixes: list[str] = []
    sibling = node.prev_sibling
    while sibling is not None:
        if sibling.type in {"comment", "line_comment", "block_comment"}:
            sibling = sibling.prev_sibling
            continue
        if sibling.type not in {"function_signature", "method_signature"}:
            break
        if _decl_name(sibling, source) != name:
            break
        text = collapse_ws(_node_text(sibling, source)).rstrip(";").strip()
        if text:
            prefixes.append(text)
        sibling = sibling.prev_sibling
    prefixes.reverse()
    return prefixes


def _entity_source_span(node: Node) -> tuple[int, int]:
    start = node.start_byte
    end = node.end_byte
    parent = node.parent
    host = node
    if parent is not None and parent.type == "decorated_definition":
        start = parent.start_byte
        end = parent.end_byte
        host = parent
    sibling = host.prev_sibling
    while sibling is not None and sibling.type in {"annotation", "decorator", "marker_annotation"}:
        start = sibling.start_byte
        sibling = sibling.prev_sibling
    if parent is not None and parent.type == "declaration":
        start = min(start, parent.start_byte)
        end = max(end, parent.end_byte)
    body_owner = node
    if node.type == "function_signature" and parent is not None and parent.type == "method_signature":
        body_owner = parent
        start = min(start, parent.start_byte)
    nxt = body_owner.next_sibling
    if nxt is not None and nxt.type == "function_body":
        end = max(end, nxt.end_byte)
    return start, end


def _callable_signature(
    node: Node,
    source: bytes,
    language: str,
    name: str,
) -> tuple[str, list[dict[str, Any]], str | None]:
    if language == "python":
        header = _header_until(node, source, frozenset({"block"}))
        params_nodes = _direct_children(node, "parameters")
        parameters = _python_parameters(params_nodes[0], source) if params_nodes else []
        return_type = _python_return(node, source)
    elif language == "dart":
        header = collapse_ws(_node_text(node, source)).rstrip(";").strip()
        if _body_is_async(node) and not header.endswith(" async"):
            header = f"{header} async"
        inner = _dart_inner_signature(node)
        param_list = _dart_param_list(inner)
        parameters = _dart_parameters(param_list, source) if param_list is not None else []
        return_type = None if inner.type == "constructor_signature" else _dart_return(inner, source)
    else:
        header = _header_until(node, source, frozenset({"statement_block"}))
        formal = _direct_children(node, "formal_parameters")
        parameters = _js_parameters(formal[0], source) if formal else []
        return_type = _js_return(node, source)
    prefixes = _overload_prefixes(node, source, name)
    if prefixes:
        parts = prefixes + ([header] if header else [])
        header = " ; ".join(part for part in parts if part)
    return header, parameters, return_type


def _class_signature(node: Node, source: bytes) -> str:
    return _header_until(
        node,
        source,
        frozenset({"class_body", "block", "declaration_list", "enum_body", "extension_body"}),
    )


def attach_signature(
    entity: Any,
    node: Node | None,
    source: bytes,
    language: str,
    settings: SnippetSettings,
    *,
    file_id: str,
) -> None:
    """Fill signature and snippet fields on a code entity. Never raises for odd syntax."""
    if node is None or language not in SIGNATURE_LANGUAGES:
        return
    try:
        if entity.kind == "class":
            signature = _class_signature(node, source)
            parameters = None
            return_type = None
        else:
            signature, parameters, return_type = _callable_signature(
                node, source, language, entity.name
            )
        if not signature and not parameters and not return_type:
            return
        signature, parameters, return_type, truncated = fit_signature(
            signature, parameters, return_type
        )
        entity.signature = signature or None
        entity.parameters = parameters
        entity.return_type = return_type
        entity.signature_truncated = truncated
        if not settings.enabled or is_secret_basename(file_id):
            entity.snippet = None
            entity.snippet_truncated = False
            return
        start, end = _entity_source_span(node)
        text = source[start:end].decode("utf-8", errors="replace")
        snippet, snippet_truncated = truncate_text(text, settings.max_lines, settings.max_bytes)
        entity.snippet = snippet
        entity.snippet_truncated = snippet_truncated
    except Exception as exc:  # noqa: BLE001 — omit a misleading contract rather than failing the file
        logger.warning("Signature capture failed for {}: {}", getattr(entity, "name", "?"), exc)
        entity.signature = None
        entity.parameters = None
        entity.return_type = None
        entity.signature_truncated = False
        entity.snippet = None
        entity.snippet_truncated = False
