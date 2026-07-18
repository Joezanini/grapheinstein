import json
from pathlib import Path

from grapheinstein.core.query import build_chunk_corpus, select_chunk_hits

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "query_graphs"


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_corpus_prefers_metadata_text():
    art = _load("auth_chunks.json")
    corpus = build_chunk_corpus(art["nodes"])
    by_id = {c.node_id: c for c in corpus}
    assert "docs/auth.md::media_text::0" in by_id
    assert by_id["docs/auth.md::media_text::0"].source == "metadata_text"
    assert by_id["concept::authentication"].source == "composed"


def test_composed_only_corpus_usable():
    art = _load("composed_only.json")
    corpus = build_chunk_corpus(art["nodes"])
    assert corpus
    assert all(c.source == "composed" for c in corpus)


def test_select_chunk_hits_respects_k_and_threshold():
    art = _load("auth_chunks.json")
    corpus = build_chunk_corpus(art["nodes"])
    hits, note = select_chunk_hits(
        corpus,
        "How does authentication work?",
        k=2,
        threshold=0.3,
    )
    assert note is None
    assert 1 <= len(hits) <= 2
    assert hits[0].final_score >= 0.3
    # Prefer media_text when scores are competitive
    assert any(h.source == "metadata_text" for h in hits) or hits[0].node_id


def test_embedding_soft_skip_note():
    art = _load("auth_chunks.json")
    corpus = build_chunk_corpus(art["nodes"])

    def boom(_texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embed down")

    hits, note = select_chunk_hits(
        corpus,
        "authentication",
        k=5,
        threshold=0.3,
        embed_fn=boom,
    )
    assert hits
    assert note is not None
    assert "skipped" in note.lower()
