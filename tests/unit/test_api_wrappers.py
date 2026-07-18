import json
from pathlib import Path

from grapheinstein.api import index
from grapheinstein.core.graph import SCHEMA_VERSION

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "config_cache"


def test_api_index_writes_schema_6(tmp_path: Path):
    out = tmp_path / "graph.json"
    result = index(FIXTURE, output=out, include_docs=True)
    data = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["schema_version"] == "6.0.0"
    assert isinstance(data.get("nodes"), list)
    assert result.stats.total_nodes >= 1
