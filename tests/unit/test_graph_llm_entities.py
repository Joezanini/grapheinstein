from pathlib import Path

from grapheinstein.core.graph import (
    add_concept,
    add_depends_on_edge,
    add_implements_edge,
    add_mentions_concept_edge,
    add_node,
    concept_id,
    new_inventory_graph,
    slugify_concept,
    to_artifact_dict,
)


def test_slugify_and_concept_id():
    assert slugify_concept("Auth Middleware") == "auth-middleware"
    assert concept_id("auth-middleware") == "concept::auth-middleware"


def test_add_concept_reuses_slug(tmp_path: Path):
    g = new_inventory_graph(tmp_path)
    a = add_concept(g, name="Auth Middleware", kind="domain_term")
    b = add_concept(g, name="auth middleware", kind="domain_term")
    assert a == b == "concept::auth-middleware"
    assert g.nodes[a]["metadata"]["name"] == "Auth Middleware"


def test_enrichment_edges_require_confidence_evidence(tmp_path: Path):
    g = new_inventory_graph(tmp_path)
    add_node(g, "src/a.py", "file")
    add_node(
        g,
        "src/a.py::function::foo::1",
        "function",
        metadata={
            "name": "foo",
            "language": "python",
            "file": "src/a.py",
            "start_line": 1,
        },
    )
    cid = add_concept(g, name="Thing")
    cid2 = add_concept(g, name="Other")
    assert add_implements_edge(
        g,
        "src/a.py::function::foo::1",
        cid,
        confidence=0.9,
        evidence="foo implements Thing",
    )
    assert add_depends_on_edge(
        g, "src/a.py", cid, confidence=0.8, evidence="depends on Thing"
    )
    assert add_mentions_concept_edge(
        g, "src/a.py", cid2, confidence=0.7, evidence="mentions Other"
    )
    art = to_artifact_dict(g)
    impl = next(link for link in art["links"] if link["type"] == "implements")
    assert impl["provenance"] == "inferred"
    assert impl["confidence"] == 0.9
    assert "Thing" in impl["evidence"]
