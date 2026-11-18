"""Shared helpers for operation executors."""

from __future__ import annotations

from ..models import OperationResult


def make_result(
    status: str = "completed",
    operation: str = "",
    document: str = "",
    summary: str = "",
    nodes_created: list | None = None,
    nodes_modified: list | None = None,
    nodes_deleted: list | None = None,
    relations_created: list | None = None,
    relations_removed: list | None = None,
    impact: dict | None = None,
    questions: list | None = None,
    validation: dict | None = None,
) -> dict:
    """Build a structured OperationResult dict with sensible defaults."""
    return OperationResult(
        status=status,
        operation=operation,
        document=document,
        summary=summary,
        nodes_created=list(nodes_created or []),
        nodes_modified=list(nodes_modified or []),
        nodes_deleted=list(nodes_deleted or []),
        relations_created=list(relations_created or []),
        relations_removed=list(relations_removed or []),
        impact=impact
        or {"required_review": [], "recommended_review": [], "optional_review": []},
        questions=list(questions or []),
        validation=validation or {"valid": True, "warnings": [], "errors": []},
    ).to_dict()
