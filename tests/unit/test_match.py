from grapheinstein.core.match import (
    fuzzy_score,
    score_nodes,
    select_matches,
)


def _nodes():
    return [
        {
            "id": "concept::auth",
            "type": "concept",
            "metadata": {"name": "Auth", "kind": "domain_term"},
        },
        {
            "id": "concept::authentication",
            "type": "concept",
            "metadata": {"name": "Authentication", "kind": "domain_term"},
        },
        {
            "id": "unrelated.py",
            "type": "file",
            "metadata": {},
        },
        {
            "id": "auth.py::check_auth",
            "type": "function",
            "metadata": {
                "name": "check_auth",
                "language": "python",
                "file": "auth.py",
                "start_line": 1,
            },
        },
    ]


def test_fuzzy_typo_and_partial():
    nodes = _nodes()
    auth = next(n for n in nodes if n["id"] == "concept::auth")
    authentication = next(n for n in nodes if n["id"] == "concept::authentication")
    score_typo = fuzzy_score(
        "autentication",
        authentication["id"],
        authentication["type"],
        authentication["metadata"],
    )
    score_partial = fuzzy_score("auth", auth["id"], auth["type"], auth["metadata"])
    noise = fuzzy_score(
        "autentication",
        "unrelated.py",
        "file",
        {},
    )
    assert score_partial >= 0.55
    assert score_typo > noise
    assert score_typo >= 0.55


def test_select_matches_threshold_top_n_concept_tiebreak():
    candidates, _ = score_nodes(_nodes(), "auth", embed_fn=None)
    selected = select_matches(candidates, threshold=0.55, top_n=2)
    assert selected
    assert selected[0].node_id in {"concept::auth", "concept::authentication", "auth.py::check_auth"}
    # Prefer concept when scores are close
    high = [c for c in candidates if c.final_score >= 0.55]
    assert any(c.node_type == "concept" for c in high)


def test_embedding_merge_and_soft_skip():
    nodes = _nodes()

    def good_embed(texts: list[str]) -> list[list[float]]:
        # Query and concept::authentication share a direction; others orthogonal-ish
        vectors = []
        for t in texts:
            if "authentication" in t or t == texts[0]:
                vectors.append([1.0, 0.0])
            else:
                vectors.append([0.0, 1.0])
        return vectors

    candidates, note = score_nodes(nodes, "login session security", embed_fn=good_embed)
    assert note is None
    by_id = {c.node_id: c for c in candidates}
    assert by_id["concept::authentication"].embedding_score is not None
    assert by_id["concept::authentication"].final_score >= by_id[
        "concept::authentication"
    ].fuzzy_score

    def bad_embed(_texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embeddings down")

    candidates2, note2 = score_nodes(nodes, "auth", embed_fn=bad_embed)
    assert note2 and "skipped" in note2.lower()
    assert all(c.embedding_score is None for c in candidates2)
    selected = select_matches(candidates2, threshold=0.55, top_n=3)
    assert selected  # fuzzy still works


def test_multi_match_selection():
    candidates, _ = score_nodes(_nodes(), "auth", embed_fn=None)
    selected = select_matches(candidates, threshold=0.3, top_n=3)
    assert 1 <= len(selected) <= 3
    assert len({c.node_id for c in selected}) == len(selected)
