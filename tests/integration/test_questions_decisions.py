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


def test_question_persists_after_reindex(seeded_engine, tmp_path):
    seeded_engine.run(
        Operation(
            operation="add_question",
            workspace=str(tmp_path),
            document="docs/architecture.md",
            content="Does the graph preserve questions?",
            options={},
        )
    )
    assert seeded_engine.ws.graph.get_node("Q-0001") is not None
    seeded_engine.index()
    assert seeded_engine.ws.graph.get_node("Q-0001") is not None


def test_decision_persists_after_reindex(seeded_engine, tmp_path):
    seeded_engine.run(
        Operation(
            operation="add_decision",
            workspace=str(tmp_path),
            document="docs/architecture.md",
            content="Graph-only nodes are preserved.",
            options={"rationale": "sync must not delete authoring nodes"},
        )
    )
    assert seeded_engine.ws.graph.get_node("DEC-0001") is not None
    seeded_engine.index()
    assert seeded_engine.ws.graph.get_node("DEC-0001") is not None


def test_registered_artifact_persists_after_reindex(seeded_engine, tmp_path):
    r = seeded_engine.run(
        Operation(
            operation="add_artifact",
            workspace=str(tmp_path),
            document="docs/architecture.md",
            artifact={"type": "code", "description": "graph-only code artifact"},
        )
    )
    nid = r["nodes_created"][0]
    seeded_engine.index()
    assert seeded_engine.ws.graph.get_node(nid) is not None


def test_removed_unit_is_still_retired(engine, make_doc, tmp_path):
    root = str(tmp_path)
    make_doc(root, "d.md", "# T\n\nFirst paragraph.\n\nSecond paragraph.\n")
    engine.index()
    assert len([n for n in engine.ws.graph.find_nodes() if n.kind == "paragraph"]) == 2
    # remove the second paragraph from the Markdown
    make_doc(root, "d.md", "# T\n\nFirst paragraph.\n")
    engine.index()
    assert len([n for n in engine.ws.graph.find_nodes() if n.kind == "paragraph"]) == 1
