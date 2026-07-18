import json
from pathlib import Path

from grapheinstein.core.index import index_project
from grapheinstein.core.parsers.media_av import TranscriptionResult

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
    rels = [link for link in data["links"] if link["type"] == "related_to"]
    assert rels
    assert all(link["provenance"] == "inferred" for link in rels)
    assert any(
        link["source"] == "assets/login.png" and link["target"] == "src/login.py"
        for link in rels
    )
