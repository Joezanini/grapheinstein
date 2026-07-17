"""Shared helpers: console, logging, and config loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import yaml
from loguru import logger
from rich.console import Console

from grapheinstein.core.parsers.llm_ollama import DEFAULT_BASE_URL, DEFAULT_MODEL
from grapheinstein.core.parsers.llm_enrich import DEFAULT_CONFIDENCE_THRESHOLD
from grapheinstein.core.parsers.registry import (
    DEFAULT_LANGUAGES,
    LanguageError,
    validate_languages,
)

DEFAULT_OUTPUT = "graph.json"
DEFAULT_LOG_LEVEL = "INFO"
USER_CONFIG_PATH = Path.home() / ".grapheinstein" / "config.yaml"

console = Console(stderr=True)


@dataclass(frozen=True)
class AppConfig:
    output: str = DEFAULT_OUTPUT
    log_level: str = DEFAULT_LOG_LEVEL
    languages: tuple[str, ...] = field(default_factory=lambda: tuple(DEFAULT_LANGUAGES))
    llm_model: str = DEFAULT_MODEL
    llm_base_url: str = DEFAULT_BASE_URL
    llm_confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD


class ConfigError(Exception):
    """Raised when a config file cannot be loaded or validated."""


def setup_logging(level: str = DEFAULT_LOG_LEVEL) -> None:
    """Configure Loguru to write diagnostics to stderr."""
    logger.remove()
    logger.add(
        lambda msg: console.print(msg, end=""),
        level=level.upper(),
        format="{time:HH:mm:ss} | {level:<8} | {message}",
        colorize=False,
    )


def _load_yaml_file(path: Path, *, required: bool) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise ConfigError(f"Config file not found: {path}")
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in config file {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config file {path} must be a YAML mapping/object")
    return data


def _coerce_languages(raw: Any, *, source: Path | None) -> list[str]:
    if not isinstance(raw, list):
        raise ConfigError(f"Config key 'languages' must be a list of strings ({source})")
    if not all(isinstance(item, str) for item in raw):
        raise ConfigError(f"Config key 'languages' must be a list of strings ({source})")
    try:
        return validate_languages(raw)
    except LanguageError as exc:
        raise ConfigError(str(exc)) from exc


def _coerce_threshold(raw: Any, *, source: Path | None) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(
            f"Config key 'llm_confidence_threshold' must be a number ({source})"
        ) from exc
    if value < 0.0 or value > 1.0:
        raise ConfigError(
            f"Config key 'llm_confidence_threshold' must be in [0.0, 1.0] ({source})"
        )
    return value


def _coerce_config(raw: dict[str, Any], *, source: Path | None) -> dict[str, Any]:
    known = {
        "output",
        "log_level",
        "languages",
        "llm_model",
        "llm_base_url",
        "llm_confidence_threshold",
    }
    unknown = set(raw) - known
    for key in sorted(unknown):
        logger.warning("Ignoring unknown config key {!r} from {}", key, source or "defaults")

    result: dict[str, Any] = {}
    if "output" in raw:
        if not isinstance(raw["output"], str) or not raw["output"].strip():
            raise ConfigError(f"Config key 'output' must be a non-empty string ({source})")
        result["output"] = raw["output"]
    if "log_level" in raw:
        if not isinstance(raw["log_level"], str) or not raw["log_level"].strip():
            raise ConfigError(f"Config key 'log_level' must be a non-empty string ({source})")
        result["log_level"] = raw["log_level"]
    if "languages" in raw:
        result["languages"] = _coerce_languages(raw["languages"], source=source)
    if "llm_model" in raw:
        if not isinstance(raw["llm_model"], str) or not raw["llm_model"].strip():
            raise ConfigError(f"Config key 'llm_model' must be a non-empty string ({source})")
        result["llm_model"] = raw["llm_model"].strip()
    if "llm_base_url" in raw:
        if not isinstance(raw["llm_base_url"], str) or not raw["llm_base_url"].strip():
            raise ConfigError(
                f"Config key 'llm_base_url' must be a non-empty string ({source})"
            )
        result["llm_base_url"] = raw["llm_base_url"].strip().rstrip("/")
    if "llm_confidence_threshold" in raw:
        result["llm_confidence_threshold"] = _coerce_threshold(
            raw["llm_confidence_threshold"], source=source
        )
    return result


def load_config(
    *,
    config_path: Path | None = None,
    output_override: Path | str | None = None,
    languages_override: Sequence[str] | None = None,
    llm_model_override: str | None = None,
    llm_base_url_override: str | None = None,
    user_config_path: Path | None = None,
) -> AppConfig:
    """
    Load config with precedence:
    CLI flags > --config file > ~/.grapheinstein/config.yaml > defaults.
    """
    merged: dict[str, Any] = {
        "output": DEFAULT_OUTPUT,
        "log_level": DEFAULT_LOG_LEVEL,
        "languages": list(DEFAULT_LANGUAGES),
        "llm_model": DEFAULT_MODEL,
        "llm_base_url": DEFAULT_BASE_URL,
        "llm_confidence_threshold": DEFAULT_CONFIDENCE_THRESHOLD,
    }

    default_user = user_config_path if user_config_path is not None else USER_CONFIG_PATH
    if config_path is not None:
        explicit = _coerce_config(
            _load_yaml_file(config_path, required=True),
            source=config_path,
        )
        merged.update(explicit)
    else:
        user_raw = _load_yaml_file(default_user, required=False)
        if user_raw:
            merged.update(_coerce_config(user_raw, source=default_user))

    if output_override is not None:
        merged["output"] = str(output_override)

    if languages_override is not None:
        try:
            merged["languages"] = validate_languages(languages_override)
        except LanguageError as exc:
            raise ConfigError(str(exc)) from exc

    if llm_model_override is not None:
        if not llm_model_override.strip():
            raise ConfigError("llm_model must be a non-empty string")
        merged["llm_model"] = llm_model_override.strip()

    if llm_base_url_override is not None:
        if not llm_base_url_override.strip():
            raise ConfigError("llm_base_url must be a non-empty string")
        merged["llm_base_url"] = llm_base_url_override.strip().rstrip("/")

    return AppConfig(
        output=merged["output"],
        log_level=merged["log_level"],
        languages=tuple(merged["languages"]),
        llm_model=merged["llm_model"],
        llm_base_url=merged["llm_base_url"],
        llm_confidence_threshold=float(merged["llm_confidence_threshold"]),
    )


def resolve_project_path(project_path: Path) -> Path:
    path = project_path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Project path does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Project path is not a directory: {path}")
    return path


def ensure_parent_dir(output_path: Path) -> None:
    parent = output_path.expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)
