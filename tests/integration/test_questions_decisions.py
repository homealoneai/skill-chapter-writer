"""Integration tests for question and decision registration."""

from chapter_writer.models import Operation


def test_add_question(seeded_engine, tmp_path):
    r = seeded_engine.run(
        Operation(
            operation="add_question",
            workspace=str(tmp_path),
            document="docs/architecture.md",
            content="Is three layers the right count?",
            options={"reason": "unclear requirement"},
            target_nodes=["P-0001"],
        )
    )
    assert r["status"] == "completed"
    nid = r["nodes_created"][0]
    node = seeded_engine.ws.graph.get_node(nid)
    assert node.kind == "question"
    assert node.status == "open"
    assert any(
        rel.type == "references" and rel.target_id == "P-0001"
        for rel in seeded_engine.ws.graph.find_relations({"type": "references"})
    )


def test_add_decision(seeded_engine, tmp_path):
    r = seeded_engine.run(
        Operation(
            operation="add_decision",
            workspace=str(tmp_path),
            document="docs/architecture.md",
            content="Use three layers.",
            options={"rationale": "simplicity", "source": "architecture review"},
        )
    )
    assert r["status"] == "completed"
    node = seeded_engine.ws.graph.get_node(r["nodes_created"][0])
    assert node.kind == "decision"
    assert node.metadata.get("rationale") == "simplicity"


def test_questions_surface_in_context(seeded_engine, tmp_path):
    seeded_engine.run(
        Operation(
            operation="add_question",
            workspace=str(tmp_path),
            document="docs/architecture.md",
            content="Is three layers the right count?",
            options={},
        )
    )
    ctx = seeded_engine.context("layers", document="docs/architecture.md")
    assert any(n["kind"] == "question" for n in ctx["questions"])
