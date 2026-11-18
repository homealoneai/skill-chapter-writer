"""Update operations: modify node content and move/rename documents."""

from __future__ import annotations

import os

from ..indexing import load_index, replace_unit, save_index, sync_document
from ..utils import document_id, normalize_relpath, resolve_abs
from ._common import make_result
from .validate import validate_paragraph


def update_node(ws, relpath: str, node_id: str, content: str, dry_run: bool = False) -> dict:
    rel = normalize_relpath(relpath)
    doc_id = document_id(rel)
    node = ws.graph.get_node(node_id)
    if node is None:
        return make_result("error", "update", rel, summary=f"node not found: {node_id}")
    if node.document_id != doc_id:
        return make_result(
            "error",
            "update",
            rel,
            summary=f"node {node_id} does not belong to {rel}",
        )

    maximum = int(ws.config.authoring.get("maximum_paragraph_words", 120))
    warnings = validate_paragraph(content, maximum) if node.kind == "paragraph" else []

    if dry_run:
        return make_result(
            "completed",
            "update",
            rel,
            summary=f"would update {node_id}",
            nodes_modified=[node_id],
            validation={"valid": True, "warnings": warnings, "errors": []},
        )

    impact = ws.graph.calculate_impact(node_id, depth=3)
    ok = replace_unit(ws, rel, node_id, content)
    if not ok:
        return make_result(
            "needs_input",
            "update",
            rel,
            summary=f"could not locate {node_id} in file; run `chapter-writer index` first",
        )

    sync = sync_document(ws, rel)
    modified = [node_id] if node_id in sync["nodes_modified"] else []
    return make_result(
        "completed",
        "update",
        rel,
        summary=f"Updated {node_id} in {rel}",
        nodes_modified=modified,
        impact=impact,
        validation={"valid": True, "warnings": warnings, "errors": []},
    )


def move_document(ws, relpath: str, new_relpath: str, dry_run: bool = False) -> dict:
    rel = normalize_relpath(relpath)
    new_rel = normalize_relpath(new_relpath)
    src = resolve_abs(ws.root, rel)
    dst = resolve_abs(ws.root, new_rel)

    if not os.path.exists(src):
        return make_result("error", "move", rel, summary=f"document does not exist: {rel}")
    if os.path.exists(dst):
        return make_result(
            "conflict", "move", rel, summary=f"destination already exists: {new_rel}"
        )

    if dry_run:
        return make_result(
            "completed", "move", rel, summary=f"would move {rel} -> {new_rel}"
        )

    old_doc_id = document_id(rel)
    new_doc_id = document_id(new_rel)

    # keep content-node identities: re-point their document_id before re-sync
    for node in ws.graph.find_nodes({"document_id": old_doc_id}):
        node.document_id = new_doc_id
        ws.graph.update_node(node)

    # drop old document node and its contains links; sync will recreate them
    for rel_ in ws.graph.find_relations({"source_id": old_doc_id}):
        ws.graph.delete_relation(rel_.id)
    for rel_ in ws.graph.find_relations({"target_id": old_doc_id}):
        ws.graph.delete_relation(rel_.id)
    if ws.graph.get_node(old_doc_id):
        ws.graph.delete_node(old_doc_id)

    os.makedirs(os.path.dirname(dst) or ws.root, exist_ok=True)
    os.rename(src, dst)

    idx = load_index(ws)
    idx.remove(old_doc_id)
    save_index(ws, idx)

    sync = sync_document(ws, new_rel)
    return make_result(
        "completed",
        "move",
        new_rel,
        summary=f"Moved {rel} -> {new_rel}",
        nodes_created=sync["nodes_created"] + [new_doc_id],
        nodes_modified=sync["nodes_modified"],
    )
