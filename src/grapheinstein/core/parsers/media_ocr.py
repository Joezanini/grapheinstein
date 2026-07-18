"""Image OCR → media_text nodes (optional [media] extras)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import networkx as nx
from loguru import logger

from grapheinstein.core.graph import add_media_text, add_section_of_edge

IMAGE_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff", ".bmp"}
)
LONG_FILE_BYTES = 100 * 1024 * 1024

ExtractTextFn = Callable[[Path], str]


class MediaExtrasError(Exception):
    """Raised when optional [media] Python packages are required but missing."""


def ensure_media_deps() -> None:
    """Fail closed if --transcribe-media is set but Python media extras are missing."""
    missing: list[str] = []
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        missing.append("pytesseract")
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        missing.append("Pillow")
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        missing.append("faster-whisper")
    if missing:
        raise MediaExtrasError(
            "Media transcription requires optional extras "
            f"(missing: {', '.join(missing)}). "
            "Install with: pip install 'grapheinstein[media]'"
        )


def default_ocr_extract(path: Path) -> str:
    import pytesseract
    from PIL import Image

    with Image.open(path) as img:
        text = pytesseract.image_to_string(img)
    return (text or "").strip()


def _warn_long_file(rel: str, size: int) -> None:
    if size > LONG_FILE_BYTES:
        logger.warning(
            "Long media file ({} bytes > {} MB threshold): {}",
            size,
            LONG_FILE_BYTES // (1024 * 1024),
            rel,
        )


def merge_media_ocr(
    graph: nx.DiGraph,
    project_root: Path,
    *,
    extract_text: ExtractTextFn | None = None,
) -> int:
    """OCR image files into media_text nodes. Returns skip count."""
    root = project_root.resolve()
    engine = extract_text or default_ocr_extract
    skips = 0
    for node_id, attrs in list(graph.nodes(data=True)):
        if attrs.get("type") != "file":
            continue
        if attrs.get("metadata", {}).get("symlink"):
            continue
        if attrs.get("metadata", {}).get("skipped"):
            continue
        suffix = Path(node_id).suffix.lower()
        if suffix not in IMAGE_EXTENSIONS:
            continue
        path = root / node_id
        try:
            size = path.stat().st_size
        except OSError as exc:
            logger.warning("Skipping unreadable image {}: {}", node_id, exc)
            skips += 1
            continue
        _warn_long_file(node_id, size)
        try:
            text = engine(path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("OCR failed for {}: {}", node_id, exc)
            skips += 1
            continue
        if not text or not text.strip():
            logger.debug("No OCR text for {}", node_id)
            continue
        media_id = add_media_text(graph, file_id=node_id, text=text.strip(), source="ocr")
        add_section_of_edge(graph, media_id, node_id)
    return skips
