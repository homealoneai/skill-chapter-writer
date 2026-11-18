"""Diagram artifact handling (Mermaid, PlantUML, SVG, PNG, ...)."""

from __future__ import annotations

from ..models import Artifact
from ..utils import content_hash
from .markdown import ParsedUnit, PLANTUML_LANGS


def diagram_artifact_from_unit(
    unit: ParsedUnit, document_id: str, node_id: str, path: str = ""
) -> Artifact:
    """Build a diagram artifact from a fenced Mermaid/PlantUML block.

    The editable structured representation (the diagram source) is preserved in
    ``content``; ``metadata.format`` records the source format. An optional
    ``path`` points at a rendered visual artifact (SVG/PNG).
    """
    lang = unit.lang.lower()
    fmt = "plantuml" if lang in PLANTUML_LANGS else "mermaid"
    return Artifact(
        id=node_id,
        document_id=document_id,
        type="diagram",
        path=path,
        description="",
        purpose="",
        content=unit.raw,
        content_hash=content_hash(unit.raw),
        metadata={"format": fmt, "language": unit.lang, "source_kind": "inline"},
    )


def diagram_artifact_from_file(
    document_id: str,
    node_id: str,
    path: str,
    description: str = "",
    purpose: str = "",
    content: str = "",
) -> Artifact:
    """Build a diagram artifact that references an external diagram file."""
    fmt = _format_from_path(path)
    return Artifact(
        id=node_id,
        document_id=document_id,
        type="diagram",
        path=path,
        description=description,
        purpose=purpose,
        content=content,
        content_hash=content_hash(content),
        metadata={"format": fmt, "source_kind": "file"},
    )


def _format_from_path(path: str) -> str:
    p = (path or "").lower()
    if p.endswith(".mmd") or p.endswith(".mermaid"):
        return "mermaid"
    if p.endswith(".puml") or p.endswith(".plantuml"):
        return "plantuml"
    if p.endswith(".svg"):
        return "svg"
    if p.endswith(".png"):
        return "png"
    return "unknown"
