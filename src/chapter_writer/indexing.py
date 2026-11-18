"""Document indexing and synchronization between Markdown files and the graph.

The Markdown file is the canonical *published* content; the graph is the
canonical store of relationships and indexing metadata. ``sync_document``
reconciles the two: it parses the file, matches units to existing nodes (by
marker, then content hash, then position), allocates stable ids for new units,
upserts the graph, maintains ``contains`` relationships, updates the lexical
index, and (optionally) rewrites invisible node markers.
"""

from __future__ import annotations

import os

from .content.diagram import diagram_artifact_from_unit
from .content.image import image_artifact_from_unit
from .content.markdown import (
    NODEABLE_KINDS,
    extract_node_markers,
    parse_markdown,
    render_with_markers,
    strip_markers,
)
from .content.table import table_artifact_from_unit
from .content.code import code_artifact_from_unit
from .models import Document, Node, Relation, paragraph
from .retrieval.index import LexicalIndex
from .utils import (
    content_hash,
    document_id,
    document_path_from_id,
    file_hash,
    normalize_relpath,
    now_iso,
    resolve_abs,
)


def load_index(ws) -> LexicalIndex:
    idx = LexicalIndex()
    idx.load(ws.index_dir)
    return idx


def save_index(ws, idx: LexicalIndex) -> None:
    idx.save(ws.index_dir)


def node_kind_for_unit(unit) -> str:
    return unit.kind


def build_unit_node(unit, document_id_: str, node_id: str) -> Node:
    """Build the graph Node for a parsed unit."""
    if unit.kind == "paragraph":
        return paragraph(
            node_id, document_id_, unit.text, heading=unit.heading, position=unit.position
        )
    if unit.kind == "image":
        return Node.from_dict(image_artifact_from_unit(unit, document_id_, node_id).to_node_dict())
    if unit.kind == "diagram":
        return Node.from_dict(diagram_artifact_from_unit(unit, document_id_, node_id).to_node_dict())
    if unit.kind == "table":
        return Node.from_dict(table_artifact_from_unit(unit, document_id_, node_id).to_node_dict())
    if unit.kind == "code":
        return Node.from_dict(code_artifact_from_unit(unit, document_id_, node_id).to_node_dict())
    raise ValueError(f"unit kind is not nodeable: {unit.kind!r}")


def unit_hash(unit) -> str:
    """Content hash that matches ``build_unit_node``'s node content hash."""
    if unit.kind == "paragraph":
        return content_hash(unit.text)
    if unit.kind == "image":
        return content_hash(unit.meta.get("src", "") or unit.meta.get("alt", ""))
    return content_hash(unit.raw)


def searchable_text(node: Node) -> str:
    """Build the searchable text indexed for a node."""
    parts = [node.id]
    if node.kind == "document":
        parts += [node.heading, node.content]
    else:
        parts += [node.content, node.heading]
    parts += [
        node.metadata.get("description", ""),
        node.metadata.get("purpose", ""),
        node.metadata.get("title", ""),
    ]
    return " ".join(p for p in parts if p)


