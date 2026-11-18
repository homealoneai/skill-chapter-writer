"""Validation: deterministic graph-integrity and content checks."""

from __future__ import annotations

from ..content import check_length
from ..models import RELATIONSHIP_TYPES

# Relationship types that must not form cycles.
PROHIBITED_CYCLE_TYPES = {"depends_on", "implements", "supersedes", "derived_from", "contains"}


def validate_node(node) -> list[str]:
    return node.validate()


def validate_relation(relation, store=None) -> list[str]:
    errors = relation.validate()
    if store is not None and not errors:
        if not store.get_node(relation.source_id):
            errors.append(f"relation {relation.id}: missing source node {relation.source_id}")
        if not store.get_node(relation.target_id):
            errors.append(f"relation {relation.id}: missing target node {relation.target_id}")
    return errors


def validate_paragraph(text: str, maximum: int = 120) -> list[str]:
    warnings: list[str] = []
    if not text.strip():
        warnings.append("paragraph is empty")
        return warnings
    n, too_long = check_length(text, maximum)
    if too_long:
        warnings.append(f"paragraph is {n} words (maximum {maximum})")
    return warnings


def validate_graph(store, config=None) -> dict:
    """Return ``{"valid", "warnings", "errors"}`` for the whole graph."""
    errors: list[str] = []
    warnings: list[str] = []

    nodes = store.find_nodes()
    ids = [n.id for n in nodes]
    if len(ids) != len(set(ids)):
        errors.append("duplicate node ids detected")

    for rel in store.find_relations():
        if rel.type not in RELATIONSHIP_TYPES:
            errors.append(f"relation {rel.id}: unknown type {rel.type!r}")
        if not store.get_node(rel.source_id):
            errors.append(f"relation {rel.id}: missing source node {rel.source_id}")
        if not store.get_node(rel.target_id):
            errors.append(f"relation {rel.id}: missing target node {rel.target_id}")

    require = bool(config and config.authoring.get("require_relationships", False))
    if require:
        for node in nodes:
            if node.kind == "document":
                continue
            if not store.find_relations({"source_id": node.id}) and not store.find_relations(
                {"target_id": node.id}
            ):
                warnings.append(f"node {node.id} has no relationships")

    for cycle in detect_cycles(store, PROHIBITED_CYCLE_TYPES):
        errors.append("relationship cycle detected: " + " -> ".join(cycle))

    return {"valid": not errors, "warnings": warnings, "errors": errors}


def detect_cycles(store, rel_types: set[str]) -> list[list[str]]:
    """Detect cycles over the given relationship types (directed DFS)."""
    adj: dict[str, list[str]] = {}
    nodes: set[str] = set()
    for rel in store.find_relations():
        if rel.type in rel_types:
            adj.setdefault(rel.source_id, []).append(rel.target_id)
            nodes.add(rel.source_id)
            nodes.add(rel.target_id)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    stack: list[str] = []
    cycles: list[list[str]] = []

    def dfs(u: str) -> None:
        color[u] = GRAY
        stack.append(u)
        for v in adj.get(u, []):
            c = color.get(v, WHITE)
            if c == GRAY:
                idx = stack.index(v)
                cycles.append(stack[idx:] + [v])
            elif c == WHITE:
                dfs(v)
        stack.pop()
        color[u] = BLACK

    for n in sorted(nodes):
        if color.get(n, WHITE) == WHITE:
            dfs(n)
    return cycles
