from pathlib import Path

from grapheinstein.core.index import index_project
from grapheinstein.core.parsers.media_av import Segment, TranscriptionResult

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "media_project"


def test_index_media_av_chunks_and_corrupt_skip(tmp_path: Path):
    out = tmp_path / "g.json"

    def ocr(_p: Path) -> str:
        return ""

    def asr(path: Path) -> TranscriptionResult:
        if path.name == "setup.wav":
            return TranscriptionResult(
                segments=[
                    Segment(0.0, 1.0, "First"),
                    Segment(1.0, 2.0, "install the package with pip."),
                ],
                duration=2.0,
            )
        if path.name == "corrupt.mp3":
            raise RuntimeError("corrupt")
        return TranscriptionResult(segments=[], duration=0.0)

    written, stats = index_project(
        FIXTURE,
        out,
        languages=[],
        transcribe_media=True,
        ocr_extract=ocr,
        av_transcribe=asr,
        skip_media_deps_check=True,
    )
    assert written.exists()
    assert stats.transcript_chunk_count >= 1
    assert stats.parse_skips >= 1
