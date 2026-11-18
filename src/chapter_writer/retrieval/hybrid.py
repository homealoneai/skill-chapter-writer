"""Hybrid retrieval: lexical + graph + document scope, with explanations."""

from __future__ import annotations

from .graph import graph_search
from .index import LexicalIndex
from .ranking import combine, normalize, rank
from .lexical import lexical_search

# Node-type weight multiplier applied during final ranking.
NODE_TYPE_WEIGHT = {
    "document": 0.3,
    "paragraph": 1.0,
    "decision": 0.9,
    "question": 0.8,
    "image": 0.7,
    "diagram": 0.7,
    "table": 0.7,
    "code": 0.7,
    "file": 0.6,
}

DEFAULT_WEIGHTS = {
    "lexical_weight": 0.45,
    "graph_weight": 0.35,
    "document_scope_weight": 0.20,
}


def hybrid_search(
    store,
    index: LexicalIndex,
    query: str,
    *,
    document: str | None = None,
    top_k: int = 10,
    weights: dict | None = None,
    kinds: set[str] | None = None,
    explicit_ids: list[str] | None = None,
    graph_depth: int = 1,
) -> list[dict]:
    """Combine lexical, graph, and document-scope signals into ranked results.

    Every result carries ``node_id``, ``score``, and ``retrieval_reasons`` (the
    union of the reasons contributed by each signal).
    """
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    explicit_ids = list(explicit_ids or [])
    reasons: dict[str, set[str]] = {}

    def note(node_id: str, reason: str) -> None:
        reasons.setdefault(node_id, set()).add(reason)

    # 1. lexical
    lex_results = lexical_search(index, query, top_k=max(top_k * 2, 10), kinds=kinds)
    lex_scores = {r["node_id"]: r["score"] for r in lex_results}
    for r in lex_results:
        note(r["node_id"], "lexical_match")

    # 2. graph: seed from explicit ids + top lexical hits
    seed_ids = list(explicit_ids)
    for r in lex_results[: top_k]:
        if r["node_id"] not in seed_ids:
            seed_ids.append(r["node_id"])
    graph_results = (
        graph_search(store, seed_ids, depth=graph_depth, kinds=kinds)
        if seed_ids
        else []
    )
    graph_scores = {r["node_id"]: r["score"] for r in graph_results}
    for r in graph_results:
        for reason in r["retrieval_reasons"]:
            note(r["node_id"], reason)
        note(r["node_id"], f"relationship:{r['relationship']}")

    # 3. document scope + explicit ids
    doc_scope: dict[str, float] = {}
    for nid in set(explicit_ids):
        note(nid, "explicit_id")
        doc_scope[nid] = 1.0
    if document:
        doc_nodes = store.find_nodes({"document_id": document})
        for node in doc_nodes:
            doc_scope.setdefault(node.id, 1.0)
            note(node.id, "same_document")
        # the document node itself
        from ..utils import document_id

        note(document_id(document), "same_document")
        doc_scope[document_id(document)] = 1.0

    # 4. combine
    combined = combine(
        [
            (normalize(lex_scores), weights["lexical_weight"]),
            (normalize(graph_scores), weights["graph_weight"]),
            (normalize(doc_scope), weights["document_scope_weight"]),
        ]
    )

    results = []
    for node_id, score in combined.items():
        node = store.get_node(node_id)
        kind = node.kind if node else ""
        type_weight = NODE_TYPE_WEIGHT.get(kind, 0.8)
        results.append(
            {
                "node_id": node_id,
                "score": round(score * type_weight, 6),
                "retrieval_reasons": sorted(reasons.get(node_id, set())),
            }
        )

    return rank(results, limit=top_k)
