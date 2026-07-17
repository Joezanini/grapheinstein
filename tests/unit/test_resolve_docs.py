from pathlib import Path

from grapheinstein.core.graph import add_node, new_inventory_graph
from grapheinstein.core.parsers.docs import extract_docs_structure
from grapheinstein.core.parsers.resolve_docs import resolve_and_emit_docs

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "docs_pdf_project"


def test_resolve_readme_mention(tmp_path: Path):
    graph = new_inventory_graph(FIXTURE)
    add_node(graph, "docs/guide.md", "file")
    add_node(graph, "README.md", "file")
    headings, links = extract_docs_structure(FIXTURE / "docs" / "guide.md")
    resolve_and_emit_docs(
        graph,
        file_id="docs/guide.md",
        headings=headings,
        links=links,
        project_root=FIXTURE,
    )
    mentions = [
        (u, v)
        for u, v, d in graph.edges(data=True)
        if d.get("type") == "mentions"
    ]
    assert any(v == "README.md" for _, v in mentions)
    section_ofs = [d for _, _, d in graph.edges(data=True) if d.get("type") == "section_of"]
    assert len(section_ofs) == 3


def test_unresolved_link_omitted(tmp_path: Path):
    graph = new_inventory_graph(tmp_path)
    add_node(graph, "docs/a.md", "file")
    from grapheinstein.core.parsers.docs import HeadingFact, LinkFact

    resolve_and_emit_docs(
        graph,
        file_id="docs/a.md",
        headings=[HeadingFact(name="A", level=1, start_line=1, source="markdown")],
        links=[LinkFact(target="missing.md", start_line=2, section_index=0)],
        project_root=tmp_path,
    )
    assert not any(d.get("type") == "mentions" for _, _, d in graph.edges(data=True))