def sync_document(ws, relpath: str, write_markers: bool = True) -> dict:
    """Reconcile one Markdown document with the graph and lexical index."""
    rel = normalize_relpath(relpath)
    abs_path = resolve_abs(ws.root, rel)
    doc_id = document_id(rel)

    if not os.path.exists(abs_path):
        return _remove_document(ws, rel, doc_id)

    text = _read_text(abs_path)
    parsed = parse_markdown(text)
    file_h = file_hash(abs_path)

    title = parsed.frontmatter.get("title") or parsed.title or ""
    purpose = (
        parsed.frontmatter.get("purpose")
        or parsed.frontmatter.get("description")
        or ""
    )

    # -- document node ----------------------------------------------------
    existing_doc = ws.graph.get_node(doc_id)
    now = now_iso()
    if existing_doc is None:
        doc_model = Document(path=rel, title=title, purpose=purpose, content_hash=file_h)
        ws.graph.create_node(Node.from_dict(doc_model.to_node_dict()))
    else:
        changed = (
            existing_doc.content_hash != file_h
            or existing_doc.metadata.get("title") != title
            or existing_doc.metadata.get("purpose") != purpose
        )
        version = existing_doc.version + 1 if changed else existing_doc.version
        doc_model = Document(
            path=rel,
            title=title,
            purpose=purpose,
            content_hash=file_h,
            version=version,
            status=existing_doc.status,
            created_at=existing_doc.created_at,
            updated_at=now,
        )
        ws.graph.update_node(Node.from_dict(doc_model.to_node_dict()))

    # -- content units ----------------------------------------------------
    nodeable = [u for u in parsed.units if u.kind in NODEABLE_KINDS]
    markers = extract_node_markers(text)
    existing = {
        n.id: n
        for n in ws.graph.find_nodes({"document_id": doc_id})
        if n.kind != "document"
    }

    unit_to_id: dict[int, str] = {}
    used: set[str] = set()

    # pass 1: explicit markers (strongest signal)
    for u in nodeable:
        mid = markers.get(u.position)
        if mid and mid in existing and mid not in used:
            unit_to_id[u.position] = mid
            used.add(mid)

    # pass 2: content-hash match
    for u in nodeable:
        if u.position in unit_to_id:
            continue
        h = unit_hash(u)
        for nid, node in existing.items():
            if nid not in used and node.kind == u.kind and node.content_hash == h:
                unit_to_id[u.position] = nid
                used.add(nid)
                break

    # pass 3: position match (same kind, in document order)
    unmatched = {nid: n for nid, n in existing.items() if nid not in used}
    pools: dict[str, list[Node]] = {}
    for node in unmatched.values():
        pools.setdefault(node.kind, []).append(node)
    for kind in pools:
        pools[kind].sort(key=lambda n: n.position)
    for u in nodeable:
        if u.position in unit_to_id:
            continue
        pool = pools.get(u.kind, [])
        if pool:
            unit_to_id[u.position] = pool.pop(0).id
            used.add(unit_to_id[u.position])

    # pass 4: allocate stable ids for genuinely new units
    for u in nodeable:
        if u.position not in unit_to_id:
            unit_to_id[u.position] = ws.allocate_node_id(u.kind)
            used.add(unit_to_id[u.position])

    # -- upsert nodes -----------------------------------------------------
    nodes_created: list[str] = []
    nodes_modified: list[str] = []
    for u in nodeable:
        nid = unit_to_id[u.position]
        node = build_unit_node(u, doc_id, nid)
        prev = existing.get(nid)
        if prev is None:
            ws.graph.create_node(node)
            nodes_created.append(nid)
        elif (
            prev.content_hash != node.content_hash
            or prev.content != node.content
            or prev.kind != node.kind
        ):
            node.version = prev.version + 1
            node.created_at = prev.created_at
            node.updated_at = now
            ws.graph.update_node(node)
            nodes_modified.append(nid)

    # -- contains relationships ------------------------------------------
    contains = {
        (r.source_id, r.target_id)
        for r in ws.graph.find_relations({"type": "contains"})
    }
    for u in nodeable:
        nid = unit_to_id[u.position]
        if (doc_id, nid) not in contains:
            ws.graph.create_relation(
                Relation(source_id=doc_id, target_id=nid, type="contains")
            )

    # -- retire nodes that no longer map to a unit ------------------------
    nodes_deleted: list[str] = []
    mapped = set(unit_to_id.values())
    for nid in existing:
        if nid not in mapped:
            ws.graph.delete_node(nid)
            nodes_deleted.append(nid)

    # -- lexical index ----------------------------------------------------
    idx = load_index(ws)
    for u in nodeable:
        nid = unit_to_id[u.position]
        node = ws.graph.get_node(nid)
        if node:
            idx.add(nid, searchable_text(node), kind=node.kind, document_id=doc_id)
    for nid in nodes_deleted:
        idx.remove(nid)
    doc_node = ws.graph.get_node(doc_id)
    if doc_node:
        idx.add(doc_id, searchable_text(doc_node), kind="document", document_id="")
    save_index(ws, idx)

    # -- rewrite markers --------------------------------------------------
    if write_markers:
        clean = strip_markers(text)
        final = render_with_markers(clean, doc_id, unit_to_id)
        if final != text:
            _write_text(abs_path, final)

    return {
        "document": rel,
        "doc_id": doc_id,
        "nodes_created": nodes_created,
        "nodes_modified": nodes_modified,
        "nodes_deleted": nodes_deleted,
    }


