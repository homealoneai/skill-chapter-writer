"""Integration tests for retrieval."""

from chapter_writer.indexing import load_index


def test_lexical_search_returns_reasons(seeded_engine):
    res = seeded_engine.search("API layer", top_k=5)
    assert res
    assert all("retrieval_reasons" in r for r in res)


def test_graph_neighbors_contains(seeded_engine):
    nbrs = seeded_engine.ws.graph.get_neighbors("DOC:docs/architecture.md", direction="out")
    assert any(rel.type == "contains" for _, rel in nbrs)


def test_context_bundle(seeded_engine):
    ctx = seeded_engine.context("layers", document="docs/architecture.md")
    assert ctx["document_purpose"] == "Describe the system architecture."
    assert ctx["results"]


def test_lexical_index_persists(seeded_engine):
    idx = load_index(seeded_engine.ws)
    assert len(idx) > 0


def test_search_document_title(seeded_engine):
    res = seeded_engine.search("architecture", top_k=10)
    ids = [r["node_id"] for r in res]
    assert "DOC:docs/architecture.md" in ids
