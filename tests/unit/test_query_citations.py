import json
from pathlib import Path

from grapheinstein.core.query import (
    fallback_citations,
    generate_cited_answer,
    parse_and_filter_citations,
    run_query,
)

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "query_graphs" / "auth_chunks.json"
)


def test_parse_filters_invalid_citations():
    artifact = {
        "nodes": [{"id": "a", "type": "file", "metadata": {}}],
        "links": [
            {
                "source": "a",
                "target": "a",
                "type": "contains",
                "provenance": "extracted",
            }
        ],
    }
    text = "See [node:a] and fake [node:missing] and [edge:a->a:contains] bad [edge:x->y:calls]."
    cites = parse_and_filter_citations(text, artifact)
    kinds = {(c.kind, c.node_id or (c.source, c.target, c.edge_type)) for c in cites}
    assert ("node", "a") in kinds
    assert ("edge", ("a", "a", "contains")) in kinds
    assert not any(c.node_id == "missing" for c in cites if c.kind == "node")


def test_fallback_citations_from_hits():
    artifact = {
        "nodes": [
            {"id": "hit1", "type": "concept", "metadata": {"name": "H"}},
            {"id": "other", "type": "file", "metadata": {}},
        ],
        "links": [
            {
                "source": "hit1",
                "target": "other",
                "type": "mentions",
                "provenance": "inferred",
            }
        ],
    }
    cites = fallback_citations(artifact, ["hit1"])
    assert any(c.kind == "node" and c.node_id == "hit1" for c in cites)


def test_generate_cited_answer_with_injectable_chat(tmp_path: Path):
    out = tmp_path / "sub.json"
    result = run_query(
        "How does authentication work?",
        FIXTURE,
        out,
        k=5,
        match_threshold=0.3,
        want_answer=False,
        use_embeddings=False,
    )
    art = json.loads(out.read_text(encoding="utf-8"))
    hit = result.hit_ids[0]

    def fake_chat(**_kwargs: object) -> str:
        return f"Authentication uses tokens. [node:{hit}] [node:not_real]"

    status, text, detail, citations = generate_cited_answer(
        question="How does authentication work?",
        artifact=art,
        hit_ids=result.hit_ids,
        model="fake",
        base_url="http://localhost:9",
        chat_fn=fake_chat,
        list_models_fn=lambda _url: ["fake"],
    )
    assert status == "ok"
    assert text
    assert detail is None
    assert any(c.kind == "node" and c.node_id == hit for c in citations)
    assert not any(c.node_id == "not_real" for c in citations if c.kind == "node")


def test_generate_cited_answer_fallback_sources(tmp_path: Path):
    out = tmp_path / "sub.json"
    result = run_query(
        "authentication",
        FIXTURE,
        out,
        k=3,
        match_threshold=0.3,
        want_answer=False,
        use_embeddings=False,
    )
    art = json.loads(out.read_text(encoding="utf-8"))

    def no_cites(**_kwargs: object) -> str:
        return "Something about auth without citations."

    status, text, _detail, citations = generate_cited_answer(
        question="authentication",
        artifact=art,
        hit_ids=result.hit_ids,
        model="fake",
        base_url="http://localhost:9",
        chat_fn=no_cites,
        list_models_fn=lambda _url: ["fake"],
    )
    assert status == "ok"
    assert citations
    assert "Sources:" in (text or "")