def index_workspace(ws, write_markers: bool = True) -> dict:
    """Sync every discovered Markdown document in the workspace."""
    summary = {
        "documents": [],
        "nodes_created": [],
        "nodes_modified": [],
        "nodes_deleted": [],
    }
    discovered = set(ws.discover_documents())
    for rel in sorted(discovered):
        try:
            result = sync_document(ws, rel, write_markers=write_markers)
        except Exception as exc:  # pragma: no cover - surface per-file errors
            summary["documents"].append({"document": rel, "error": str(exc)})
            continue
        summary["documents"].append(rel)
        summary["nodes_created"].extend(result["nodes_created"])
        summary["nodes_modified"].extend(result["nodes_modified"])
        summary["nodes_deleted"].extend(result["nodes_deleted"])

    # detect documents whose files were deleted externally
    for node in ws.graph.find_nodes({"kind": "document"}):
        path = document_path_from_id(node.id)
        if path and path not in discovered and not os.path.exists(resolve_abs(ws.root, path)):
            result = _remove_document(ws, path, node.id)
            summary["documents"].append({"document": path, "deleted": True})
            summary["nodes_deleted"].extend(result["nodes_deleted"])

    return summary


# -- file edit helpers (used by operations) --------------------------------


def _read_text(abs_path: str) -> str:
    with open(abs_path, "r", encoding="utf-8") as fh:
        return fh.read()


def _write_text(abs_path: str, text: str) -> None:
    with open(abs_path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _locate_unit(text: str, node_id: str):
    parsed = parse_markdown(text)
    markers = extract_node_markers(text)
    for u in parsed.units:
        if u.kind not in NODEABLE_KINDS:
            continue
        if markers.get(u.position) == node_id:
            return u
    return None


def append_unit(ws, relpath: str, text: str) -> None:
    abs_path = resolve_abs(ws.root, relpath)
    current = _read_text(abs_path).rstrip("\n")
    body = text.rstrip("\n")
    _write_text(abs_path, current + "\n\n" + body + "\n")


def replace_unit(ws, relpath: str, node_id: str, new_text: str) -> bool:
    """Replace a unit's text located by its node marker. Returns success."""
    abs_path = resolve_abs(ws.root, relpath)
    text = _read_text(abs_path)
    unit = _locate_unit(text, node_id)
    if unit is None:
        return False
    lines = text.split("\n")
    lines[unit.start_line - 1 : unit.end_line] = new_text.rstrip("\n").split("\n")
    _write_text(abs_path, "\n".join(lines))
    return True


def remove_unit(ws, relpath: str, node_id: str) -> bool:
    """Remove a unit and its node marker located by marker. Returns success."""
    abs_path = resolve_abs(ws.root, relpath)
    text = _read_text(abs_path)
    unit = _locate_unit(text, node_id)
    if unit is None:
        return False
    lines = text.split("\n")
    marker_idx = None
    for idx in range(unit.start_line - 1, len(lines)):
        if f"chapter-writer:node {node_id}" in lines[idx]:
            marker_idx = idx
            break
    if marker_idx is not None:
        del lines[marker_idx]
    del lines[unit.start_line - 1 : unit.end_line]
    _write_text(abs_path, "\n".join(lines))
    return True


def _remove_document(ws, relpath: str, doc_id: str) -> dict:
    idx = load_index(ws)
    removed: list[str] = []
    for node in ws.graph.find_nodes({"document_id": doc_id}):
        removed.append(node.id)
        idx.remove(node.id)
        ws.graph.delete_node(node.id)
    if ws.graph.get_node(doc_id):
        ws.graph.delete_node(doc_id)
        idx.remove(doc_id)
        removed.append(doc_id)
    save_index(ws, idx)
    return {
        "document": relpath,
        "doc_id": doc_id,
        "nodes_created": [],
        "nodes_modified": [],
        "nodes_deleted": removed,
    }
