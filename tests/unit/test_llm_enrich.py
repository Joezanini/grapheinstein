from pathlib import Path

from grapheinstein.core.graph import add_node, new_inventory_graph
from grapheinstein.core.parsers.llm_enrich import (
    apply_enrichment_payload,
    evidence_grounded,
)

CHUNK = (
    "Auth Middleware validates JWT on each request.\n"
    "validate_token implements the Auth Middleware checks described above.\n"
    "import jwt  # PyJWT\n"
)


def test_evidence_grounded():
    assert evidence_grounded("Auth Middleware validates", CHUNK)
    assert evidence_grounded("  Auth   Middleware  validates  ", CHUNK)
    assert not evidence_grounded("completely fabricated evidence", CHUNK)


def test_apply_enrichment_payload_creates_concept_and_implements(tmp_path: Path):
    g = new_inventory_graph(tmp_path)
    add_node(g, "src/auth.py", "file")
    add_node(
        g,
        "src/auth.py::function::validate_token::5",
        "function",
        metadata={
            "name": "validate_token",
            "language": "python",
            "file": "src/auth.py",
            "start_line": 5,
        },
    )
    payload = {
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
                "confidence": 0.85,
            },
        ],
    }
    added, dropped = apply_enrichment_payload(
        g, payload, file_id="src/auth.py", chunk=CHUNK, confidence_threshold=0.5
    )
    assert added >= 2
    assert "concept::auth-middleware" in g
    assert any(
        d.get("type") == "implements" for _, _, d in g.edges(data=True)
    )
