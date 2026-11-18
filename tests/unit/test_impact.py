"""Unit tests for deterministic impact analysis."""

from chapter_writer.models import Node, Relation
from chapter_writer.operations.impact import compute_impact, impact_category
from chapter_writer.storage import MemoryStore


def _store():
    s = MemoryStore()
    for nid in ("P-0001", "P-0002", "P-0003", "IMG-0001"):
        kind = "image" if nid.startswith("IMG") else "paragraph"
        s.create_node(Node(id=nid, kind=kind, document_id="DOC:d"))
    return s


def test_impact_categories():
    s = _store()
    s.create_relation(Relation(source_id="P-0002", target_id="P-0001", type="depends_on"))
    s.create_relation(Relation(source_id="P-0003", target_id="P-0001", type="refines"))
    s.create_relation(Relation(source_id="IMG-0001", target_id="P-0001", type="illustrates"))
    r = compute_impact(s, "P-0001")
    assert "P-0002" in r["required_review"]
    assert "P-0003" in r["recommended_review"]
    assert "IMG-0001" in r["optional_review"]


def test_impact_transitive():
    s = _store()
    s.create_relation(Relation(source_id="P-0002", target_id="P-0001", type="depends_on"))
    s.create_relation(Relation(source_id="P-0003", target_id="P-0002", type="depends_on"))
    r = compute_impact(s, "P-0001", depth=3)
    assert "P-0003" in r["required_review"]


def test_impact_category_map():
    assert impact_category("depends_on") == "required_review"
    assert impact_category("refines") == "recommended_review"
    assert impact_category("illustrates") == "optional_review"
    assert impact_category("unknown") is None
