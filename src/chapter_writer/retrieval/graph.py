"""Deterministic graph retrieval (neighbor expansion and impact traversal)."""

from __future__ import annotations

# Relationship importance for graph ranking (deterministic, configurable).
REL_IMPORTANCE = {
    "depends_on": 1.0,
    "implements": 0.9,
    "contradicts": 0.9,
    "refines": 0.7,
    "supports": 0.6,
    "derived_from": 0.6,
    "supersedes": 0.5,
    "contains": 0.5,
    "references": 0.4,
    "illustrates": 0.4,
}


def expand_neighbors(
    store,
    seed_ids: list[str],
    depth: int = 1,
    rel_types: set[str] | None = None,
    direction: str = "both",
    kinds: set[str] | None = None,
    documents: set[str] | None = None,
) -> list[dict]:
    """BFS-expand from seed nodes, returning graph-scored results.

    Each result carries ``score`` (relationship importance discounted by depth),
    ``relationship`` (the connecting type), and ``depth``.
    """
    limit = max(1, int(depth or 1))
    frontier = list(seed_ids)
    seen: dict[str, dict] = {}
    level = 0

    while frontier and level < limit:
        next_frontier: list[str] = []
        for current in frontier:
            for neighbor, rel in store.get_neighbors(current, direction=direction, rel_types=rel_types):
                if neighbor.id in seen:
                    continue
                if kinds and neighbor.kind not in kinds:
                    continue
                if documents and neighbor.document_id not in documents:
                    continue
                importance = REL_IMPORTANCE.get(rel.type, 0.3)
                seen[neighbor.id] = {
                    "node_id": neighbor.id,
                    "score": importance / (1 + level),
                    "relationship": rel.type,
                    "depth": level + 1,
                }
                next_frontier.append(neighbor.id)
        frontier = next_frontier
        level += 1

    return list(seen.values())


def graph_search(
    store,
    seed_ids: list[str],
    depth: int = 1,
    rel_types: set[str] | None = None,
    direction: str = "both",
    kinds: set[str] | None = None,
    documents: set[str] | None = None,
) -> list[dict]:
    """Ranked graph results with retrieval reasons."""
    results = expand_neighbors(
        store,
        seed_ids,
        depth=depth,
        rel_types=rel_types,
        direction=direction,
        kinds=kinds,
        documents=documents,
    )
    out = []
    for r in results:
        reasons = ["direct_dependency" if r["depth"] == 1 else "graph_neighbor"]
        out.append(
            {
                "node_id": r["node_id"],
                "score": round(r["score"], 6),
                "retrieval_reasons": reasons,
                "relationship": r["relationship"],
                "depth": r["depth"],
            }
        )
    out.sort(key=lambda x: x["score"], reverse=True)
    return out
