from pathlib import Path

from typer.testing import CliRunner

from grapheinstein.cli import cli

runner = CliRunner()
SAMPLE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_project"
MERGE = Path(__file__).resolve().parents[1] / "fixtures" / "merge_graphs"


def test_index_complete_write(tmp_path: Path):
    out = tmp_path / "graph.json"
    result = runner.invoke(cli, ["index", str(SAMPLE), "--output", str(out)])
    assert result.exit_code == 0, result.output
    data = out.read_text(encoding="utf-8")
    assert '"schema_version": "6.0.0"' in data
    assert '"metadata"' in data
    assert "project_root" in data


def test_cli_merge_union_and_conflict(tmp_path: Path):
    out = tmp_path / "merged.json"
    ok = runner.invoke(
        cli,
        ["merge", str(MERGE / "a.json"), str(MERGE / "b.json"), "--output", str(out)],
    )
    assert ok.exit_code == 0, ok.output
    assert out.exists()

    bad_out = tmp_path / "nope.json"
    bad = runner.invoke(
        cli,
        [
            "merge",
            str(MERGE / "conflict_a.json"),
            str(MERGE / "conflict_b.json"),
            "--output",
            str(bad_out),
        ],
    )
    assert bad.exit_code != 0
    assert not bad_out.exists()


def test_cli_compress_and_versioned(tmp_path: Path):
    out = tmp_path / "graph.json"
    result = runner.invoke(
        cli,
        ["index", str(SAMPLE), "--output", str(out), "--compress", "--versioned"],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "graph.json.gz").exists()
    assert (tmp_path / "graph_v1.json.gz").exists()

    result2 = runner.invoke(
        cli,
        ["index", str(SAMPLE), "--output", str(out), "--compress", "--versioned"],
    )
    assert result2.exit_code == 0, result2.output
    assert (tmp_path / "graph_v2.json.gz").exists()


def test_cli_merge_mixed_gzip(tmp_path: Path):
    # compress a.json
    from grapheinstein.core.graph import load_artifact, write_artifact_dict

    a = load_artifact(MERGE / "a.json")
    a_gz = tmp_path / "a.json.gz"
    write_artifact_dict(a, a_gz, compress=True)
    out = tmp_path / "merged.json"
    result = runner.invoke(
        cli,
        ["merge", str(a_gz), str(MERGE / "b.json"), "--output", str(out), "--compress"],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "merged.json.gz").exists()
