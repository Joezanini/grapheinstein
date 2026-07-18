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


DEFAULT_EXPLAIN_HOPS = 2
DEFAULT_EXPLAIN_TOP_N = 3
DEFAULT_EXPLAIN_MATCH_THRESHOLD = 0.55
DEFAULT_EXPLAIN_NODE_CAP = 500
DEFAULT_PATH_MATCH_THRESHOLD = 0.55
DEFAULT_PATH_MAX_HOPS = 32
DEFAULT_PATH_CONFIDENCE_DEFAULT = 0.5
DEFAULT_PATH_CONFIDENCE_FLOOR = 0.35
DEFAULT_PATH_PROVENANCE_INFERRED_FACTOR = 1.75
DEFAULT_QUERY_K = 20
DEFAULT_QUERY_HOPS = 1
DEFAULT_QUERY_MATCH_THRESHOLD = 0.40
DEFAULT_QUERY_NODE_CAP = 500
MAX_QUERY_K = 200

DEFAULT_MAX_FILE_SIZE = 10_485_760
DEFAULT_CACHE_DIR = Path.home() / ".grapheinstein" / "cache"
DEFAULT_IGNORED_PATTERNS: tuple[str, ...] = (
    ".venv/",
    "venv/",
    "node_modules/",
    "__pycache__/",
    ".git/",
    "*.pyc",
    ".DS_Store",
)
DEFAULT_EMBEDDING_MODEL = DEFAULT_MODEL


@dataclass(frozen=True)
class AppConfig:
    output: str = DEFAULT_OUTPUT
    log_level: str = DEFAULT_LOG_LEVEL
    languages: tuple[str, ...] = field(default_factory=lambda: tuple(DEFAULT_LANGUAGES))
    llm_model: str = DEFAULT_MODEL
    llm_base_url: str = DEFAULT_BASE_URL
    llm_confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
    compress: bool = False
    versioned: bool = False
    explain_hops: int = DEFAULT_EXPLAIN_HOPS
    explain_top_n: int = DEFAULT_EXPLAIN_TOP_N
    explain_match_threshold: float = DEFAULT_EXPLAIN_MATCH_THRESHOLD
    explain_node_cap: int = DEFAULT_EXPLAIN_NODE_CAP
    path_match_threshold: float = DEFAULT_PATH_MATCH_THRESHOLD
    path_max_hops: int = DEFAULT_PATH_MAX_HOPS
    path_confidence_default: float = DEFAULT_PATH_CONFIDENCE_DEFAULT
    path_confidence_floor: float = DEFAULT_PATH_CONFIDENCE_FLOOR
    path_provenance_inferred_factor: float = DEFAULT_PATH_PROVENANCE_INFERRED_FACTOR
    query_k: int = DEFAULT_QUERY_K
    query_hops: int = DEFAULT_QUERY_HOPS
    query_match_threshold: float = DEFAULT_QUERY_MATCH_THRESHOLD
    query_node_cap: int = DEFAULT_QUERY_NODE_CAP
    ignored_patterns: tuple[str, ...] = field(
        default_factory=lambda: tuple(DEFAULT_IGNORED_PATTERNS)
    )
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    max_file_size: int = DEFAULT_MAX_FILE_SIZE
    cache_dir: Path = field(default_factory=lambda: DEFAULT_CACHE_DIR)


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


def _coerce_threshold(raw: Any, *, key: str, source: Path | None) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Config key {key!r} must be a number ({source})") from exc
    if value < 0.0 or value > 1.0:
        raise ConfigError(f"Config key {key!r} must be in [0.0, 1.0] ({source})")
    return value


def _coerce_positive_int(raw: Any, *, key: str, source: Path | None) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Config key {key!r} must be an integer ({source})") from exc
    if value < 1:
        raise ConfigError(f"Config key {key!r} must be >= 1 ({source})")
    return value


def _coerce_non_negative_int(raw: Any, *, key: str, source: Path | None) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Config key {key!r} must be an integer ({source})") from exc
    if value < 0:
        raise ConfigError(f"Config key {key!r} must be >= 0 ({source})")
    return value


