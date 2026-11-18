"""Relationship model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from uuid import uuid4

from ..utils import now_iso

RELATIONSHIP_TYPES = {
    "depends_on",
    "refines",
    "supports",
    "implements",
    "references",
    "contradicts",
    "supersedes",
    "derived_from",
    "illustrates",
    "contains",
}


@dataclass
class Relation:
    """A typed, directed relationship between two content nodes."""

    source_id: str
    target_id: str
    type: str
    description: str = ""
    created_at: str = ""
    created_by: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = now_iso()
        if not self.id:
            self.id = f"R-{uuid4().hex[:12]}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Relation":
        known = set(cls.__dataclass_fields__)
        payload = {k: v for k, v in data.items() if k in known}
        return cls(**payload)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.type not in RELATIONSHIP_TYPES:
            errors.append(f"unknown relationship type: {self.type!r}")
        if not self.source_id:
            errors.append("relation.source_id is required")
        if not self.target_id:
            errors.append("relation.target_id is required")
        if self.source_id and self.source_id == self.target_id:
            errors.append(f"self-relations are not allowed: {self.source_id!r}")
        return errors
