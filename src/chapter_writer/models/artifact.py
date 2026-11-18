"""Artifact model: non-text content associated with a document."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..utils import now_iso

ARTIFACT_TYPES = {"image", "diagram", "table", "code", "file"}

VALID_STATUSES = {"active", "draft", "archived", "deprecated", "superseded"}


@dataclass
class Artifact:
    """A non-text content unit (image, diagram, table, code block, or file)."""

    id: str
    document_id: str
    type: str = "file"
    path: str = ""
    description: str = ""
    purpose: str = ""
    content: str = ""
    content_hash: str = ""
    version: int = 1
    status: str = "active"
    metadata: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = now_iso()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not isinstance(self.metadata, dict):
            self.metadata = {}

    def to_dict(self) -> dict:
        return asdict(self)

    def to_node_dict(self) -> dict:
        """Serialize as a generic ``Node`` record (kind = artifact type)."""
        return {
            "id": self.id,
            "kind": self.type,
            "document_id": self.document_id,
            "content": self.content,
            "heading": "",
            "position": 0,
            "content_hash": self.content_hash,
            "version": self.version,
            "status": self.status,
            "metadata": {
                "path": self.path,
                "description": self.description,
                "purpose": self.purpose,
                **self.metadata,
            },
            "provenance": [],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_node_dict(cls, data: dict) -> "Artifact":
        meta = dict(data.get("metadata") or {})
        return cls(
            id=data.get("id", ""),
            document_id=data.get("document_id", ""),
            type=data.get("kind", "file"),
            path=meta.pop("path", ""),
            description=meta.pop("description", ""),
            purpose=meta.pop("purpose", ""),
            content=data.get("content", ""),
            content_hash=data.get("content_hash", ""),
            version=int(data.get("version", 1)),
            status=data.get("status", "active"),
            metadata=meta,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.id:
            errors.append("artifact.id is required")
        if self.type not in ARTIFACT_TYPES:
            errors.append(f"unknown artifact type: {self.type!r}")
        if not self.document_id:
            errors.append(f"artifact {self.id} is missing document_id")
        if self.status not in VALID_STATUSES:
            errors.append(f"unknown artifact status: {self.status!r}")
        return errors