def _coerce_bool(raw: Any, *, key: str, source: Path | None) -> bool:
    if isinstance(raw, bool):
        return raw
    raise ConfigError(f"Config key {key!r} must be a boolean ({source})")


def _coerce_non_empty_str(raw: Any, *, key: str, source: Path | None) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ConfigError(f"Config key {key!r} must be a non-empty string ({source})")
    return raw.strip()


def _coerce_ignored_patterns(raw: Any, *, source: Path | None) -> tuple[str, ...]:
    if not isinstance(raw, list):
        raise ConfigError(f"Config key 'ignored_patterns' must be a list of strings ({source})")
    if not all(isinstance(item, str) for item in raw):
        raise ConfigError(f"Config key 'ignored_patterns' must be a list of strings ({source})")
    return tuple(raw)


def _coerce_config(raw: dict[str, Any], *, source: Path | None) -> dict[str, Any]:
    known = {
        "output",
        "log_level",
        "languages",
        "llm_model",
        "llm_base_url",
        "llm_confidence_threshold",
        "compress",
        "versioned",
        "explain_hops",
        "explain_top_n",
        "explain_match_threshold",
        "explain_node_cap",
        "path_match_threshold",
        "path_max_hops",
        "path_confidence_default",
        "path_confidence_floor",
        "path_provenance_inferred_factor",
        "query_k",
        "query_hops",
        "query_match_threshold",
        "query_node_cap",
        "ignored_patterns",
        "embedding_model",
        "max_file_size",
        "cache_dir",
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
            raw["llm_confidence_threshold"],
            key="llm_confidence_threshold",
            source=source,
        )
    if "compress" in raw:
        result["compress"] = _coerce_bool(raw["compress"], key="compress", source=source)
    if "versioned" in raw:
        result["versioned"] = _coerce_bool(raw["versioned"], key="versioned", source=source)
    if "explain_hops" in raw:
        hops = _coerce_positive_int(raw["explain_hops"], key="explain_hops", source=source)
        if hops not in (1, 2):
            raise ConfigError(f"Config key 'explain_hops' must be 1 or 2 ({source})")
        result["explain_hops"] = hops
    if "explain_top_n" in raw:
        result["explain_top_n"] = _coerce_positive_int(
            raw["explain_top_n"], key="explain_top_n", source=source
        )
    if "explain_match_threshold" in raw:
        result["explain_match_threshold"] = _coerce_threshold(
            raw["explain_match_threshold"],
            key="explain_match_threshold",
            source=source,
        )
    if "explain_node_cap" in raw:
        result["explain_node_cap"] = _coerce_positive_int(
            raw["explain_node_cap"], key="explain_node_cap", source=source
        )
    if "path_match_threshold" in raw:
        result["path_match_threshold"] = _coerce_threshold(
            raw["path_match_threshold"],
            key="path_match_threshold",
            source=source,
        )
    if "path_max_hops" in raw:
        result["path_max_hops"] = _coerce_non_negative_int(
            raw["path_max_hops"], key="path_max_hops", source=source
        )
    if "path_confidence_default" in raw:
        result["path_confidence_default"] = _coerce_threshold(
            raw["path_confidence_default"],
            key="path_confidence_default",
            source=source,
        )
    if "path_confidence_floor" in raw:
        result["path_confidence_floor"] = _coerce_threshold(
            raw["path_confidence_floor"],
            key="path_confidence_floor",
            source=source,
        )
    if "path_provenance_inferred_factor" in raw:
        try:
            factor = float(raw["path_provenance_inferred_factor"])
        except (TypeError, ValueError) as exc:
            raise ConfigError(
                f"Config key 'path_provenance_inferred_factor' must be a number ({source})"
            ) from exc
        if factor <= 0:
            raise ConfigError(
                f"Config key 'path_provenance_inferred_factor' must be > 0 ({source})"
            )
        result["path_provenance_inferred_factor"] = factor
    if "query_k" in raw:
        qk = _coerce_positive_int(raw["query_k"], key="query_k", source=source)
        if qk > MAX_QUERY_K:
            raise ConfigError(
                f"Config key 'query_k' must be <= {MAX_QUERY_K} ({source})"
            )
        result["query_k"] = qk
    if "query_hops" in raw:
        hops = _coerce_positive_int(raw["query_hops"], key="query_hops", source=source)
        if hops not in (1, 2):
            raise ConfigError(f"Config key 'query_hops' must be 1 or 2 ({source})")
        result["query_hops"] = hops
    if "query_match_threshold" in raw:
        result["query_match_threshold"] = _coerce_threshold(
            raw["query_match_threshold"],
            key="query_match_threshold",
            source=source,
        )
    if "query_node_cap" in raw:
        result["query_node_cap"] = _coerce_positive_int(
            raw["query_node_cap"], key="query_node_cap", source=source
        )
    if "ignored_patterns" in raw:
        result["ignored_patterns"] = _coerce_ignored_patterns(
            raw["ignored_patterns"], source=source
        )
    if "embedding_model" in raw:
        result["embedding_model"] = _coerce_non_empty_str(
            raw["embedding_model"], key="embedding_model", source=source
        )
    if "max_file_size" in raw:
        result["max_file_size"] = _coerce_positive_int(
            raw["max_file_size"], key="max_file_size", source=source
        )
    if "cache_dir" in raw:
        result["cache_dir"] = _coerce_non_empty_str(
            raw["cache_dir"], key="cache_dir", source=source
        )
    return result


