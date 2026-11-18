"""Link operations: create and remove typed relationships."""

from __future__ import annotations

from ..models import Relation
from ._common import make_result
from .validate import validate_relation


def link_nodes(
    ws,
    source_id: str,
    target_id: str,
    rel_type: str,
    description: str = "",
    dry_run: bool = False,
) -> dict:
    relation = Relation(
        source_id=source_id, target_id=target_id, type=rel_type, description=description
    )
    errors = validate_relation(relation, ws.graph)
    if errors:
        return make_result(
            "validation_failed",
            "link",
            summary="invalid relationship",
            validation={"valid": False, "warnings": [], "errors": errors},
        )

    if dry_run:
        return make_result(
            "completed",
            "link",
            summary=f"would link {source_id} -{rel_type}-> {target_id}",
        )

    ws.graph.create_relation(relation)
    return make_result(
        "completed",
        "link",
        summary=f"Linked {source_id} -{rel_type}-> {target_id}",
        relations_created=[relation.id],
    )


def unlink(ws, relation_id: str, dry_run: bool = False) -> dict:
    existing = ws.graph.find_relations({"id": relation_id})
    if not existing:
        return make_result("error", "link", summary=f"relationship not found: {relation_id}")

    if dry_run:
        return make_result("completed", "link", summary=f"would remove {relation_id}")

    ws.graph.delete_relation(relation_id)
    return make_result(
        "completed", "link", summary=f"Removed relationship {relation_id}",
        relations_removed=[relation_id],
    )
