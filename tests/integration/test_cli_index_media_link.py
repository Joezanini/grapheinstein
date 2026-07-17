import json
from pathlib import Path

from grapheinstein.core.index import index_project
from grapheinstein.core.parsers.media_av import Segment, TranscriptionResult

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "media_project"


def test_related_to_filename_link(tmp_path: Path):
    out = tmp_path / "g.json"

    def ocr(path: Path) -> str:
        return "Sign in with SSO" if path.name == "login.png" else ""

    def asr(_path: Path) -> TranscriptionResult:
        return TranscriptionResult(segments=[], duration=0.0)

    index_project(
        FIXTURE,
        out,
        languages=[],
        transcribe_media=True,
        ocr_extract=ocr,
        av_transcribe=asr,
        skip_media_deps_check=True,
    )
    data = json.loads(out.read_text())
    rels = [l for l in data["links"] if l["type"] == "related_to"]
    assert rels
    assert all(l["provenance"] == "inferred" for l in rels)
    assert any(
        l["source"] == "assets/login.png" and l["target"] == "src/login.py" for l in rels
    )