def load_config(
    *,
    config_path: Path | None = None,
    output_override: Path | str | None = None,
    languages_override: Sequence[str] | None = None,
    llm_model_override: str | None = None,
    llm_base_url_override: str | None = None,
    compress_override: bool | None = None,
    versioned_override: bool | None = None,
    explain_hops_override: int | None = None,
    explain_top_n_override: int | None = None,
    explain_match_threshold_override: float | None = None,
    explain_node_cap_override: int | None = None,
    path_match_threshold_override: float | None = None,
    path_max_hops_override: int | None = None,
    query_k_override: int | None = None,
    query_hops_override: int | None = None,
    query_match_threshold_override: float | None = None,
    query_node_cap_override: int | None = None,
    ignored_patterns_override: Sequence[str] | None = None,
    embedding_model_override: str | None = None,
    max_file_size_override: int | None = None,
    cache_dir_override: Path | str | None = None,
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
        "compress": False,
        "versioned": False,
        "explain_hops": DEFAULT_EXPLAIN_HOPS,
        "explain_top_n": DEFAULT_EXPLAIN_TOP_N,
        "explain_match_threshold": DEFAULT_EXPLAIN_MATCH_THRESHOLD,
        "explain_node_cap": DEFAULT_EXPLAIN_NODE_CAP,
        "path_match_threshold": DEFAULT_PATH_MATCH_THRESHOLD,
        "path_max_hops": DEFAULT_PATH_MAX_HOPS,
        "path_confidence_default": DEFAULT_PATH_CONFIDENCE_DEFAULT,
        "path_confidence_floor": DEFAULT_PATH_CONFIDENCE_FLOOR,
        "path_provenance_inferred_factor": DEFAULT_PATH_PROVENANCE_INFERRED_FACTOR,
        "query_k": DEFAULT_QUERY_K,
        "query_hops": DEFAULT_QUERY_HOPS,
        "query_match_threshold": DEFAULT_QUERY_MATCH_THRESHOLD,
        "query_node_cap": DEFAULT_QUERY_NODE_CAP,
        "ignored_patterns": list(DEFAULT_IGNORED_PATTERNS),
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
        "max_file_size": DEFAULT_MAX_FILE_SIZE,
        "cache_dir": str(DEFAULT_CACHE_DIR),
    }

    default_user = user_config_path if user_config_path is not None else USER_CONFIG_PATH
    path_threshold_from_file = False
    if config_path is not None:
        explicit = _coerce_config(
            _load_yaml_file(config_path, required=True),
            source=config_path,
        )
        path_threshold_from_file = "path_match_threshold" in explicit
        llm_model_from_file = "llm_model" in explicit
        embedding_model_from_file = "embedding_model" in explicit
        merged.update(explicit)
    else:
        user_raw = _load_yaml_file(default_user, required=False)
        llm_model_from_file = False
        embedding_model_from_file = False
        if user_raw:
            coerced = _coerce_config(user_raw, source=default_user)
            path_threshold_from_file = "path_match_threshold" in coerced
            llm_model_from_file = "llm_model" in coerced
            embedding_model_from_file = "embedding_model" in coerced
            merged.update(coerced)

    if llm_model_from_file and not embedding_model_from_file:
        # Older configs that only set llm_model keep using it for embeddings too.
        merged["embedding_model"] = merged["llm_model"]

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

    if compress_override is not None:
        merged["compress"] = bool(compress_override)
    if versioned_override is not None:
        merged["versioned"] = bool(versioned_override)

    if explain_hops_override is not None:
        if explain_hops_override not in (1, 2):
            raise ConfigError("explain_hops must be 1 or 2")
        merged["explain_hops"] = explain_hops_override
    if explain_top_n_override is not None:
        if explain_top_n_override < 1:
            raise ConfigError("explain_top_n must be >= 1")
        merged["explain_top_n"] = int(explain_top_n_override)
    if explain_match_threshold_override is not None:
        thr = float(explain_match_threshold_override)
        if thr < 0.0 or thr > 1.0:
            raise ConfigError("explain_match_threshold must be in [0.0, 1.0]")
        merged["explain_match_threshold"] = thr
    if explain_node_cap_override is not None:
        if explain_node_cap_override < 1:
            raise ConfigError("explain_node_cap must be >= 1")
        merged["explain_node_cap"] = int(explain_node_cap_override)

    if path_match_threshold_override is not None:
        thr = float(path_match_threshold_override)
        if thr < 0.0 or thr > 1.0:
            raise ConfigError("path_match_threshold must be in [0.0, 1.0]")
        merged["path_match_threshold"] = thr
    elif not path_threshold_from_file:
        # Inherit explain match threshold when path key was not set in config files
        merged["path_match_threshold"] = float(merged["explain_match_threshold"])

    if path_max_hops_override is not None:
        if path_max_hops_override < 0:
            raise ConfigError("path_max_hops must be >= 0")
        merged["path_max_hops"] = int(path_max_hops_override)

    if query_k_override is not None:
        if query_k_override < 1 or query_k_override > MAX_QUERY_K:
            raise ConfigError(f"query_k must be between 1 and {MAX_QUERY_K}")
        merged["query_k"] = int(query_k_override)
    if query_hops_override is not None:
        if query_hops_override not in (1, 2):
            raise ConfigError("query_hops must be 1 or 2")
        merged["query_hops"] = query_hops_override
    if query_match_threshold_override is not None:
        thr = float(query_match_threshold_override)
        if thr < 0.0 or thr > 1.0:
            raise ConfigError("query_match_threshold must be in [0.0, 1.0]")
        merged["query_match_threshold"] = thr
    if query_node_cap_override is not None:
        if query_node_cap_override < 1:
            raise ConfigError("query_node_cap must be >= 1")
        merged["query_node_cap"] = int(query_node_cap_override)

    if ignored_patterns_override is not None:
        if not all(isinstance(item, str) for item in ignored_patterns_override):
            raise ConfigError("ignored_patterns must be a list of strings")
        merged["ignored_patterns"] = list(ignored_patterns_override)

    if embedding_model_override is not None:
        if not embedding_model_override.strip():
            raise ConfigError("embedding_model must be a non-empty string")
        merged["embedding_model"] = embedding_model_override.strip()

    if max_file_size_override is not None:
        if max_file_size_override < 1:
            raise ConfigError("max_file_size must be >= 1")
        merged["max_file_size"] = int(max_file_size_override)

    if cache_dir_override is not None:
        if not str(cache_dir_override).strip():
            raise ConfigError("cache_dir must be a non-empty path")
        merged["cache_dir"] = str(cache_dir_override)

    cache_dir_path = Path(str(merged["cache_dir"])).expanduser()
    try:
        cache_dir_path = cache_dir_path.resolve()
    except OSError:
        pass

    return AppConfig(
        output=merged["output"],
        log_level=merged["log_level"],
        languages=tuple(merged["languages"]),
        llm_model=merged["llm_model"],
        llm_base_url=merged["llm_base_url"],
        llm_confidence_threshold=float(merged["llm_confidence_threshold"]),
        compress=bool(merged["compress"]),
        versioned=bool(merged["versioned"]),
        explain_hops=int(merged["explain_hops"]),
        explain_top_n=int(merged["explain_top_n"]),
        explain_match_threshold=float(merged["explain_match_threshold"]),
        explain_node_cap=int(merged["explain_node_cap"]),
        path_match_threshold=float(merged["path_match_threshold"]),
        path_max_hops=int(merged["path_max_hops"]),
        path_confidence_default=float(merged["path_confidence_default"]),
        path_confidence_floor=float(merged["path_confidence_floor"]),
        path_provenance_inferred_factor=float(merged["path_provenance_inferred_factor"]),
        query_k=int(merged["query_k"]),
        query_hops=int(merged["query_hops"]),
        query_match_threshold=float(merged["query_match_threshold"]),
        query_node_cap=int(merged["query_node_cap"]),
        ignored_patterns=tuple(merged["ignored_patterns"]),
        embedding_model=str(merged["embedding_model"]),
        max_file_size=int(merged["max_file_size"]),
        cache_dir=cache_dir_path,
    )


