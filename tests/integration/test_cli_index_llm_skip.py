import json
from pathlib import Path

from grapheinstein.core.index import index_project

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "llm_project"


def test_missing_model_skips_enrichment(tmp_path: Path):
    out = tmp_path / "graph.json"
    written, stats = index_project(
        FIXTURE,
        out,
        languages=["python"],
        include_docs=True,
        enrich_llm=True,
        llm_model="definitely-missing-model-tag-xyz",
        list_models_fn=lambda _url: ["other:latest"],
    )
    data = json.loads(written.read_text(encoding="utf-8"))
    assert data["schema_version"] == "6.0.0"
    assert data["graph"]["enrich_llm"] is True
    assert data["graph"]["llm_model"] == "definitely-missing-model-tag-xyz"
    assert not any(n["type"] == "concept" for n in data["nodes"])
    # structural graph still present
    assert stats.file_count >= 1
    assert any(n["type"] == "function" for n in data["nodes"])
