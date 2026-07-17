from pathlib import Path

from grapheinstein.core.graph import add_node, new_inventory_graph
from grapheinstein.core.parsers.llm_enrich import merge_llm_enrichment
from grapheinstein.core.parsers.llm_ollama import OllamaError


def test_partial_chunk_failure_continues(tmp_path: Path):
    (tmp_path / "a.py").write_text("print('a')\nAuth Middleware here\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("print('b')\nAuth Middleware here\n", encoding="utf-8")
    g = new_inventory_graph(tmp_path)
    add_node(g, "a.py", "file")
    add_node(g, "b.py", "file")

    calls = {"n": 0}

    def flaky_chat(**_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OllamaError("boom")
        return {
            "entities": [
                {
                    "name": "Auth Middleware",
                    "kind": "domain_term",
                    "evidence": "Auth Middleware here",
                    "confidence": 0.9,
                }
            ],
            "relations": [],
        }

    skips = merge_llm_enrichment(g, tmp_path, llm_chat=flaky_chat)
    assert skips >= 1
    assert "concept::auth-middleware" in g
