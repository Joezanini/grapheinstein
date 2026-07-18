import pytest

from grapheinstein.core.parsers.registry import (
    CANONICAL_LANGUAGES,
    LanguageError,
    parse_languages_csv,
    validate_languages,
)


def test_validate_languages_ok():
    assert validate_languages(["Python", "go"]) == ["python", "go"]


def test_validate_languages_unknown():
    with pytest.raises(LanguageError, match="brainfuck"):
        validate_languages(["python", "brainfuck"])


def test_parse_languages_csv():
    assert parse_languages_csv("python, go") == ["python", "go"]
    assert parse_languages_csv(None) is None
    assert set(CANONICAL_LANGUAGES) >= {"python", "sql"}
