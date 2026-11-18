"""Create operations: new documents, added paragraphs, and artifact registration."""

from __future__ import annotations

import os

from ..indexing import (
    append_unit,
    load_index,
    save_index,
    searchable_text,
    sync_document,
    _write_text,
)
from ..models import ARTIFACT_TYPES, Artifact, Node, Relation, decision, question
from ..utils import document_id, normalize_relpath, resolve_abs
from ._common import make_result
from .validate import validate_paragraph, validate_relation


def create_document(
    ws,
    relpath: str,
    title: str = "",
    purpose: str = "",
    content: str = "",
    dry_run: bool = False,
) -> dict:
    rel = normalize_relpath(relpath)
    abs_path = resolve_abs(ws.root, rel)
    if os.path.exists(abs_path):
        return make_result(
            "conflict", "create", rel, summary=f"document already exists: {rel}"
        )

    lines: list[str] = []
    if title or purpose:
        lines.append("---")
        if title:
            lines.append(f"title: {_yaml_str(title)}")
        if purpose:
            lines.append(f"purpose: {_yaml_str(purpose)}")
        lines.append("---")
        lines.append("")
    lines.append(f"# {title or rel}")
    lines.append("")
    if content:
        lines.append(content.strip())
        lines.append("")
    text = "\n".join(lines)

    if dry_run:
        return make_result(
            "completed",
            "create",
            rel,
            summary=f"would create {rel}",
        )

    os.makedirs(os.path.dirname(abs_path) or ws.root, exist_ok=True)
    _write_text(abs_path, text)
    sync = sync_document(ws, rel)
    return make_result(
        "completed",
        "create",
        rel,
        summary=f"Created {rel}",
        nodes_created=sync["nodes_created"] + [document_id(rel)],
    )


def add_paragraph(
    ws,
    relpath: str,
    content: str,
    heading: str = "",
    relationships: list | None = None,
    dry_run: bool = False,
) -> dict:
    rel = normalize_relpath(relpath)
    abs_path = resolve_abs(ws.root, rel)
    if not os.path.exists(abs_path):
        return make_result(
            "needs_input", "add", rel, summary=f"document does not exist: {rel}"
        )

    maximum = int(ws.config.authoring.get("maximum_paragraph_words", 120))
    warnings = validate_paragraph(content, maximum)
    if not content.strip():
        return make_result(
            "validation_failed",
            "add",
            rel,
            summary="content is empty",
            validation={"valid": False, "warnings": warnings, "errors": ["content is empty"]},
        )

    doc_id = document_id(rel)
    duplicates = [
        n
        for n in ws.graph.find_nodes({"kind": "paragraph", "document_id": doc_id})
        if n.content.strip() == content.strip()
    ]
    if duplicates:
        return make_result(
            "validation_failed",
            "add",
            rel,
            summary="content already exists in document",
            validation={
                "valid": False,
                "warnings": ["duplicate content"],
                "errors": [f"duplicate paragraph content matches {duplicates[0].id}"],
            },
        )

    if dry_run:
        return make_result(
            "completed",
            "add",
            rel,
            summary=f"would add paragraph to {rel}",
            validation={"valid": True, "warnings": warnings, "errors": []},
        )

    body = f"## {heading}\n\n{content}" if heading else content
    append_unit(ws, rel, body)
    sync = sync_document(ws, rel)

    created = sync["nodes_created"]
    if not created:
        return make_result(
            "validation_failed",
            "add",
            rel,
            summary="no new node created (possible duplicate content)",
            validation={
                "valid": False,
                "warnings": ["content may duplicate an existing paragraph"],
                "errors": ["no new node created"],
            },
        )

    new_nid = created[-1]
    relations_created = []
    for spec in relationships or []:
        target = spec.get("target") or spec.get("target_id")
        rtype = spec.get("type") or spec.get("relationship") or "references"
        relation = Relation(
            source_id=new_nid,
            target_id=target or "",
            type=rtype,
            description=spec.get("description", ""),
        )
        if validate_relation(relation, ws.graph):
            continue
        ws.graph.create_relation(relation)
        relations_created.append(relation.id)

    impact = ws.graph.calculate_impact(
        new_nid, depth=int(ws.config.retrieval.get("graph", {}).get("maximum_depth", 3))
    )
    return make_result(
        "completed",
        "add",
        rel,
        summary=f"Added paragraph to {rel}",
        nodes_created=[new_nid],
        relations_created=relations_created,
        impact=impact,
        validation={"valid": True, "warnings": warnings, "errors": []},
    )


