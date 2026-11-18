"""Table artifact handling."""

from __future__ import annotations

from ..models import Artifact
from ..utils import content_hash
from .markdown import ParsedUnit


def table_artifact_from_unit(
    unit: ParsedUnit, document_id: str, node_id: str
) -> Artifact:
    """Build a table artifact from a parsed table unit, preserving its schema."""
    return Artifact(
        id=node_id,
        document_id=document_id,
        type="table",
        path="",
        description="",
        purpose="",
        content=unit.raw,
        content_hash=content_hash(unit.raw),
        metadata={"schema": extract_schema(unit.raw)},
    )


def extract_schema(raw: str) -> list[str]:
    """Return the header cell names of a Markdown table."""
    lines = [l for l in (raw or "").split("\n") if l.strip()]
    for line in lines:
        if _is_separator(line):
            continue
        return _cells(line)
    return []


def _is_separator(line: str) -> bool:
    body = line.strip().strip("|")
    return all(ch in " :-|" for ch in body) and "-" in body


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]
