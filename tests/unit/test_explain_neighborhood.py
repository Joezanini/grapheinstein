import json
from pathlib import Path

from grapheinstein.core.explain import (
    build_explanation_artifact,
    undirected_neighborhood,
)
from grapheinstein.core.graph import artifact_to_digraph, load_artifact

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "explain_graphs" / "auth_neighborhood.json"
)


def test_undirected_hops_1_vs_2():
    source = load_artifact(FIXTURE)
    graph = artifact_to_digraph(source)
    n1, trunc1 = undirected_neighborhood(graph, ["concept::auth"], hops=1, node_cap=500)
    n2, trunc2 = undirected_neighborhood(graph, ["concept::auth"], hops=2, node_cap=500)
    assert not trunc1 and not trunc2
    assert "concept::auth" in n1
    assert "auth.py::check_auth" in n1
    assert "auth.py" not in n1  # 2 hops from concept via function
    assert "auth.py" in n2
    assert len(n2) >= len(n1)


def test_isolated_seed_returns_only_seed():
    source = load_artifact(FIXTURE)
    graph = artifact_to_digraph(source)
    # Remove edges incident to unrelated.py mentally: it only has contains from .
    # Pick concept::auth after removing all edges — use a node with only root link:
    nodes, truncated = undirected_neighborhood(graph, ["unrelated.py"], hops=2, node_cap=500)
    assert "unrelated.py" in nodes
    assert "." in nodes  # parent via undirected contains
    assert not truncated


def test_node_cap_truncation_sets_flag():
    source = load_artifact(FIXTURE)
    graph = artifact_to_digraph(source)
    nodes, truncated = undirected_neighborhood(
        graph, ["concept::auth"], hops=2, node_cap=2
    )
    assert truncated
    assert "concept::auth" in nodes
    assert len(nodes) <= 2


def test_build_explanation_artifact_metadata(tmp_path: Path):
    source = load_artifact(FIXTURE)
    graph = artifact_to_digraph(source)
    node_ids, truncated = undirected_neighborhood(graph, ["concept::auth"], hops=2)
    artifact = build_explanation_artifact(
        source,
        node_ids=node_ids,
        concept="auth",
        match_ids=["concept::auth"],
        match_scores={"concept::auth": 1.0},
        hops=2,
        truncated=truncated,
    )
    assert artifact["schema_version"] == "6.0.0"
    assert artifact["graph"]["explained_concept"] == "auth"
    assert artifact["graph"]["explain_match_ids"] == ["concept::auth"]
    assert artifact["graph"]["explain_hops"] == 2
    assert "generated_at" in artifact["graph"]
    ids = {n["id"] for n in artifact["nodes"]}
    assert "concept::auth" in ids
    for link in artifact["links"]:
        assert link["source"] in ids and link["target"] in ids
        assert link["provenance"] in {"extracted", "inferred"}
    out = tmp_path / "sub.json"
    out.write_text(json.dumps(artifact), encoding="utf-8")
    reloaded = load_artifact(out)
    assert reloaded["graph"]["explain_match_ids"] == ["concept::auth"]
