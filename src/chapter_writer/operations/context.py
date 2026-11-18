"""Context retrieval and node review."""

from __future__ import annotations

from ..indexing import load_index
from ..models import Document, ARTIFACT_TYPES
from ..retrieval import hybrid_search
from ..utils import document_id


def retrieve_context(
    ws,
    query: str,
    document: str | None = None,
    top_k: int = 10,
    graph_depth: int | None = None,
    explicit_ids: list[str] | None = None,
    weights: dict | None = None,
) -> dict:
    """Retrieve a hybrid context bundle for a query, optionally scoped to a document."""
    store = ws.graph
    idx = load_index(ws)
    cfg = ws.config.retrieval
    if graph_depth is None:
        graph_depth = int(cfg.get("graph", {}).get("default_depth", 1))
    if weights is None:
        weights = cfg.get("hybrid") or None

    results = hybrid_search(
        store,
        idx,
        query,
        document=document,
        top_k=top_k,
        weights=weights,
        graph_depth=graph_depth,
        explicit_ids=explicit_ids,
    )

    doc = None
    if document:
        dn = store.get_node(document_id(document))
        if dn:
            doc = Document.from_node_dict(dn.to_dict())

    relevant = []
    decisions = []
    questions = []
    artifacts = []
    contradictions = []
    neighbor_ids: set[str] = set()

    for r in results:
        node = store.get_node(r["node_id"])
        if not node:
            continue
        relevant.append(
            {"node": node.to_dict(), "retrieval_reasons": r.get("retrieval_reasons", [])}
        )
        if node.kind == "question":
            questions.append(node.to_dict())
        if node.kind == "decision":
            decisions.append(node.to_dict())
        if node.kind in ARTIFACT_TYPES:
            artifacts.append(node.to_dict())
        for nb, rel in store.get_neighbors(node.id, direction="both"):
            neighbor_ids.add(nb.id)
            if rel.type == "contradicts":
                contradictions.append(
                    {
                        "source_id": rel.source_id,
                        "target_id": rel.target_id,
                        "description": rel.description,
                    }
                )

    neighbors = [
        store.get_node(i).to_dict() for i in sorted(neighbor_ids) if store.get_node(i)
    ]

    return {
        "query": query,
        "document": doc.to_dict() if doc else None,
        "document_purpose": doc.purpose if doc else "",
        "results": relevant,
        "neighbors": neighbors,
        "decisions": decisions,
        "questions": questions,
        "artifacts": artifacts,
        "contradictions": contradictions,
    }


def review_node(ws, node_id: str, depth: int | None = None) -> dict:
    """Return a node plus its deterministic impact set and neighbors."""
    store = ws.graph
    node = store.get_node(node_id)
    if not node:
        return {"status": "error", "summary": f"node not found: {node_id}"}
    impact = store.calculate_impact(node_id, depth=depth or 3)
    neighbors = [
        {"node_id": nb.id, "relationship": rel.type}
        for nb, rel in store.get_neighbors(node_id, direction="both")
    ]
    related_questions = [
        n.to_dict()
        for n in store.find_nodes({"kind": "question"})
        if node_id in (n.metadata.get("related_nodes") or [])
    ]
    return {
        "status": "completed",
        "node": node.to_dict(),
        "impact": impact,
        "neighbors": neighbors,
        "questions": related_questions,
    }