def add_artifact(
    ws,
    relpath: str,
    artifact: dict,
    dry_run: bool = False,
) -> dict:
    rel = normalize_relpath(relpath)
    doc_id = document_id(rel)
    abs_path = resolve_abs(ws.root, rel)
    if not os.path.exists(abs_path):
        return make_result(
            "needs_input", "add_artifact", rel, summary=f"document does not exist: {rel}"
        )

    atype = artifact.get("type", "file")
    if atype not in ARTIFACT_TYPES:
        return make_result(
            "validation_failed",
            "add_artifact",
            rel,
            summary=f"unknown artifact type: {atype!r}",
            validation={"valid": False, "warnings": [], "errors": [f"unknown artifact type: {atype!r}"]},
        )

    nid = ws.allocate_node_id(atype)
    art = Artifact(
        id=nid,
        document_id=doc_id,
        type=atype,
        path=artifact.get("path", ""),
        description=artifact.get("description", ""),
        purpose=artifact.get("purpose", ""),
        content=artifact.get("content", ""),
        metadata={**artifact.get("metadata", {}), "origin": "authoring"},
    )
    node = Node.from_dict(art.to_node_dict())

    if dry_run:
        return make_result(
            "completed",
            "add_artifact",
            rel,
            summary=f"would register {atype} artifact in {rel}",
            nodes_created=[nid],
        )

    ws.graph.create_node(node)
    ws.graph.create_relation(Relation(source_id=doc_id, target_id=nid, type="contains"))

    idx = load_index(ws)
    idx.add(nid, searchable_text(node), kind=atype, document_id=doc_id)
    save_index(ws, idx)

    impact = ws.graph.calculate_impact(nid, depth=3)
    return make_result(
        "completed",
        "add_artifact",
        rel,
        summary=f"Registered {atype} artifact in {rel}",
        nodes_created=[nid],
        impact=impact,
    )


def _yaml_str(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def add_question(
    ws,
    relpath: str,
    question_text: str,
    reason: str = "",
    related_nodes: list | None = None,
    dry_run: bool = False,
) -> dict:
    rel = normalize_relpath(relpath)
    doc_id = document_id(rel)
    if not os.path.exists(resolve_abs(ws.root, rel)):
        return make_result(
            "needs_input", "add_question", rel, summary=f"document does not exist: {rel}"
        )
    if not question_text.strip():
        return make_result(
            "validation_failed",
            "add_question",
            rel,
            summary="question text is empty",
            validation={"valid": False, "warnings": [], "errors": ["question text is empty"]},
        )

    nid = ws.allocate_node_id("question")
    node = question(nid, doc_id, question_text, reason=reason, related_nodes=related_nodes)

    if dry_run:
        return make_result(
            "completed", "add_question", rel, summary=f"would register question {nid}",
            nodes_created=[nid],
        )

    ws.graph.create_node(node)
    ws.graph.create_relation(Relation(source_id=doc_id, target_id=nid, type="contains"))
    for target in related_nodes or []:
        if target and ws.graph.get_node(target):
            ws.graph.create_relation(
                Relation(source_id=nid, target_id=target, type="references")
            )

    idx = load_index(ws)
    idx.add(nid, searchable_text(node), kind="question", document_id=doc_id)
    save_index(ws, idx)

    return make_result(
        "completed",
        "add_question",
        rel,
        summary=f"Registered question {nid}",
        nodes_created=[nid],
    )


def add_decision(
    ws,
    relpath: str,
    decision_text: str,
    rationale: str = "",
    source: str = "",
    dry_run: bool = False,
) -> dict:
    rel = normalize_relpath(relpath)
    doc_id = document_id(rel)
    if not os.path.exists(resolve_abs(ws.root, rel)):
        return make_result(
            "needs_input", "add_decision", rel, summary=f"document does not exist: {rel}"
        )
    if not decision_text.strip():
        return make_result(
            "validation_failed",
            "add_decision",
            rel,
            summary="decision text is empty",
            validation={"valid": False, "warnings": [], "errors": ["decision text is empty"]},
        )

    nid = ws.allocate_node_id("decision")
    node = decision(nid, doc_id, decision_text, rationale=rationale, source=source)

    if dry_run:
        return make_result(
            "completed", "add_decision", rel, summary=f"would register decision {nid}",
            nodes_created=[nid],
        )

    ws.graph.create_node(node)
    ws.graph.create_relation(Relation(source_id=doc_id, target_id=nid, type="contains"))

    idx = load_index(ws)
    idx.add(nid, searchable_text(node), kind="decision", document_id=doc_id)
    save_index(ws, idx)

    return make_result(
        "completed",
        "add_decision",
        rel,
        summary=f"Registered decision {nid}",
        nodes_created=[nid],
    )
