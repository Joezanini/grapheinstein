"""Audio/video transcription → transcript_chunk nodes (optional [media] extras)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
from loguru import logger

from grapheinstein.core.graph import add_section_of_edge, add_transcript_chunk
from grapheinstein.core.parsers.media_ocr import LONG_FILE_BYTES

AV_EXTENSIONS = frozenset(
    {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".mp4", ".mov", ".mkv", ".webm"}
)
LONG_DURATION_SEC = 600.0
MERGE_MIN_CHARS = 400
MERGE_MIN_DURATION_SEC = 30.0

TranscribeFn = Callable[[Path], "TranscriptionResult"]


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TranscriptionResult:
    segments: Sequence[Segment]
    duration: float | None = None


def default_transcribe(path: Path) -> TranscriptionResult:
    from faster_whisper import WhisperModel

    model = WhisperModel("base", device="cpu")
    segments_iter, info = model.transcribe(str(path))
    segments: list[Segment] = []
    for seg in segments_iter:
        text = (seg.text or "").strip()
        if not text:
            continue
        segments.append(Segment(start=float(seg.start), end=float(seg.end), text=text))
    duration = getattr(info, "duration", None)
    return TranscriptionResult(
        segments=segments,
        duration=float(duration) if duration is not None else None,
    )


def merge_segments(segments: Sequence[Segment]) -> list[Segment]:
    """Merge consecutive segments until length/duration thresholds (research R8)."""
    if not segments:
        return []
    merged: list[Segment] = []
    buf_texts: list[str] = []
    buf_start = segments[0].start
    buf_end = segments[0].end

    def flush() -> None:
        nonlocal buf_texts, buf_start, buf_end
        if not buf_texts:
            return
        merged.append(
            Segment(start=buf_start, end=buf_end, text=" ".join(buf_texts).strip())
        )
        buf_texts = []

    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        if not buf_texts:
            buf_start = seg.start
            buf_end = seg.end
            buf_texts = [text]
            continue
        buf_texts.append(text)
        buf_end = seg.end
        combined = " ".join(buf_texts)
        duration = buf_end - buf_start
        if len(combined) >= MERGE_MIN_CHARS or duration >= MERGE_MIN_DURATION_SEC:
            flush()
            buf_start = seg.end
            buf_end = seg.end
    flush()
    return [s for s in merged if s.text]


def _warn_long_media(rel: str, size: int, duration: float | None) -> None:
    if size > LONG_FILE_BYTES:
        logger.warning(
            "Long media file ({} bytes > {} MB threshold): {}",
            size,
            LONG_FILE_BYTES // (1024 * 1024),
            rel,
        )
    elif duration is not None and duration > LONG_DURATION_SEC:
        logger.warning(
            "Long media file ({:.1f}s > {}s threshold): {}",
            duration,
            int(LONG_DURATION_SEC),
            rel,
        )


def merge_media_av(
    graph: nx.DiGraph,
    project_root: Path,
    *,
    transcribe: TranscribeFn | None = None,
) -> int:
    """Transcribe A/V files into transcript_chunk nodes. Returns skip count."""
    root = project_root.resolve()
    engine = transcribe or default_transcribe
    skips = 0
    for node_id, attrs in list(graph.nodes(data=True)):
        if attrs.get("type") != "file":
            continue
        if attrs.get("metadata", {}).get("symlink"):
            continue
        if attrs.get("metadata", {}).get("skipped"):
            continue
        suffix = Path(node_id).suffix.lower()
        if suffix not in AV_EXTENSIONS:
            continue
        path = root / node_id
        try:
            size = path.stat().st_size
        except OSError as exc:
            logger.warning("Skipping unreadable media {}: {}", node_id, exc)
            skips += 1
            continue
        # Size-based warn before expensive work
        if size > LONG_FILE_BYTES:
            _warn_long_media(node_id, size, None)
        try:
            result = engine(path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Transcription failed for {}: {}", node_id, exc)
            skips += 1
            continue
        _warn_long_media(node_id, size, result.duration)
        chunks = merge_segments(result.segments)
        if not chunks:
            logger.debug("No transcript text for {}", node_id)
            continue
        for i, chunk in enumerate(chunks, start=1):
            chunk_id = add_transcript_chunk(
                graph,
                file_id=node_id,
                text=chunk.text,
                start_sec=chunk.start,
                end_sec=chunk.end,
                ordinal=i,
            )
            add_section_of_edge(graph, chunk_id, node_id)
    return skips
