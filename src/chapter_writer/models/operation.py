"""Operation contract: structured input/output for every authoring action."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

OPERATIONS = {
    "create",
    "add",
    "update",
    "delete",
    "move",
    "link",
    "review",
    "add_artifact",
    "add_question",
    "add_decision",
}

RESULT_STATUSES = {"completed", "needs_input", "validation_failed", "conflict", "error"}


@dataclass
class Operation:
    """A structured operation request (harness-independent)."""

    operation: str
    workspace: str = ""
    document: str = ""
    content: str = ""
    target_nodes: list = field(default_factory=list)
    node_id: str = ""
    artifact: dict = field(default_factory=dict)
    relationships: list = field(default_factory=list)
    options: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.target_nodes, list):
            self.target_nodes = []
        if not isinstance(self.relationships, list):
            self.relationships = []
        if not isinstance(self.options, dict):
            self.options = {}

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Operation":
        known = set(cls.__dataclass_fields__)
        payload = {k: v for k, v in data.items() if k in known}
        return cls(**payload)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.operation not in OPERATIONS:
            errors.append(f"unknown operation: {self.operation!r}")
        if self.operation in {"add", "update", "create"} and not self.document:
            errors.append(f"operation {self.operation!r} requires a target document")
        return errors


@dataclass
class ValidationResult:
    valid: bool = True
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"valid": self.valid, "warnings": list(self.warnings), "errors": list(self.errors)}


@dataclass
class OperationResult:
    """A structured operation result."""

    status: str = "completed"
    operation: str = ""
    document: str = ""
    summary: str = ""
    nodes_created: list = field(default_factory=list)
    nodes_modified: list = field(default_factory=list)
    nodes_deleted: list = field(default_factory=list)
    relations_created: list = field(default_factory=list)
    relations_removed: list = field(default_factory=list)
    impact: dict = field(
        default_factory=lambda: {
            "required_review": [],
            "recommended_review": [],
            "optional_review": [],
        }
    )
    questions: list = field(default_factory=list)
    validation: dict = field(
        default_factory=lambda: {"valid": True, "warnings": [], "errors": []}
    )

    def to_dict(self) -> dict:
        d = asdict(self)
        # keep the spec's field order for readability
        return {
            "status": d["status"],
            "operation": d["operation"],
            "document": d["document"],
            "summary": d["summary"],
            "nodes_created": d["nodes_created"],
            "nodes_modified": d["nodes_modified"],
            "nodes_deleted": d["nodes_deleted"],
            "relations_created": d["relations_created"],
            "relations_removed": d["relations_removed"],
            "impact": d["impact"],
            "questions": d["questions"],
            "validation": d["validation"],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OperationResult":
        known = set(cls.__dataclass_fields__)
        payload = {k: v for k, v in data.items() if k in known}
        return cls(**payload)
