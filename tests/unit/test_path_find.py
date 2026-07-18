from pathlib import Path

import networkx as nx
import pytest

from grapheinstein.core.graph import artifact_to_digraph, load_artifact
from grapheinstein.core.path import (
    PATH_ANSWER_KIND,
    EndpointUnresolvedError,
    NoPathError,
    PathTooLongError,
    find_path,
    find_weighted_path,
    path_answer_to_dict,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "path_graphs"


def test_simple_chain_path_answer_shape():
    result = find_path(
        "start-concept",
        "end-concept",
        FIXTURES / "simple_chain.json",
        want_llm_explain=False,
        use_embeddings=False,
    )
    d = path_answer_to_dict(result.answer)
    assert d["kind"] == PATH_ANSWER_KIND
    assert d["version"] == "1.0.0"
    assert d["nodes"][0] == d["start"]["node_id"]
    assert d["nodes"][-1] == d["end"]["node_id"]
    assert d["hop_count"] == len(d["steps"])
    assert d["hop_count"] >= 1
    for step in d["steps"]:
        assert step["type"]
        assert step["provenance"] in {"extracted", "inferred"}
        assert step["cost"] > 0
    assert d["explanation"]


def test_weighted_routes_prefer_extracted_mid():
    result = find_path(
        "A",
        "B",
        FIXTURES / "weighted_routes.json",
        want_llm_explain=False,
        use_embeddings=False,
    )
    assert "func:preferred-mid" in result.answer.nodes
    assert all(s.provenance == "extracted" for s in result.answer.steps)


def test_same_node_trivial_path():
    result = find_path(
        "start-concept",
        "start-concept",
        FIXTURES / "simple_chain.json",
        want_llm_explain=False,
        use_embeddings=False,
    )
    assert result.answer.hop_count == 0
    assert result.answer.steps == ()
    assert len(result.answer.nodes) == 1
    assert result.answer.total_cost == 0.0


def test_no_path_disconnected():
    with pytest.raises(NoPathError):
        find_path(
            "island-a",
            "island-b",
            FIXTURES / "disconnected.json",
            want_llm_explain=False,
            use_embeddings=False,
        )


def test_unresolved_endpoint():
    with pytest.raises(EndpointUnresolvedError) as exc:
        find_path(
            "zzzz-no-such-node",
            "end-concept",
            FIXTURES / "simple_chain.json",
            want_llm_explain=False,
            use_embeddings=False,
        )
    assert "start" in exc.value.failed


def test_max_hops_exceeded():
    artifact = load_artifact(FIXTURES / "simple_chain.json")
    graph = artifact_to_digraph(artifact)
    with pytest.raises(PathTooLongError):
        find_weighted_path(
            graph,
            "concept::start-concept",
            "concept::end-concept",
            max_hops=0,
        )


def test_find_weighted_path_direct(tmp_path: Path):
    g = nx.DiGraph()
    g.add_node("a")
    g.add_node("b")
    g.add_edge("a", "b", type="calls", provenance="extracted", confidence=0.9)
    nodes, steps, total = find_weighted_path(g, "a", "b")
    assert nodes == ["a", "b"]
    assert len(steps) == 1
    assert total > 0
