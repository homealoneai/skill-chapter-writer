"""Deterministic impact analysis.

Impact is computed purely from the graph, by relationship type and traversal
rules. The LLM may *explain* the semantic impact afterward but never selects the
initial impact set.
"""

from __future__ import annotations

REQUIRED_TYPES = {"depends_on", "implements", "contradicts"}
RECOMMENDED_TYPES = {"refines", "supports", "references", "derived_from", "contains"}
OPTIONAL_TYPES = {"supersedes", "illustrates"}

# Relationship types through which impact propagates transitively.
STRONG_TYPES = {"depends_on", "implements"}

_CATEGORY = {}
for _t in REQUIRED_TYPES:
    _CATEGORY[_t] = "required_review"
for _t in RECOMMENDED_TYPES:
    _CATEGORY[_t] = "recommended_review"
for _t in OPTIONAL_TYPES:
    _CATEGORY[_t] = "optional_review"


def impact_category(rel_type: str) -> str | None:
    """Return the impact category for a relationship type, or None."""
    return _CATEGORY.get(rel_type)


def compute_impact(store, node_id: str, depth: int = 3) -> dict:
    """Compute the nodes affected by a change to ``node_id``.

    Returns ``{"required_review": [ids], "recommended_review": [ids],
    "optional_review": [ids]}``. Traversal follows *incoming* edges (nodes that
    point at the changed node, i.e. its dependents). Only ``STRONG_TYPES`` edges
    propagate transitively; the ``depth`` parameter caps that propagation.
    """
    result = {"required_review": [], "recommended_review": [], "optional_review": []}
    if not node_id:
        return result

    seen = {node_id}
    frontier = [node_id]
    level = 0
    limit = max(1, int(depth or 1))

    while frontier and level < limit:
        next_frontier: list[str] = []
        for current in frontier:
            for neighbor, rel in store.get_neighbors(current, direction="in"):
                if neighbor.id in seen:
                    continue
                seen.add(neighbor.id)
                category = _CATEGORY.get(rel.type)
                if category:
                    result[category].append(neighbor.id)
                if rel.type in STRONG_TYPES:
                    next_frontier.append(neighbor.id)
        frontier = next_frontier
        level += 1

    for key in result:
        result[key] = _dedupe(result[key])
    return result


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out
