"""Unit tests for data models."""

import pytest

from chapter_writer.models import (
    Artifact,
    Document,
    Node,
    Operation,
    OperationResult,
    Relation,
)
from chapter_writer.utils import document_id


def test_node_requires_document_id():
    node = Node(id="P-0001", kind="paragraph")
    assert any("document_id" in e for e in node.validate())


def test_node_rejects_invalid_id():
    node = Node(id="P-1", kind="paragraph", document_id="DOC:x")
    assert any("invalid node id" in e for e in node.validate())


def test_node_content_hash_auto():
    node = Node(id="P-0001", kind="paragraph", document_id="DOC:x", content="hello")
    assert node.content_hash


def test_document_id_derivation():
    doc = Document(path="docs/a.md")
    assert doc.id == "DOC:docs/a.md"
    assert document_id("docs/a.md") == "DOC:docs/a.md"


def test_relation_type_validation():
    rel = Relation(source_id="a", target_id="b", type="bogus")
    assert any("unknown relationship type" in e for e in rel.validate())


def test_relation_self_loop():
    rel = Relation(source_id="a", target_id="a", type="depends_on")
    assert any("self" in e for e in rel.validate())


def test_operation_requires_document_for_add():
    op = Operation(operation="add")
    assert any("document" in e for e in op.validate())


def test_artifact_type_validation():
    art = Artifact(id="IMG-0001", document_id="DOC:x", type="bogus")
    assert any("unknown artifact type" in e for e in art.validate())


def test_operation_result_roundtrip():
    r = OperationResult(status="completed", operation="add", document="d.md")
    d = r.to_dict()
    assert d["status"] == "completed"
    assert d["impact"] == {"required_review": [], "recommended_review": [], "optional_review": []}
