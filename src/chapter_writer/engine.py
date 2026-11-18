"""Engine facade: ties workspace, indexing, retrieval, and operations together.

The CLI is a thin wrapper over this class. Agents and subagents should call the
CLI (or these methods) rather than touching graph storage directly.
"""

from __future__ import annotations

from .indexing import index_workspace, load_index
from .models import Operation
from .operations import context as _context
from .operations import create as _create
from .operations import delete as _delete
from .operations import link as _link
from .operations import update as _update
from .operations.validate import validate_graph
from .retrieval import hybrid_search
from .storage import WorkspaceStore


class Engine:
    def __init__(self, root: str):
        self.root = root
        self.ws = WorkspaceStore.open(root)

    @classmethod
    def open(cls, root: str) -> "Engine":
        return cls(root)

    # -- workspace --------------------------------------------------------

    def init(self, name: str | None = None) -> dict:
        self.ws.init(name)
        return {"status": "completed", "workspace": self.ws.root, "config": self.ws.config.data}

    def status(self) -> dict:
        nodes = self.ws.graph.find_nodes()
        rels = self.ws.graph.find_relations()
        return {
            "workspace": self.ws.root,
            "name": self.ws.config.workspace_name,
            "provider": self.ws.config.graph_provider,
            "documents": len(self.ws.discover_documents()),
            "nodes": len(nodes),
            "relationships": len(rels),
        }

    # -- indexing ---------------------------------------------------------

    def index(self, write_markers: bool = True) -> dict:
        summary = index_workspace(self.ws, write_markers=write_markers)
        return {"status": "completed", **summary}

    # -- retrieval --------------------------------------------------------

    def search(self, query: str, document: str | None = None, top_k: int = 10) -> list[dict]:
        idx = load_index(self.ws)
        return hybrid_search(self.ws.graph, idx, query, document=document, top_k=top_k)

    def context(
        self,
        query: str,
        document: str | None = None,
        top_k: int = 10,
        explicit_ids: list[str] | None = None,
    ) -> dict:
        return _context.retrieve_context(
            self.ws, query, document=document, top_k=top_k, explicit_ids=explicit_ids
        )

    def impact(self, node_id: str, depth: int | None = None) -> dict:
        return self.ws.graph.calculate_impact(node_id, depth=depth or 3)

    # -- operations -------------------------------------------------------

    def run(self, op: Operation) -> dict:
        errors = op.validate()
        if errors:
            return {
                "status": "validation_failed",
                "operation": op.operation,
                "document": op.document,
                "summary": "invalid operation",
                "nodes_created": [],
                "nodes_modified": [],
                "nodes_deleted": [],
                "relations_created": [],
                "relations_removed": [],
                "impact": {"required_review": [], "recommended_review": [], "optional_review": []},
                "questions": [],
                "validation": {"valid": False, "warnings": [], "errors": errors},
            }

        dry_run = bool(op.options.get("dry_run", False))
        if op.operation == "create":
            return _create.create_document(
                self.ws, op.document, title=op.options.get("title", ""),
                purpose=op.options.get("purpose", ""), content=op.content, dry_run=dry_run,
            )
        if op.operation == "add":
            return _create.add_paragraph(
                self.ws, op.document, op.content,
                heading=op.options.get("heading", ""),
                relationships=op.relationships or op.options.get("relationships"),
                dry_run=dry_run,
            )
        if op.operation == "add_artifact":
            return _create.add_artifact(self.ws, op.document, op.artifact, dry_run=dry_run)
        if op.operation == "add_question":
            return _create.add_question(
                self.ws, op.document, op.content,
                reason=op.options.get("reason", ""),
                related_nodes=op.target_nodes, dry_run=dry_run,
            )
        if op.operation == "add_decision":
            return _create.add_decision(
                self.ws, op.document, op.content,
                rationale=op.options.get("rationale", ""),
                source=op.options.get("source", ""), dry_run=dry_run,
            )
        if op.operation == "update":
            return _update.update_node(self.ws, op.document, op.node_id, op.content, dry_run=dry_run)
        if op.operation == "delete":
            return _delete.delete_node(self.ws, op.document, op.node_id, dry_run=dry_run)
        if op.operation == "move":
            return _update.move_document(
                self.ws, op.document, op.options.get("new_path", ""), dry_run=dry_run
            )
        if op.operation == "link":
            rel_type = op.options.get("type", "references")
            if op.target_nodes:
                target = op.target_nodes[0]
            else:
                target = op.options.get("target", "")
            source = op.node_id or op.options.get("source", "")
            return _link.link_nodes(
                self.ws, source, target, rel_type,
                description=op.options.get("description", ""), dry_run=dry_run,
            )
        if op.operation == "review":
            node_id = op.node_id or (op.target_nodes[0] if op.target_nodes else "")
            return _context.review_node(self.ws, node_id, depth=op.options.get("depth"))
        return {
            "status": "error",
            "operation": op.operation,
            "summary": f"unsupported operation: {op.operation}",
        }

    # -- validation -------------------------------------------------------

    def validate(self) -> dict:
        return validate_graph(self.ws.graph, self.ws.config)
