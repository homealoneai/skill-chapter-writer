"""Code artifact handling."""

from __future__ import annotations

from ..models import Artifact
from ..utils import content_hash
from .markdown import ParsedUnit


def code_artifact_from_unit(
    unit: ParsedUnit, document_id: str, node_id: str
) -> Artifact:
    """Build a code artifact from a fenced code block, preserving formatting."""
    return Artifact(
        id=node_id,
        document_id=document_id,
        type="code",
        path="",
        description="",
        purpose="",
        content=unit.raw,
        content_hash=content_hash(unit.raw),
        metadata={"language": unit.lang or ""},
    )
