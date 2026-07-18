from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs" / "agent-integration.md"


def test_agent_integration_doc_exists_and_covers_surfaces():
    assert DOCS.is_file(), "docs/agent-integration.md must exist"
    text = DOCS.read_text(encoding="utf-8")
    assert "grapheinstein.api" in text
    assert "/index" in text
    assert "/query" in text
    assert "[serve]" in text or "grapheinstein[serve]" in text
