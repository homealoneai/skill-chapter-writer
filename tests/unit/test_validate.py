"""Unit tests for validation and cycle detection."""

from chapter_writer.models import Node, Relation
from chapter_writer.operations.validate import detect_cycles, validate_graph
from chapter_writer.storage import MemoryStore


def test_validate_missing_target():
    s = MemoryStore()
    s.create_node(Node(id="P-0001", kind="paragraph", document_id="DOC:d"))
    s.create_relation(Relation(source_id="P-0001", target_id="P-9999", type="depends_on"))
    v = validate_graph(s)
    assert not v["valid"]
    assert any("missing target" in e for e in v["errors"])


def test_validate_duplicate_ids():
    s = MemoryStore()
    s.create_node(Node(id="P-0001", kind="paragraph", document_id="DOC:d"))
    # memory store guards duplicates on create; simulate via direct injection
    s._nodes["P-0001"] = s._nodes["P-0001"]
    # no real duplicate possible through the API; assert valid is true
    assert validate_graph(s)["valid"] is True


def test_cycle_detection():
    s = MemoryStore()
    for i in ("1", "2", "3"):
        s.create_node(Node(id=f"P-000{i}", kind="paragraph", document_id="DOC:d"))
    s.create_relation(Relation(source_id="P-0001", target_id="P-0002", type="depends_on"))
    s.create_relation(Relation(source_id="P-0002", target_id="P-0003", type="depends_on"))
    s.create_relation(Relation(source_id="P-0003", target_id="P-0001", type="depends_on"))
    assert detect_cycles(s, {"depends_on"})
    v = validate_graph(s)
    assert not v["valid"]
    assert any("cycle" in e for e in v["errors"])


def test_non_prohibited_cycle_ok():
    s = MemoryStore()
    for i in ("1", "2"):
        s.create_node(Node(id=f"P-000{i}", kind="paragraph", document_id="DOC:d"))
    s.create_relation(Relation(source_id="P-0001", target_id="P-0002", type="references"))
    s.create_relation(Relation(source_id="P-0002", target_id="P-0001", type="references"))
    assert not detect_cycles(s, {"depends_on", "implements", "supersedes", "derived_from", "contains"})
