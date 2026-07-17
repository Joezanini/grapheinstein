from pathlib import Path

from grapheinstein.core.graph import add_node, new_inventory_graph
from grapheinstein.core.parsers.llm_enrich import apply_enrichment_payload

CHUNK = "Auth Middleware validates JWT on each request. uses PyJWT library."


def test_drops_low_confidence(tmp_path: Path):
    g = new_inventory_graph(tmp_path)
    add_node(g, "docs/a.md", "file")
    payload = {
        "entities": [
            {
                "name": "Auth Middleware",
                "kind": "domain_term",
                "evidence": "Auth Middleware validates",
                "confidence": 0.4,
            }
        ],
        "relations": [],
    }
    added, dropped = apply_enrichment_payload(
        g, payload, file_id="docs/a.md", chunk=CHUNK, confidence_threshold=0.5
    )
    assert added == 0
    assert dropped >= 1
    assert "concept::auth-middleware" not in g


def test_keeps_confidence_at_threshold(tmp_path: Path):
    g = new_inventory_graph(tmp_path)
    add_node(g, "docs/a.md", "file")
    payload = {
        "entities": [
            {
                "name": "Auth Middleware",
                "kind": "domain_term",
                "evidence": "Auth Middleware validates",
                "confidence": 0.5,
            }
        ],
        "relations": [],
    }
    added, _dropped = apply_enrichment_payload(
        g, payload, file_id="docs/a.md", chunk=CHUNK, confidence_threshold=0.5
    )
    assert added >= 1
    assert "concept::auth-middleware" in g


def test_drops_ungrounded_evidence(tmp_path: Path):
    g = new_inventory_graph(tmp_path)
    add_node(g, "docs/a.md", "file")
    payload = {
        "entities": [
            {
                "name": "Auth Middleware",
                "kind": "domain_term",
                "evidence": "this evidence is not in the chunk at all",
                "confidence": 0.99,
            }
        ],
        "relations": [],
    }
    added, dropped = apply_enrichment_payload(
        g, payload, file_id="docs/a.md", chunk=CHUNK, confidence_threshold=0.5
    )
    assert added == 0
    assert dropped >= 1
