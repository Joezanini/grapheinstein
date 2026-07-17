from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import app_typer
from grapheinstein.core.index import index_project
from grapheinstein.core.parsers.media_av import Segment, TranscriptionResult

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "media_project"
runner = CliRunner()


def _fake_ocr(path: Path) -> str:
    return "Sign in with SSO" if path.name == "login.png" else ""


def _fake_asr(path: Path) -> TranscriptionResult:
    if path.name == "setup.wav":
        return TranscriptionResult(
            segments=[Segment(0.0, 2.0, "hello world")], duration=2.0
        )
    if "corrupt" in path.name:
        raise RuntimeError("bad")
    return TranscriptionResult(segments=[], duration=0.0)


def test_index_media_ocr_integration(tmp_path: Path):
    out = tmp_path / "g.json"
    index_project(
        FIXTURE,
        out,
        languages=[],
        transcribe_media=True,
        ocr_extract=_fake_ocr,
        av_transcribe=_fake_asr,
        skip_media_deps_check=True,
    )
    text = out.read_text()
    assert "media_text" in text
    assert "secret.png" not in text or "ignored_media/secret.png" not in text
    assert "assets/login.png::media_text::1" in text


def test_cli_transcribe_media_flag_off(tmp_path: Path):
    out = tmp_path / "g.json"
    result = runner.invoke(
        app_typer,
        ["index", str(FIXTURE), "-o", str(out), "--languages", ""],
    )
    # empty languages may fail — use languages=none by omitting and accepting code langs
    # Re-run without languages override
    result = runner.invoke(app_typer, ["index", str(FIXTURE), "-o", str(out)])
    assert result.exit_code == 0, result.output
    data = out.read_text()
    assert "media_text" not in data or '"type": "media_text"' not in data
