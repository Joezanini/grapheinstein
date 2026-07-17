import json
from pathlib import Path

import pytest

from grapheinstein.core.graph import SCHEMA_VERSION, GraphError, load_artifact
from grapheinstein.core.index import index_project
from grapheinstein.core.parsers.media_av import Segment, TranscriptionResult

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "media_project"
OLD_V4 = Path(__file__).resolve().parents[1] / "fixtures" / "old_schema_v4_graph.json"


def _fake_ocr(path: Path) -> str:
    if path.name == "login.png":
        return "Sign in with SSO"
    return ""


def _fake_asr(path: Path) -> TranscriptionResult:
    if path.name == "setup.wav":
        return TranscriptionResult(
            segments=[Segment(0.0, 3.0, "First install the package with pip.")],
            duration=3.0,
        )
    if path.name == "corrupt.mp3":
        raise RuntimeError("corrupt")
    return TranscriptionResult(segments=[], duration=0.0)


def test_v5_media_nodes_and_provenance(tmp_path: Path):
    out = tmp_path / "graph.json"
    index_project(
        FIXTURE,
        out,
        languages=[],
        transcribe_media=True,
        ocr_extract=_fake_ocr,
        av_transcribe=_fake_asr,
        skip_media_deps_check=True,
    )
    data = load_artifact(out)
    assert data["schema_version"] == "5.0.0"
    assert SCHEMA_VERSION == "5.0.0"
    assert data["graph"]["transcribe_media"] is True

    media = [n for n in data["nodes"] if n["type"] == "media_text"]
    chunks = [n for n in data["nodes"] if n["type"] == "transcript_chunk"]
    assert media
    assert any("Sign in" in n["metadata"]["text"] for n in media)
    assert chunks
    for link in data["links"]:
        if link["type"] == "section_of" and (
            "::media_text::" in str(link["source"])
            or "::transcript_chunk::" in str(link["source"])
        ):
            assert link["provenance"] == "extracted"
        if link["type"] == "related_to":
            assert link["provenance"] == "inferred"
    assert any(link["type"] == "related_to" for link in data["links"])


def test_reject_v4_artifact():
    with pytest.raises(GraphError, match="unsupported|Re-index|schema_version"):
        load_artifact(OLD_V4)


def test_transcribe_media_false_metadata(tmp_path: Path):
    out = tmp_path / "graph.json"
    index_project(FIXTURE, out, languages=[], transcribe_media=False)
    data = json.loads(out.read_text())
    assert data["schema_version"] == "5.0.0"
    assert data["graph"]["transcribe_media"] is False
    assert not any(n["type"] == "media_text" for n in data["nodes"])
