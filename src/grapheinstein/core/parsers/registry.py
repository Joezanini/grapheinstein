"""Language registry: ids, extensions, Tree-sitter Language/Parser loading."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from tree_sitter import Language, Parser

CANONICAL_LANGUAGES = (
    "python",
    "javascript",
    "typescript",
    "java",
    "go",
    "rust",
    "cpp",
    "sql",
)

DEFAULT_LANGUAGES: tuple[str, ...] = CANONICAL_LANGUAGES

# Extension → language (first match wins for ambiguous cases)
EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".h": "cpp",
    ".sql": "sql",
}


class LanguageError(ValueError):
    """Invalid language configuration."""


@dataclass(frozen=True)
class LanguageSpec:
    language_id: str
    language: Language
    # For typescript, tsx uses a separate Language
    alt_language: Language | None = None
    alt_extensions: frozenset[str] = frozenset()


def validate_languages(names: Iterable[str]) -> list[str]:
    """Return normalized unique language ids or raise LanguageError."""
    valid = set(CANONICAL_LANGUAGES)
    seen: list[str] = []
    invalid: list[str] = []
    for raw in names:
        name = str(raw).strip().lower()
        if not name:
            continue
        if name not in valid:
            invalid.append(str(raw).strip())
            continue
        if name not in seen:
            seen.append(name)
    if invalid:
        raise LanguageError(
            f"Unknown language(s): {', '.join(invalid)}. "
            f"Valid languages: {', '.join(CANONICAL_LANGUAGES)}"
        )
    return seen


def parse_languages_csv(value: str | None) -> list[str] | None:
    """Parse comma-separated languages. None/blank → None (use default)."""
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    parts = [p.strip() for p in text.split(",")]
    return validate_languages(parts)


def language_for_path(path: str | Path, enabled: Iterable[str]) -> str | None:
    enabled_set = set(enabled)
    suffix = Path(path).suffix.lower()
    lang = EXTENSION_MAP.get(suffix)
    if lang is None or lang not in enabled_set:
        return None
    return lang


def _load_language(language_id: str) -> LanguageSpec:
    if language_id == "python":
        import tree_sitter_python as tsp

        return LanguageSpec(language_id, Language(tsp.language()))
    if language_id == "javascript":
        import tree_sitter_javascript as tsjs

        return LanguageSpec(language_id, Language(tsjs.language()))
    if language_id == "typescript":
        import tree_sitter_typescript as tsts

        return LanguageSpec(
            language_id,
            Language(tsts.language_typescript()),
            alt_language=Language(tsts.language_tsx()),
            alt_extensions=frozenset({".tsx"}),
        )
    if language_id == "java":
        import tree_sitter_java as tsjava

        return LanguageSpec(language_id, Language(tsjava.language()))
    if language_id == "go":
        import tree_sitter_go as tsgo

        return LanguageSpec(language_id, Language(tsgo.language()))
    if language_id == "rust":
        import tree_sitter_rust as tsrust

        return LanguageSpec(language_id, Language(tsrust.language()))
    if language_id == "cpp":
        import tree_sitter_cpp as tscpp

        return LanguageSpec(language_id, Language(tscpp.language()))
    if language_id == "sql":
        import tree_sitter_sql as tssql

        return LanguageSpec(language_id, Language(tssql.language()))
    raise LanguageError(f"Unsupported language: {language_id}")


@lru_cache(maxsize=16)
def get_language_spec(language_id: str) -> LanguageSpec:
    return _load_language(language_id)


def get_parser_for_file(language_id: str, file_path: str | Path) -> tuple[Parser, Language]:
    spec = get_language_spec(language_id)
    suffix = Path(file_path).suffix.lower()
    if spec.alt_language is not None and suffix in spec.alt_extensions:
        lang = spec.alt_language
    else:
        lang = spec.language
    return Parser(lang), lang
