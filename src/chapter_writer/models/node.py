"""The generic graph node record and typed content-unit constructors.

Every graph node is stored uniformly (single node table) so that new node kinds
can be added without a database redesign. ``kind`` is the discriminator; per-kind
fields live in ``metadata``. The typed constructors below produce valid records.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..utils import content_hash, is_document_id, is_valid_node_id, now_iso

NODE_KINDS = {
    "document",
    "paragraph",
    "image",
    "diagram",
    "table",
    "code",
    "file",
    "question",
    "decision",
}

ARTIFACT_KINDS = {"image", "diagram", "table", "code", "file"}

VALID_STATUSES = {
    "active",
    "draft",
    "archived",
    "deprecated",
    "retired",
    "superseded",
    "open",
    "resolved",
    "closed",
}


@dataclass
class Node:
    """A single atomic content unit in the knowledge graph."""

    id: str
    kind: str = ""
    document_id: str = ""
    content: str = ""
    heading: str = ""
    position: int = 0
    content_hash: str = ""
    version: int = 1
    status: str = "active"
    metadata: dict = field(default_factory=dict)
    provenance: list = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = now_iso()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.content_hash and self.content and self.kind != "document":
            self.content_hash = content_hash(self.content)
        if not isinstance(self.metadata, dict):
            self.metadata = {}
        if not isinstance(self.provenance, list):
            self.provenance = []

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Node":
        known = set(cls.__dataclass_fields__)
        payload = {k: v for k, v in data.items() if k in known}
        return cls(**payload)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.id:
            errors.append("node.id is required")
        elif self.kind == "document":
            if not is_document_id(self.id):
                errors.append(f"document node id must be DOC:<path>: {self.id!r}")
        elif not is_valid_node_id(self.id):
            errors.append(f"invalid node id: {self.id!r}")

        if self.kind not in NODE_KINDS:
            errors.append(f"unknown node kind: {self.kind!r}")
        if self.status not in VALID_STATUSES:
            errors.append(f"unknown node status: {self.status!r}")
        if self.kind != "document" and not self.document_id:
            errors.append(f"node {self.id} is missing document_id")
        return errors


def paragraph(
    id: str,
    document_id: str,
    content: str,
    heading: str = "",
    position: int = 0,
    **kwargs,
) -> Node:
    """Build a paragraph node."""
    return Node(
        id=id,
        kind="paragraph",
        document_id=document_id,
        content=content,
        heading=heading,
        position=position,
        **kwargs,
    )


def question(
    id: str,
    document_id: str,
    question_text: str,
    reason: str = "",
    related_nodes: list | None = None,
    status: str = "open",
    **kwargs,
) -> Node:
    """Build a question node (unresolved information)."""
    return Node(
        id=id,
        kind="question",
        document_id=document_id,
        content=question_text,
        status=status,
        metadata={"reason": reason, "related_nodes": list(related_nodes or []), "origin": "authoring"},
        **kwargs,
    )


def decision(
    id: str,
    document_id: str,
    decision_text: str,
    rationale: str = "",
    source: str = "",
    **kwargs,
) -> Node:
    """Build a decision node (confirmed decision)."""
    return Node(
        id=id,
        kind="decision",
        document_id=document_id,
        content=decision_text,
        metadata={"rationale": rationale, "source": source, "origin": "authoring"},
        **kwargs,
    )
