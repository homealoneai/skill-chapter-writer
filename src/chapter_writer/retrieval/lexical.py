"""Lexical retrieval over the TF-IDF index."""

from __future__ import annotations

from .index import LexicalIndex


def lexical_search(
    index: LexicalIndex,
    query: str,
    top_k: int = 10,
    filters: dict | None = None,
    kinds: set[str] | None = None,
) -> list[dict]:
    """Return ranked lexical results with retrieval reasons."""
    hits = index.search(query, top_k=top_k, filters=filters, kinds=kinds)
    return [
        {
            "node_id": node_id,
            "score": round(score, 6),
            "retrieval_reasons": ["lexical_match"],
        }
        for node_id, score in hits
    ]
