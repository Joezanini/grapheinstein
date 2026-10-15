"""Test indexing a subfolder of a monorepo."""
from pathlib import Path

from grapheinstein.api import index

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "monorepo_project"


def test_index_full_monorepo():
    """Index the full monorepo - should find all entities."""
    result = index(
        FIXTURE,
        output=FIXTURE / "full_graph.json",
        languages=["python"],
        include_artifact=True,
    )
    assert result.output_path.exists()
    artifact = result.artifact
    
    node_ids = [n["id"] for n in artifact["nodes"]]
    assert any("root.py" in n for n in node_ids)
    assert any("package_a/main.py" in n for n in node_ids)
    assert any("package_b/main.py" in n for n in node_ids)
    
    result.output_path.unlink()


def test_index_subfolder_only():
    """Index only a subfolder - should only find entities in that subfolder."""
    subfolder = FIXTURE / "packages" / "package_a"
    result = index(
        subfolder,
        output=FIXTURE / "subfolder_graph.json",
        languages=["python"],
        include_artifact=True,
    )
    assert result.output_path.exists()
    artifact = result.artifact
    
    node_ids = [n["id"] for n in artifact["nodes"]]
    assert any("main.py" in n for n in node_ids)
    assert not any("root.py" in n for n in node_ids)
    assert not any("package_b" in n for n in node_ids)
    
    result.output_path.unlink()
