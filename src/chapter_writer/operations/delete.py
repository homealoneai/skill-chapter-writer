"""Delete operation: remove a content node (and its relationships)."""

from __future__ import annotations

import os

from ..indexing import load_index, remove_unit, save_index, sync_document
from ..utils import document_id, normalize_relpath, resolve_abs
from ._common import make_result


def delete_node(ws, relpath: str, node_id: str, dry_run: bool = False) -> dict:
    rel = normalize_relpath(relpath)
    doc_id = document_id(rel)
    node = ws.graph.get_node(node_id)
    if node is None:
        return make_result("error", "delete", rel, summary=f"node not found: {node_id}")
    if node.document_id != doc_id:
        return make_result(
            "error", "delete", rel, summary=f"node {node_id} does not belong to {rel}"
        )

    if dry_run:
        return make_result(
            "completed",
            "delete",
            rel,
            summary=f"would delete {node_id}",
            nodes_deleted=[node_id],
        )

    impact = ws.graph.calculate_impact(node_id, depth=3)

    abs_path = resolve_abs(ws.root, rel)
    if os.path.exists(abs_path):
        ok = remove_unit(ws, rel, node_id)
        if ok:
            sync_document(ws, rel)
        else:
            ws.graph.delete_node(node_id)
            idx = load_index(ws)
            idx.remove(node_id)
            save_index(ws, idx)
    else:
        ws.graph.delete_node(node_id)

    return make_result(
        "completed",
        "delete",
        rel,
        summary=f"Deleted {node_id} from {rel}",
        nodes_deleted=[node_id],
        impact=impact,
    )
