from pathlib import Path

from grapheinstein.core.index import build_inventory_graph, discover_paths


def test_symlink_recorded_as_file_not_followed(tmp_path: Path):
    project = tmp_path / "proj"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("nope", encoding="utf-8")
    nested = outside / "nested"
    nested.mkdir()
    (nested / "deep.py").write_text("x=1\n", encoding="utf-8")
    (project / "README.md").write_text("ok\n", encoding="utf-8")
    link = project / "link_out"
    link.symlink_to(outside, target_is_directory=True)

    paths = {rel: (typ, meta) for rel, typ, meta in discover_paths(project)}
    assert "link_out" in paths
    assert paths["link_out"][0] == "file"
    assert paths["link_out"][1].get("symlink") is True
    assert "link_out/secret.txt" not in paths
    assert "link_out/nested" not in paths
    assert "link_out/nested/deep.py" not in paths

    graph = build_inventory_graph(project)
    assert graph.nodes["link_out"]["type"] == "file"
    assert graph.nodes["link_out"]["metadata"].get("symlink") is True
    assert "link_out/secret.txt" not in graph
