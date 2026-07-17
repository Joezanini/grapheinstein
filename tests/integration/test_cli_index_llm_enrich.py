import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli
from grapheinstein.core.index import index_project

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "llm_project"
runner = CliRunner()


def _fake_chat(**_kwargs):
    content = _kwargs.get("user_content", "")
    # Only enrich docs/auth.md content path meaningfully
    if "Auth Middleware" not in content and "auth.md" not in content and "auth.py" not in content:
        return {"entities": [], "relations": []}
    return {
        "entities": [
            {
                "name": "Auth Middleware",
                "kind": "domain_term",
                "evidence": "Auth Middleware validates JWT on each request.",
                "confidence": 0.95,
            }
        ],
        "relations": [
            {
                "type": "implements",
                "subject": "validate_token",
                "object": "Auth Middleware",
                "evidence": "validate_token implements the Auth Middleware checks described above.",
                "confidence": 0.9,
            },
            {
                "type": "depends_on",
                "subject": "src/auth.py",
                "object": "PyJWT",
                "evidence": "import jwt  # PyJWT",
                "confidence": 0.88,
            },
        ],
    }


def test_index_enrich_llm_writes_concepts(tmp_path: Path):
    out = tmp_path / "graph.json"
    index_project(
        FIXTURE,
        out,
        languages=["python"],
        include_docs=True,
        enrich_llm=True,
        llm_chat=_fake_chat,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert any(n["type"] == "concept" for n in data["nodes"])
    assert any(link["type"] == "implements" for link in data["links"])
    # ignored secret must not appear as enriched source mentions from secret.md
    assert not any(
        link.get("source") == "ignored/secret.md" for link in data["links"]
    )


def test_index_without_enrich_llm_no_concepts(tmp_path: Path):
    out = tmp_path / "graph.json"
    index_project(FIXTURE, out, languages=["python"], include_docs=True, enrich_llm=False)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert not any(n["type"] == "concept" for n in data["nodes"])


def test_cli_enrich_flag_help():
    result = runner.invoke(cli, ["index", "--help"])
    assert result.exit_code == 0
    assert "--enrich-llm" in result.output
    assert "--llm-model" in result.output
    assert "--llm-base-url" in result.output


def test_low_confidence_produces_no_edges(tmp_path: Path):
    def low(**_k):
        return {
            "entities": [
                {
                    "name": "Auth Middleware",
                    "kind": "domain_term",
                    "evidence": "Auth Middleware validates JWT on each request.",
                    "confidence": 0.1,
                }
            ],
            "relations": [
                {
                    "type": "implements",
                    "subject": "validate_token",
                    "object": "Auth Middleware",
                    "evidence": "validate_token implements the Auth Middleware checks described above.",
                    "confidence": 0.1,
                }
            ],
        }

    out = tmp_path / "graph.json"
    index_project(
        FIXTURE,
        out,
        languages=["python"],
        include_docs=True,
        enrich_llm=True,
        llm_chat=low,
        llm_confidence_threshold=0.5,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert not any(n["type"] == "concept" for n in data["nodes"])
    assert not any(link["type"] == "implements" for link in data["links"])
