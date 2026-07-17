from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import app_typer
from grapheinstein.core.parsers.media_ocr import MediaExtrasError

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "media_project"
runner = CliRunner()


def test_cli_missing_media_extras(monkeypatch, tmp_path: Path):
    def boom():
        raise MediaExtrasError(
            "Media transcription requires optional extras "
            "(missing: faster-whisper). "
            "Install with: pip install 'grapheinstein[media]'"
        )

    monkeypatch.setattr("grapheinstein.core.index.ensure_media_deps", boom)
    out = tmp_path / "x.json"
    result = runner.invoke(
        app_typer,
        ["index", str(FIXTURE), "--transcribe-media", "-o", str(out)],
    )
    assert result.exit_code == 1
    assert "grapheinstein[media]" in result.output
    assert not out.exists()
