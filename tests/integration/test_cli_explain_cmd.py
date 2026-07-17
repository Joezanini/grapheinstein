import json
from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli
from grapheinstein.core.graph import load_artifact, write_artifact_dict

runner = CliRunner()
FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "explain_graphs" / "auth_neighborhood.json"
)


def test_explain_happy_path_no_summary(tmp_path: Path):
    out = tmp_path / "sub.json"
    result = runner.invoke(
        cli,
        [
            "explain",
            "auth",
            "--input",
            str(FIXTURE),
            "--output",
            str(out),
            "--no-summary",
        ],
    )
    assert result.exit_code == 0, result.output
    data = load_artifact(out)
    assert data["schema_version"] == "6.0.0"
    assert data["graph"]["explained_concept"] == "auth"
    assert data["graph"]["explain_match_ids"]
    assert data["graph"]["explain_hops"] == 2
    assert data["nodes"]
    assert all("metadata" in n for n in data["nodes"])
    assert all("provenance" in e for e in data["links"])


def test_explain_hops_1_vs_2(tmp_path: Path):
    h1 = tmp_path / "h1.json"
    h2 = tmp_path / "h2.json"
    r1 = runner.invoke(
        cli,
        [
            "explain",
            "auth",
            "-i",
            str(FIXTURE),
            "-o",
            str(h1),
            "--hops",
            "1",
            "--no-summary",
        ],
    )
    r2 = runner.invoke(
        cli,
        [
            "explain",
            "auth",
            "-i",
            str(FIXTURE),
            "-o",
            str(h2),
            "--hops",
            "2",
            "--no-summary",
        ],
    )
    assert r1.exit_code == 0, r1.output
    assert r2.exit_code == 0, r2.output
    n1 = len(load_artifact(h1)["nodes"])
    n2 = len(load_artifact(h2)["nodes"])
    assert n2 >= n1


def test_explain_approximate_phrase(tmp_path: Path):
    out = tmp_path / "fuzzy.json"
    result = runner.invoke(
        cli,
        [
            "explain",
            "authentication",
            "-i",
            str(FIXTURE),
            "-o",
            str(out),
            "--no-summary",
        ],
    )
    assert result.exit_code == 0, result.output
    ids = load_artifact(out)["graph"]["explain_match_ids"]
    assert any("auth" in i for i in ids)


def test_explain_multi_match_top_n(tmp_path: Path):
    out = tmp_path / "multi.json"
    result = runner.invoke(
        cli,
        [
            "explain",
            "auth",
            "-i",
            str(FIXTURE),
            "-o",
            str(out),
            "--top-n",
            "2",
            "--match-threshold",
            "0.3",
            "--no-summary",
        ],
    )
    assert result.exit_code == 0, result.output
    ids = load_artifact(out)["graph"]["explain_match_ids"]
    assert 1 <= len(ids) <= 2


def test_explain_gzip_input(tmp_path: Path):
    gz = tmp_path / "graph.json.gz"
    artifact = json.loads(FIXTURE.read_text(encoding="utf-8"))
    write_artifact_dict(artifact, gz, compress=True)
    assert gz.exists()
    out = tmp_path / "from_gz.json"
    result = runner.invoke(
        cli,
        ["explain", "auth", "-i", str(gz), "-o", str(out), "--no-summary"],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_explain_llm_unavailable_still_writes(tmp_path: Path, monkeypatch):
    out = tmp_path / "sum.json"
    # Force summary path: do not pass --no-summary; unreachable Ollama should skip
    result = runner.invoke(
        cli,
        [
            "explain",
            "auth",
            "-i",
            str(FIXTURE),
            "-o",
            str(out),
            "--llm-base-url",
            "http://127.0.0.1:1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert "skipped" in result.output.lower() or "Summary" in result.output