DEFAULT_CONFIG_TEMPLATE = f"""\
# Grapheinstein configuration
#
# Precedence: CLI flags > --config file > ~/.grapheinstein/config.yaml > built-in defaults.
# Every key below is optional; omit any key to keep its default.

# Path (and glob) patterns to skip during indexing, in addition to .gitignore.
# Uses gitignore-style syntax via pathspec.
ignored_patterns:
{chr(10).join(f'  - "{pattern}"' for pattern in DEFAULT_IGNORED_PATTERNS)}

# Local Ollama model used for embedding calls (explain/path/query/index).
embedding_model: "{DEFAULT_EMBEDDING_MODEL}"

# Local Ollama model used for LLM enrichment/explanation/answer text.
llm_model: "{DEFAULT_MODEL}"

# Base URL for the local Ollama server.
llm_base_url: "{DEFAULT_BASE_URL}"

# Maximum file size (bytes) to parse/chunk/embed during indexing.
# Files larger than this are kept as inventory nodes but not parsed.
max_file_size: {DEFAULT_MAX_FILE_SIZE}

# Directory for the local parse/chunk/embedding cache (created on first use).
cache_dir: "{DEFAULT_CACHE_DIR}"

# Path for the graph.json artifact written by `grapheinstein index`.
output: "{DEFAULT_OUTPUT}"

# Diagnostic log verbosity: DEBUG, INFO, WARNING, ERROR.
log_level: "{DEFAULT_LOG_LEVEL}"
"""


def write_config_template(path: Path, *, force: bool = False) -> Path:
    """
    Write the commented starter config template to ``path``.

    Creates parent directories as needed. Raises ``ConfigError`` if ``path``
    already exists and ``force`` is False (callers handle any interactive
    overwrite confirmation before passing ``force=True``).
    """
    destination = path.expanduser()
    if destination.exists() and not force:
        raise ConfigError(
            f"Config file already exists at {destination}; use --force to overwrite"
        )
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConfigError(f"Cannot create directory {destination.parent}: {exc}") from exc
    try:
        destination.write_text(DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot write config file {destination}: {exc}") from exc
    return destination


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
