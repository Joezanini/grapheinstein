import json
from pathlib import Path

import pytest

from grapheinstein.core.explain import undirected_neighborhood
from grapheinstein.core.graph import artifact_to_digraph
from grapheinstein.core.query import (
    NoEvidenceError,
    build_chunk_corpus,
    build_supporting_subgraph,
    run_query,
    select_chunk_hits,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "query_graphs"


def test_hybrid_expand_includes_neighbors(tmp_path: Path):
    src = FIXTURE_DIR / "auth_chunks.json"
    out = tmp_path / "sub.json"
    result = run_query(
        "How does authentication work?",
        src,
        out,
        k=5,
        hops=1,
        match_threshold=0.3,
        want_answer=False,
        use_embeddings=False,
    )
    art = json.loads(out.read_text(encoding="utf-8"))
    ids = {n["id"] for n in art["nodes"]}
    assert "docs/auth.md::media_text::0" in result.hit_ids or any(
        "authentication" in h.lower() or "auth" in h.lower() for h in result.hit_ids
    )
    # Traversal should pull related function when media chunk is a hit
    if "docs/auth.md::media_text::0" in ids:
        assert "auth.py::check_auth" in ids or "docs/auth.md" in ids
    assert art["graph"]["query_hops"] == 1
    assert all("type" in e and "provenance" in e for e in art["links"])


def test_hops_1_vs_2_node_counts(tmp_path: Path):
    src = FIXTURE_DIR / "auth_chunks.json"
    out1 = tmp_path / "h1.json"
    out2 = tmp_path / "h2.json"
    run_query(
        "authentication",
        src,
        out1,
        k=3,
        hops=1,
        match_threshold=0.3,
        want_answer=False,
        use_embeddings=False,
    )
    run_query(
        "authentication",
        src,
        out2,
        k=3,
        hops=2,
        match_threshold=0.3,
        want_answer=False,
        use_embeddings=False,
    )
    n1 = len(json.loads(out1.read_text())["nodes"])
    n2 = len(json.loads(out2.read_text())["nodes"])
    assert n2 >= n1


def test_node_cap_truncation():
    art = json.loads((FIXTURE_DIR / "auth_chunks.json").read_text(encoding="utf-8"))
    digraph = artifact_to_digraph(art)
    seeds = ["docs/auth.md::media_text::0"]
    node_ids, truncated = undirected_neighborhood(digraph, seeds, hops=2, node_cap=2)
    assert truncated is True
    assert len(node_ids) <= 2
    sub = build_supporting_subgraph(
        art,
        node_ids=node_ids,
        question="authentication",
        hit_ids=seeds,
        hit_scores={seeds[0]: 0.9},
        k=1,
        hops=2,
        truncated=True,
    )
    assert sub["graph"].get("query_truncated") is True


def test_no_evidence_raises(tmp_path: Path):
    with pytest.raises(NoEvidenceError):
        run_query(
            "zzzx_not_a_real_topic_qqq_999",
            FIXTURE_DIR / "noise_sparse.json",
            tmp_path / "out.json",
            k=5,
            match_threshold=0.9,
            want_answer=False,
            use_embeddings=False,
        )
    assert not (tmp_path / "out.json").exists()


def test_dir_nodes_still_produce_composed_corpus():
    corpus = build_chunk_corpus([{"id": "x", "type": "dir", "metadata": {}}])
    assert corpus
    assert corpus[0].source == "composed"


def test_primary_hits_capped_by_k():
    art = json.loads((FIXTURE_DIR / "auth_chunks.json").read_text(encoding="utf-8"))
    corpus = build_chunk_corpus(art["nodes"])
    hits, _ = select_chunk_hits(corpus, "auth", k=1, threshold=0.2)
    assert len(hits) <= 1
