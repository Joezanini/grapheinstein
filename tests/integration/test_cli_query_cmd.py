import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli
from grapheinstein.core.query import run_query

runner = CliRunner()
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "query_graphs"
AUTH = FIXTURE_DIR / "auth_chunks.json"
COMPOSED = FIXTURE_DIR / "composed_only.json"


def test_query_happy_path_no_answer(tmp_path: Path):
    out = tmp_path / "sub.json"
    result = runner.invoke(
        cli,
        [
            "query",
            "How does authentication work?",
            "--input",
            str(AUTH),
            "--output",
            str(out),
            "--no-answer",
            "--match-threshold",
            "0.3",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    sub = json.loads(out.read_text(encoding="utf-8"))
    assert sub["schema_version"] == "6.0.0"
    assert "authentication" in sub["graph"]["query_question"].lower()
    assert sub["graph"]["query_hit_ids"]
    assert all("provenance" in e for e in sub["links"])
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "1.0.0"
    assert payload["answer"]["status"] == "skipped"
    assert payload["visualization"]["node_count"] == len(sub["nodes"])
    assert "Visualization summary" in result.output or "Supporting subgraph" in result.output


def test_query_k_bounds_primary_hits(tmp_path: Path):
    out = tmp_path / "k3.json"
    result = runner.invoke(
        cli,
        [
            "query",
            "configuration",
            "--input",
            str(COMPOSED),
            "--output",
            str(out),
            "--k",
            "1",
            "--no-answer",
            "--match-threshold",
            "0.3",
        ],
    )
    assert result.exit_code == 0, result.output
    sub = json.loads(out.read_text(encoding="utf-8"))
    assert sub["graph"]["query_k"] == 1
    assert len(sub["graph"]["query_hit_ids"]) <= 1


def test_query_composed_only_fixture(tmp_path: Path):
    out = tmp_path / "comp.json"
    result = runner.invoke(
        cli,
        [
            "query",
            "How is configuration loaded?",
            "--input",
            str(COMPOSED),
            "--output",
            str(out),
            "--no-answer",
            "--match-threshold",
            "0.25",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_query_embedding_soft_skip_via_library(tmp_path: Path):
    out = tmp_path / "emb.json"

    def boom(_texts: list[str]) -> list[list[float]]:
        raise RuntimeError("no embed")

    result = run_query(
        "authentication",
        AUTH,
        out,
        k=5,
        match_threshold=0.3,
        want_answer=False,
        embed_fn=boom,
    )
    assert out.exists()
    assert result.embed_note is not None
    assert "skipped" in result.embed_note.lower()


def test_query_answer_with_injectable_chat(tmp_path: Path):
    out = tmp_path / "ans.json"
    # Library-level: CLI does not expose injectables; prove answer path via run_query
    result = run_query(
        "How does authentication work?",
        AUTH,
        out,
        k=5,
        match_threshold=0.3,
        want_answer=True,
        use_embeddings=False,
        chat_fn=lambda **_k: f"Auth works via tokens. [node:{'docs/auth.md::media_text::0'}]",
        list_models_fn=lambda _url: ["fake-model"],
        llm_model="fake-model",
    )
    assert result.answer_status == "ok"
    assert result.answer_text
    assert result.citations
    assert all(
        c.node_id in {n["id"] for n in json.loads(out.read_text())["nodes"]}
        for c in result.citations
        if c.kind == "node"
    )


def test_query_llm_unavailable_still_writes(tmp_path: Path):
    out = tmp_path / "skip.json"
    result = run_query(
        "authentication",
        AUTH,
        out,
        k=5,
        match_threshold=0.3,
        want_answer=True,
        use_embeddings=False,
        list_models_fn=lambda _url: [],
        llm_model="missing-model",
    )
    assert out.exists()
    assert result.answer_status == "skipped"
    assert result.visualization.node_count > 0
