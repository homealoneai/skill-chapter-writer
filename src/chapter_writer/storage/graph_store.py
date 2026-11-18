"""Graph storage abstraction.

The storage layer is deliberately decoupled from the LLM and the skill
instructions: all graph operations go through :class:`GraphStore`. Two backends
are provided by default:

* :class:`~chapter_writer.storage.ladybug_store.LadybugStore` — the primary backend,
  backed by the embedded `Ladybug <https://ladybugdb.com>`_ graph database.
* :class:`~chapter_writer.storage.memory_store.MemoryStore` — a pure-Python in-memory
  fallback used when the native ``ladybug`` package is unavailable (CI, etc.).
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

from ..models import Node, Relation


def _json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value) -> object:
    if value is None or value == "":
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def node_to_row(node: Node) -> dict:
    """Serialize a Node to a flat storage record."""
    return {
        "id": node.id,
        "kind": node.kind,
        "document_id": node.document_id,
        "content": node.content,
        "heading": node.heading,
        "position": int(node.position or 0),
        "content_hash": node.content_hash,
        "version": int(node.version or 1),
        "status": node.status,
        "meta": _json_dumps(node.metadata or {}),
        "provenance": _json_dumps(node.provenance or []),
        "created_at": node.created_at,
        "updated_at": node.updated_at,
    }


def row_to_node(row: dict) -> Node:
    """Deserialize a flat storage record to a Node."""
    meta = _json_loads(row.get("meta"))
    prov = _json_loads(row.get("provenance"))
    return Node(
        id=row["id"],
        kind=row.get("kind", ""),
        document_id=row.get("document_id", ""),
        content=row.get("content", ""),
        heading=row.get("heading", ""),
        position=int(row.get("position", 0) or 0),
        content_hash=row.get("content_hash", ""),
        version=int(row.get("version", 1) or 1),
        status=row.get("status", "active"),
        metadata=meta if isinstance(meta, dict) else {},
        provenance=prov if isinstance(prov, list) else [],
        created_at=row.get("created_at", ""),
        updated_at=row.get("updated_at", ""),
    )


def relation_to_row(rel: Relation) -> dict:
    return {
        "id": rel.id,
        "source_id": rel.source_id,
        "target_id": rel.target_id,
        "type": rel.type,
        "description": rel.description,
        "created_at": rel.created_at,
        "created_by": rel.created_by,
    }


def row_to_relation(row: dict) -> Relation:
    return Relation(
        id=row.get("id", ""),
        source_id=row.get("source_id", ""),
        target_id=row.get("target_id", ""),
        type=row.get("type", ""),
        description=row.get("description", ""),
        created_at=row.get("created_at", ""),
        created_by=row.get("created_by", ""),
    )


class GraphStore(ABC):
    """Abstract interface for graph persistence."""

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()

    # -- lifecycle --------------------------------------------------------

    @abstractmethod
    def connect(self) -> "GraphStore":
        """Open the backend. Idempotent."""

    @abstractmethod
    def close(self) -> None:
        """Close the backend."""

    @abstractmethod
    def create_schema(self) -> None:
        """Create the node/relationship schema (idempotent for the backend)."""

    # -- nodes ------------------------------------------------------------

    @abstractmethod
    def create_node(self, node: Node) -> Node:
        """Insert a node; raise if the id already exists."""

    @abstractmethod
    def get_node(self, node_id: str) -> Node | None:
        """Return a node by id, or None."""

    @abstractmethod
    def update_node(self, node: Node) -> Node:
        """Replace an existing node's properties, preserving the id."""

    @abstractmethod
    def delete_node(self, node_id: str) -> None:
        """Delete a node and its incident relationships."""

    @abstractmethod
    def find_nodes(self, filters: dict | None = None) -> list[Node]:
        """Return nodes matching exact equality filters on flat columns."""

    def node_exists(self, node_id: str) -> bool:
        return self.get_node(node_id) is not None

    def all_ids(self, kind: str | None = None) -> list[str]:
        nodes = self.find_nodes({"kind": kind} if kind else None)
        return [n.id for n in nodes]

    # -- relationships ----------------------------------------------------

    @abstractmethod
    def create_relation(self, relation: Relation) -> Relation:
        """Insert a typed relationship."""

    @abstractmethod
    def delete_relation(self, relation_id: str) -> None:
        """Delete a relationship by id."""

    @abstractmethod
    def find_relations(self, filters: dict | None = None) -> list[Relation]:
        """Return relationships matching exact equality filters."""

    @abstractmethod
    def get_neighbors(
        self,
        node_id: str,
        direction: str = "out",
        rel_types: set[str] | None = None,
    ) -> list[tuple[Node, Relation]]:
        """Return depth-1 neighbors with the connecting relationship."""

    # -- derived ----------------------------------------------------------

    def calculate_impact(self, node_id: str, depth: int = 3) -> dict:
        from ..operations.impact import compute_impact

        return compute_impact(self, node_id, depth=depth)


def get_graph_store(provider: str, path: str = "", **kwargs) -> GraphStore:
    """Return a GraphStore for the requested provider, with graceful fallback."""
    provider = (provider or "ladybugdb").lower()
    if provider in ("ladybug", "ladybugdb"):
        try:
            from .ladybug_store import LadybugStore

            store = LadybugStore(path, **kwargs)
            store.connect()
            return store
        except (ImportError, RuntimeError) as exc:  # pragma: no cover - env dependent
            import warnings

            warnings.warn(
                f"ladybug backend unavailable ({exc}); falling back to in-memory store"
            )
            from .memory_store import MemoryStore

            return MemoryStore()
    if provider in ("memory", "inmem", "dict", "none"):
        from .memory_store import MemoryStore

        return MemoryStore()
    raise ValueError(f"unknown graph provider: {provider!r}")
