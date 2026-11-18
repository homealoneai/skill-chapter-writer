"""Integration tests for authoring operations."""

from chapter_writer.models import Operation


def test_create_document(engine, tmp_path):
    r = engine.run(
        Operation(
            operation="create",
            workspace=str(tmp_path),
            document="docs/new.md",
            content="Initial content.",
            options={"title": "New", "purpose": "purpose text"},
        )
    )
    assert r["status"] == "completed"
    assert engine.ws.graph.get_node("DOC:docs/new.md") is not None


def test_add_paragraph(seeded_engine, tmp_path):
    r = seeded_engine.run(
        Operation(
            operation="add",
            workspace=str(tmp_path),
            document="docs/architecture.md",
            content="A brand new paragraph.",
        )
    )
    assert r["status"] == "completed"
    nid = r["nodes_created"][0]
    assert seeded_engine.ws.graph.get_node(nid).kind == "paragraph"
    assert any(
        rel.type == "contains" and rel.target_id == nid
        for rel in seeded_engine.ws.graph.find_relations({"type": "contains"})
    )


def test_add_duplicate_detected(seeded_engine, tmp_path):
    existing = [n for n in seeded_engine.ws.graph.find_nodes() if n.kind == "paragraph"][0]
    r = seeded_engine.run(
        Operation(
            operation="add",
            workspace=str(tmp_path),
            document="docs/architecture.md",
            content=existing.content,
        )
    )
    assert r["status"] == "validation_failed"


def test_update_preserves_id(seeded_engine, tmp_path):
    p = [n for n in seeded_engine.ws.graph.find_nodes() if n.kind == "paragraph"][0]
    r = seeded_engine.run(
        Operation(
            operation="update",
            workspace=str(tmp_path),
            document="docs/architecture.md",
            node_id=p.id,
            content="Updated content here.",
        )
    )
    assert r["status"] == "completed"
    node = seeded_engine.ws.graph.get_node(p.id)
    assert node is not None
    assert node.content == "Updated content here."
    assert node.version > p.version


def test_delete_node(seeded_engine, tmp_path):
    p = [n for n in seeded_engine.ws.graph.find_nodes() if n.kind == "paragraph"][0]
    r = seeded_engine.run(
        Operation(
            operation="delete",
            workspace=str(tmp_path),
            document="docs/architecture.md",
            node_id=p.id,
        )
    )
    assert r["status"] == "completed"
    assert seeded_engine.ws.graph.get_node(p.id) is None


def test_link_and_impact(seeded_engine, tmp_path):
    ps = [n for n in seeded_engine.ws.graph.find_nodes() if n.kind == "paragraph"]
    a, b = ps[0], ps[1]
    r = seeded_engine.run(
        Operation(
            operation="link",
            workspace=str(tmp_path),
            node_id=b.id,
            target_nodes=[a.id],
            options={"type": "depends_on"},
        )
    )
    assert r["status"] == "completed"
    impact = seeded_engine.impact(a.id)
    assert b.id in impact["required_review"]


def test_link_invalid_target(seeded_engine, tmp_path):
    r = seeded_engine.run(
        Operation(
            operation="link",
            workspace=str(tmp_path),
            node_id="P-0001",
            target_nodes=["P-9999"],
            options={"type": "depends_on"},
        )
    )
    assert r["status"] == "validation_failed"
