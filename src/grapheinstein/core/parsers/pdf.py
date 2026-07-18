"""PDF text extraction and section chunking via PyMuPDF."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import networkx as nx
from loguru import logger

from grapheinstein.core.graph import add_heading, add_section_of_edge

PDF_EXTENSIONS = frozenset({".pdf"})


@dataclass(frozen=True)
class PdfHeadingFact:
    name: str
    level: int
    page: int


def extract_pdf_sections(path: Path) -> list[PdfHeadingFact]:
    """Extract section headings from a PDF. Raises on open/extract failure."""
    import fitz  # PyMuPDF

    doc = fitz.open(path)
    try:
        if doc.is_encrypted and not doc.authenticate(""):
            raise ValueError("encrypted PDF")
        if doc.page_count == 0:
            return []

        toc = doc.get_toc(simple=True) or []
        sections: list[PdfHeadingFact] = []
        if toc:
            for level, title, page in toc:
                name = (title or "").strip() or "untitled"
                page_no = max(1, int(page))
                sections.append(PdfHeadingFact(name=name, level=max(1, int(level)), page=page_no))
            return sections

        # Fallback: one section per page using first non-empty line as title
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            text = page.get_text("text") or ""
            title = f"Page {page_index + 1}"
            for line in text.splitlines():
                stripped = line.strip()
                if stripped:
                    title = stripped[:120]
                    break
            sections.append(PdfHeadingFact(name=title, level=1, page=page_index + 1))
        return sections
    finally:
        doc.close()


def merge_pdf_structure(graph: nx.DiGraph, project_root: Path) -> int:
    """Extract PDF structure for indexed PDF files. Returns parse skip count."""
    skips = 0
    root = project_root.resolve()
    file_ids = [
        n
        for n, attrs in graph.nodes(data=True)
        if attrs.get("type") == "file"
        and Path(n).suffix.lower() in PDF_EXTENSIONS
        and not (attrs.get("metadata") or {}).get("skipped")
    ]
    for file_id in sorted(file_ids):
        path = root / file_id
        try:
            sections = extract_pdf_sections(path)
            if not sections:
                continue
            stack: list[tuple[int, str]] = []
            for section in sections:
                node_id = add_heading(
                    graph,
                    file_id=file_id,
                    name=section.name,
                    source="pdf",
                    page=section.page,
                    level=section.level,
                    locator=f"p{section.page}",
                )
                while stack and stack[-1][0] >= section.level:
                    stack.pop()
                parent = stack[-1][1] if stack else file_id
                add_section_of_edge(graph, node_id, parent)
                stack.append((section.level, node_id))
        except Exception as exc:  # noqa: BLE001 - non-fatal per file
            logger.warning("Skipping PDF structure for {}: {}", file_id, exc)
            skips += 1
    return skips


__all__ = [
    "PDF_EXTENSIONS",
    "PdfHeadingFact",
    "extract_pdf_sections",
    "merge_pdf_structure",
]
