from grapheinstein.core.path import PathStep, format_deterministic_explanation


def test_deterministic_explanation_includes_edge_labels():
    steps = (
        PathStep(
            source="a",
            target="b",
            type="calls",
            provenance="extracted",
            confidence=0.9,
            cost=1.1,
        ),
        PathStep(
            source="b",
            target="c",
            type="depends_on",
            provenance="inferred",
            confidence=None,
            cost=2.0,
        ),
    )
    text = format_deterministic_explanation("start", "end", ["a", "b", "c"], steps)
    assert "calls" in text
    assert "extracted" in text
    assert "depends_on" in text
    assert "inferred" in text
    assert "start" in text and "end" in text


def test_trivial_same_node_explanation():
    text = format_deterministic_explanation("auth", "auth", ["concept::auth"], ())
    assert "same entity" in text
    assert "concept::auth" in text
