"""Tree-sitter query strings per language."""

from __future__ import annotations

QUERIES: dict[str, str] = {
    "python": """
(function_definition
  name: (identifier) @function.name) @function.def

(class_definition
  name: (identifier) @class.name) @class.def

(class_definition
  body: (block
    (function_definition
      name: (identifier) @method.name) @method.def))

(import_statement) @import
(import_from_statement) @import

(call
  function: (identifier) @call.name)
(call
  function: (attribute
    attribute: (identifier) @call.attr))
""",
    "javascript": """
(function_declaration
  name: (identifier) @function.name) @function.def

(class_declaration
  name: (identifier) @class.name) @class.def

(method_definition
  name: (property_identifier) @method.name) @method.def

(import_statement) @import

(call_expression
  function: (identifier) @call.name)
(call_expression
  function: (member_expression
    property: (property_identifier) @call.attr))
""",
    "typescript": """
(function_declaration
  name: (identifier) @function.name) @function.def

(class_declaration
  name: (type_identifier) @class.name) @class.def

(method_definition
  name: (property_identifier) @method.name) @method.def

(import_statement) @import

(call_expression
  function: (identifier) @call.name)
(call_expression
  function: (member_expression
    property: (property_identifier) @call.attr))
""",
    "java": """
(method_declaration
  name: (identifier) @method.name) @method.def

(class_declaration
  name: (identifier) @class.name) @class.def

(import_declaration) @import

(method_invocation
  name: (identifier) @call.name)
""",
    "go": """
(function_declaration
  name: (identifier) @function.name) @function.def

(method_declaration
  name: (field_identifier) @method.name) @method.def

(type_declaration
  (type_spec
    name: (type_identifier) @class.name)) @class.def

(import_declaration) @import

(call_expression
  function: (identifier) @call.name)
(call_expression
  function: (selector_expression
    field: (field_identifier) @call.attr))
""",
    "rust": """
(function_item
  name: (identifier) @function.name) @function.def

(impl_item
  type: (type_identifier) @class.name) @class.def

(function_item
  name: (identifier) @method.name) @method.def

(use_declaration) @import

(call_expression
  function: (identifier) @call.name)
(call_expression
  function: (field_expression
    field: (field_identifier) @call.attr))
""",
    "cpp": """
(function_definition
  declarator: (function_declarator
    declarator: (identifier) @function.name)) @function.def

(class_specifier
  name: (type_identifier) @class.name) @class.def

(function_definition
  declarator: (function_declarator
    declarator: (field_identifier) @method.name)) @method.def

(preproc_include) @import

(call_expression
  function: (identifier) @call.name)
(call_expression
  function: (field_expression
    field: (field_identifier) @call.attr))
""",
    "sql": """
(create_function
  (object_reference
    (identifier) @function.name)) @function.def
""",
}


def get_query(language_id: str) -> str:
    return QUERIES.get(language_id, "")
