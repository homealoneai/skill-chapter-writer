"""Integration tests for workspace isolation and artifact handling."""

import pytest

from chapter_writer.engine import Engine
from chapter_writer.models import Node, Operation


def test_same_ids_different_workspaces(tmp_path):
    a = Engine.open(str(tmp_path / "a"))
    a.init()
    b = Engine.open(str(tmp_path / "b"))
    b.init()
    a.ws.graph.create_node(Node(id="P-0001", kind="paragraph", document_id="DOC:d"))
    b.ws.graph.create_node(Node(id="P-0001", kind="paragraph", document_id="DOC:d"))
    assert len(a.ws.graph.find_nodes()) == 1
    assert len(b.ws.graph.find_nodes()) == 1
    a.ws.graph.delete_node("P-0001")
    assert b.ws.graph.get_node("P-0001") is not None
    a.ws.close()
    b.ws.close()


def test_image_registered(seeded_engine):
    imgs = [n for n in seeded_engine.ws.graph.find_nodes() if n.kind == "image"]
    assert imgs
    assert imgs[0].metadata.get("path") == "assets/arch.png"


def test_diagram_registered(seeded_engine):
    diagrams = [n for n in seeded_engine.ws.graph.find_nodes() if n.kind == "diagram"]
    assert diagrams
    assert diagrams[0].metadata.get("format") == "mermaid"


def test_table_schema(seeded_engine):
    tables = [n for n in seeded_engine.ws.graph.find_nodes() if n.kind == "table"]
    assert tables
    assert "Layer" in tables[0].metadata.get("schema", [])


def test_code_formatting_preserved(seeded_engine):
    codes = [n for n in seeded_engine.ws.graph.find_nodes() if n.kind == "code"]
    assert codes
    assert codes[0].content.startswith("```python")


def test_add_artifact_operation(seeded_engine, tmp_path):
    r = seeded_engine.run(
        Operation(
            operation="add_artifact",
            workspace=str(tmp_path),
            document="docs/architecture.md",
            artifact={"type": "file", "path": "assets/data.json", "description": "sample data"},
        )
    )
    assert r["status"] == "completed"
    assert r["nodes_created"]
