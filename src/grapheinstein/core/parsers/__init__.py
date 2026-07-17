"""Parser plugins for multi-language code structure extraction."""

from __future__ import annotations

from grapheinstein.core.parsers.registry import (
    CANONICAL_LANGUAGES,
    DEFAULT_LANGUAGES,
    LanguageError,
    parse_languages_csv,
    validate_languages,
)
from grapheinstein.core.parsers.resolve import merge_code_structure
from grapheinstein.core.parsers.docs import merge_docs_structure
from grapheinstein.core.parsers.pdf import merge_pdf_structure

__all__ = [
    "CANONICAL_LANGUAGES",
    "DEFAULT_LANGUAGES",
    "LanguageError",
    "merge_code_structure",
    "merge_docs_structure",
    "merge_pdf_structure",
    "parse_languages_csv",
    "validate_languages",
]
