"""Markdown / TXT / RST documentation structure extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
from loguru import logger

DOC_EXTENSIONS = frozenset({".md", ".markdown", ".txt", ".rst", ".rest"})

_MD_ATX = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_ANGLE_LINK = re.compile(r"<([^>]+)>")
_RST_LINK = re.compile(r"`([^`<]+)\s*<([^>]+)>`_")
_SETTEXT_UNDER = re.compile(r"^(=+|-+|~+|\^+|\*+|\"+|'+|#+)$")


@dataclass(frozen=True)
class HeadingFact:
    name: str
    level: int
    start_line: int
    source: str


@dataclass(frozen=True)
class LinkFact:
    target: str
    start_line: int
    section_index: int | None  # index into headings list, or None if before any


def _source_for_suffix(suffix: str) -> str:
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix in {".rst", ".rest"}:
        return "rst"
    return "txt"


def _underline_level(ch: str) -> int:
    order = {"=": 1, "-": 2, "~": 3, "^": 4, "*": 5, '"': 6, "'": 7, "#": 1}
    return order.get(ch, 2)


def _extract_markdown(lines: list[str], source: str) -> tuple[list[HeadingFact], list[LinkFact]]:
    headings: list[HeadingFact] = []
    links: list[LinkFact] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        line_no = i + 1
        m = _MD_ATX.match(line)
        if m:
            headings.append(
                HeadingFact(
                    name=m.group(2).strip(),
                    level=len(m.group(1)),
                    start_line=line_no,
                    source=source,
                )
            )
            i += 1
            continue
        # Setext
        if i + 1 < len(lines) and line.strip() and _SETTEXT_UNDER.match(lines[i + 1].strip()):
            under = lines[i + 1].strip()
            level = 1 if under[0] == "=" else 2
            headings.append(
                HeadingFact(name=line.strip(), level=level, start_line=line_no, source=source)
            )
            i += 2
            continue
        section_index = len(headings) - 1 if headings else None
        for match in _MD_LINK.finditer(line):
            target = match.group(2).strip()
            if target and not target.startswith("#"):
                # keep fragment links to same-file anchors as "#..."
                links.append(LinkFact(target=target, start_line=line_no, section_index=section_index))
            elif target.startswith("#"):
                links.append(LinkFact(target=target, start_line=line_no, section_index=section_index))
        for match in _ANGLE_LINK.finditer(line):
            target = match.group(1).strip()
            if "/" in target or target.endswith((".md", ".txt", ".rst", ".pdf")):
                links.append(LinkFact(target=target, start_line=line_no, section_index=section_index))
        i += 1
    return headings, links


def _extract_rst_or_txt(lines: list[str], source: str) -> tuple[list[HeadingFact], list[LinkFact]]:
    headings: list[HeadingFact] = []
    links: list[LinkFact] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        line_no = i + 1
        # overline + title + underline
        if (
            i + 2 < len(lines)
            and _SETTEXT_UNDER.match(line.strip())
            and lines[i + 1].strip()
            and _SETTEXT_UNDER.match(lines[i + 2].strip())
            and lines[i + 2].strip()[0] == line.strip()[0]
        ):
            title = lines[i + 1].strip()
            level = _underline_level(line.strip()[0])
            headings.append(
                HeadingFact(name=title, level=level, start_line=i + 2, source=source)
            )
            i += 3
            continue
        # title + underline
        if (
            i + 1 < len(lines)
            and line.strip()
            and not _SETTEXT_UNDER.match(line.strip())
            and _SETTEXT_UNDER.match(lines[i + 1].strip())
            and len(lines[i + 1].strip()) >= max(3, len(line.strip()) // 2)
        ):
            under = lines[i + 1].strip()
            headings.append(
                HeadingFact(
                    name=line.strip(),
                    level=_underline_level(under[0]),
                    start_line=line_no,
                    source=source,
                )
            )
            i += 2
            continue
        section_index = len(headings) - 1 if headings else None
        for match in _RST_LINK.finditer(line):
            links.append(
                LinkFact(target=match.group(2).strip(), start_line=line_no, section_index=section_index)
            )
        for match in _MD_LINK.finditer(line):
            links.append(
                LinkFact(target=match.group(2).strip(), start_line=line_no, section_index=section_index)
            )
        i += 1
    return headings, links


def extract_docs_structure(
    path: Path, *, source: str | None = None
) -> tuple[list[HeadingFact], list[LinkFact]]:
    """Parse a documentation file into headings and link facts."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    src = source or _source_for_suffix(path.suffix.lower())
    if src == "markdown":
        return _extract_markdown(lines, src)
    return _extract_rst_or_txt(lines, src)


def merge_docs_structure(graph: nx.DiGraph, project_root: Path) -> int:
    """Extract docs structure for indexed doc files. Returns parse skip count."""
    from grapheinstein.core.parsers.resolve_docs import resolve_and_emit_docs

    skips = 0
    root = project_root.resolve()
    file_ids = [
        n
        for n, attrs in graph.nodes(data=True)
        if attrs.get("type") == "file" and Path(n).suffix.lower() in DOC_EXTENSIONS
    ]
    for file_id in sorted(file_ids):
        path = root / file_id
        try:
            headings, links = extract_docs_structure(path)
            resolve_and_emit_docs(
                graph,
                file_id=file_id,
                headings=headings,
                links=links,
                project_root=root,
            )
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Skipping docs structure for {}: {}", file_id, exc)
            skips += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping docs structure for {}: {}", file_id, exc)
            skips += 1
    return skips


__all__ = [
    "DOC_EXTENSIONS",
    "HeadingFact",
    "LinkFact",
    "extract_docs_structure",
    "merge_docs_structure",
]
