import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from grapheinstein.cli import app_typer
from grapheinstein.core.index import MediaExtrasError, index_project
from grapheinstein.core.parsers.media_av import Segment, TranscriptionResult

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "media_project"
runner = CliRunner()


def _engines():
    def ocr(path: Path) -> str:
        return "Sign in with SSO" if path.name == "login.png" else ""

    def asr(path: Path) -> TranscriptionResult:
        if path.name == "setup.wav":
            return TranscriptionResult(
                segments=[Segment(0.0, 1.0, "hello")], duration=1.0
            )
        if "corrupt" in path.name:
            raise RuntimeError("bad")
        return TranscriptionResult(segments=[], duration=0.0)

    return ocr, asr


def test_flag_off_no_media(tmp_path: Path):
    out = tmp_path / "off.json"
    index_project(FIXTURE, out, languages=[], transcribe_media=False)
    data = json.loads(out.read_text())
    assert data["graph"]["transcribe_media"] is False
    assert not any(n["type"] in {"media_text", "transcript_chunk"} for n in data["nodes"])
    assert not any(l["type"] == "related_to" for l in data["links"])


def test_flag_on_with_stubs(tmp_path: Path):
    out = tmp_path / "on.json"
    ocr, asr = _engines()
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
    assert data["graph"]["transcribe_media"] is True
    assert any(n["type"] == "media_text" for n in data["nodes"])


def test_cli_index_with_transcribe_media_flag(tmp_path: Path, monkeypatch):
    out = tmp_path / "alias.json"
    ocr, asr = _engines()

    def fake_index(project_path, output_path, **kwargs):
        assert kwargs.get("transcribe_media") is True
        return index_project(
            project_path,
            output_path,
            languages=[],
            transcribe_media=True,
            ocr_extract=ocr,
            av_transcribe=asr,
            skip_media_deps_check=True,
        )

    monkeypatch.setattr("grapheinstein.cli.index_project", fake_index)
    result = runner.invoke(
        app_typer,
        ["index", str(FIXTURE), "--transcribe-media", "-o", str(out)],
    )
    assert result.exit_code == 0, result.output


def test_missing_extras_via_build(monkeypatch):
    def boom():
        raise MediaExtrasError("Install with: pip install 'grapheinstein[media]'")

    monkeypatch.setattr("grapheinstein.core.index.ensure_media_deps", boom)
    from grapheinstein.core.index import build_inventory_graph

    with pytest.raises(MediaExtrasError, match="grapheinstein\\[media\\]"):
        build_inventory_graph(FIXTURE, languages=[], transcribe_media=True)
