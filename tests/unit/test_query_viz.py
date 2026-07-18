import json
from pathlib import Path

from grapheinstein.core.query import (
    format_visualization_summary,
    query_answer_to_dict,
    run_query,
)

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "query_graphs" / "auth_chunks.json"
)


def test_visualization_summary_counts(tmp_path: Path):
    out = tmp_path / "sub.json"
    result = run_query(
        "How does authentication work?",
        FIXTURE,
        out,
        k=5,
        hops=1,
        match_threshold=0.3,
        want_answer=False,
        use_embeddings=False,
    )
    art = json.loads(out.read_text(encoding="utf-8"))
    viz = format_visualization_summary(
        art,
        hit_ids=result.hit_ids,
        truncated=result.truncated,
        output_path=out,
    )
    assert viz.node_count == len(art["nodes"])
    assert viz.edge_count == len(art["links"])
    assert viz.node_type_counts
    assert "Supporting subgraph" in viz.format_human()
    assert art["graph"]["query_question"]
    assert art["graph"]["query_hit_ids"]
    assert art["graph"]["query_k"] == 5


def test_query_answer_envelope_shape(tmp_path: Path):
    out = tmp_path / "sub.json"
    result = run_query(
        "authentication",
        FIXTURE,
        out,
        k=3,
        match_threshold=0.3,
        want_answer=False,
        use_embeddings=False,
    )
    payload = query_answer_to_dict(result)
    assert payload["schema_version"] == "1.0.0"
    assert payload["answer"]["status"] == "skipped"
    assert payload["visualization"]["node_count"] == result.visualization.node_count
    assert payload["hit_ids"] == list(result.hit_ids)
