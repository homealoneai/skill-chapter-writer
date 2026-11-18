"""Document model: a Markdown file's identity and metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ..utils import document_id, normalize_relpath, now_iso

VALID_STATUSES = {"active", "draft", "archived", "deprecated"}


@dataclass
class Document:
    """A Markdown file as a first-class node in the graph.

    ``id`` is always ``DOC:<normalized workspace-relative path>`` and is stable
    across renames/moves only when the move operation re-paths the node (see
    ``operations/move``); the path is otherwise the source of truth for identity.
    """

    path: str
    title: str = ""
    purpose: str = ""
    content_hash: str = ""
    version: int = 1
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        self.path = normalize_relpath(self.path)
        if not self.id:
            self.id = document_id(self.path)
        if not self.created_at:
            self.created_at = now_iso()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> dict:
        return asdict(self)

    def to_node_dict(self) -> dict:
        """Serialize as a generic ``Node`` record (kind='document')."""
        return {
            "id": self.id,
            "kind": "document",
            "document_id": "",
            "content": self.purpose,
            "heading": self.title,
            "position": 0,
            "content_hash": self.content_hash,
            "version": self.version,
            "status": self.status,
            "metadata": {
                "path": self.path,
                "title": self.title,
                "purpose": self.purpose,
            },
            "provenance": [],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_node_dict(cls, data: dict) -> "Document":
        meta = data.get("metadata") or {}
        return cls(
            path=meta.get("path", data.get("id", "").removeprefix("DOC:")),
            title=meta.get("title", data.get("heading", "")),
            purpose=meta.get("purpose", data.get("content", "")),
            content_hash=data.get("content_hash", ""),
            version=int(data.get("version", 1)),
            status=data.get("status", "active"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            id=data.get("id", ""),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.path:
            errors.append("document.path is required")
        if self.status not in VALID_STATUSES:
            errors.append(f"unknown document status: {self.status!r}")
        return errors
