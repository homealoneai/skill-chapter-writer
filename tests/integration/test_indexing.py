"""Integration tests for indexing and synchronization."""

import os
from pathlib import Path

from chapter_writer.utils import document_id


def test_index_creates_all_kinds(seeded_engine):
    kinds = {n.kind for n in seeded_engine.ws.graph.find_nodes()}
    assert {"document", "paragraph", "code", "diagram", "table", "image"} <= kinds


def test_every_node_references_document(seeded_engine):
    for n in seeded_engine.ws.graph.find_nodes():
        if n.kind == "document":
            continue
        assert n.document_id == "DOC:docs/architecture.md"


def test_stable_ids_on_reindex(seeded_engine):
    before = {n.id for n in seeded_engine.ws.graph.find_nodes()}
    res = seeded_engine.index()
    assert res["nodes_created"] == []
    after = {n.id for n in seeded_engine.ws.graph.find_nodes()}
    assert before == after


def test_external_modification_detected(seeded_engine, tmp_path):
    p = os.path.join(str(tmp_path), "docs", "architecture.md")
    with open(p, "a", encoding="utf-8") as fh:
        fh.write("\nA new external paragraph.\n")
    res = seeded_engine.index()
    assert res["nodes_created"]


def test_external_deletion_detected(seeded_engine, tmp_path):
    os.remove(os.path.join(str(tmp_path), "docs", "architecture.md"))
    seeded_engine.index()
    assert len(seeded_engine.ws.graph.find_nodes()) == 0


def test_fixture_file_index(engine, tmp_path):
    src = Path(__file__).parent.parent / "fixtures" / "sample.md"
    import shutil

    shutil.copy(str(src), str(tmp_path / "sample.md"))
    engine.index()
    assert engine.ws.graph.get_node("DOC:sample.md") is not None


def test_document_move_preserves_content_ids(seeded_engine, tmp_path):
    from chapter_writer.models import Operation

    before_ids = {n.id for n in seeded_engine.ws.graph.find_nodes() if n.kind != "document"}
    r = seeded_engine.run(
        Operation(
            operation="move",
            workspace=str(tmp_path),
            document="docs/architecture.md",
            options={"new_path": "specs/arch.md"},
        )
    )
    assert r["status"] == "completed"
    after_ids = {n.id for n in seeded_engine.ws.graph.find_nodes() if n.kind != "document"}
    assert before_ids == after_ids
    assert seeded_engine.ws.graph.get_node("DOC:specs/arch.md") is not None
