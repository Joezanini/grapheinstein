from pathlib import Path

import pytest

from grapheinstein.api import IndexResult, index, query
from grapheinstein.core.query import NoEvidenceError

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "config_cache"
AUTH = Path(__file__).resolve().parents[1] / "fixtures" / "query_graphs" / "auth_chunks.json"
NOISE = Path(__file__).resolve().parents[1] / "fixtures" / "query_graphs" / "noise_sparse.json"


def test_index_signature_and_result_fields(tmp_path: Path):
    out = tmp_path / "graph.json"
    result = index(FIXTURE, output=out, include_docs=True)
    assert isinstance(result, IndexResult)
    assert result.output_path == out or result.output_path.exists()
    assert result.output_path.exists()
    assert result.stats is not None
    assert getattr(result.stats, "total_nodes", None) is not None or (
        isinstance(result.stats, dict) and "total_nodes" in result.stats
    )
    assert result.artifact is None


def test_index_include_artifact(tmp_path: Path):
    out = tmp_path / "g.json"
    result = index(FIXTURE, output=out, include_artifact=True)
    assert result.artifact is not None
    assert result.artifact["schema_version"] == "6.0.0"


def test_index_missing_path_raises(tmp_path: Path):
    missing = tmp_path / "no-such-project"
    with pytest.raises((FileNotFoundError, NotADirectoryError, OSError)):
        index(missing, output=tmp_path / "out.json")


def test_query_envelope_shape(tmp_path: Path):
    out = tmp_path / "sub.json"
    envelope = query(
        "How does authentication work?",
        input=AUTH,
        output=out,
        no_answer=True,
        match_threshold=0.3,
    )
    assert envelope["schema_version"] == "1.0.0"
    assert "answer" in envelope
    assert "hit_ids" in envelope
    assert envelope["answer"]["status"] in ("ok", "skipped", "failed")
    assert out.exists()


def test_query_missing_graph_raises(tmp_path: Path):
    with pytest.raises((FileNotFoundError, OSError)):
        query("x", input=tmp_path / "missing.json", output=tmp_path / "s.json", no_answer=True)


def test_query_no_evidence_raises(tmp_path: Path):
    with pytest.raises(NoEvidenceError):
        query(
            "zzzx_not_a_real_topic_qqq_999",
            input=NOISE,
            output=tmp_path / "s.json",
            no_answer=True,
            match_threshold=0.9,
            k=5,
        )
