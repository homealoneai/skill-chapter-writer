"""Ranking helpers for hybrid retrieval."""

from __future__ import annotations


def normalize(scores: dict[str, float]) -> dict[str, float]:
    """Min-max normalize a node_id → score map into [0, 1]."""
    if not scores:
        return {}
    values = list(scores.values())
    lo, hi = min(values), max(values)
    if hi == lo:
        return {k: (1.0 if v > 0 else 0.0) for k, v in scores.items()}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def combine(
    sources: list[tuple[dict[str, float], float]],
) -> dict[str, float]:
    """Weighted sum of multiple score maps (already normalized)."""
    combined: dict[str, float] = {}
    for scores, weight in sources:
        for node_id, score in scores.items():
            combined[node_id] = combined.get(node_id, 0.0) + weight * score
    return combined


def rank(results: list[dict], limit: int | None = None) -> list[dict]:
    """Sort results by score descending and optionally truncate."""
    results = sorted(results, key=lambda r: r.get("score", 0.0), reverse=True)
    return results[:limit] if limit else results
