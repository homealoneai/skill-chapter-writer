"""Pure-Python in-memory GraphStore fallback.

Used when the native ``ladybug`` backend is unavailable. It implements the same
``GraphStore`` semantics so the rest of the skill and its tests remain portable.
"""

from __future__ import annotations

from ..models import Node, Relation
from .graph_store import GraphStore, relation_to_row, row_to_relation


class MemoryStore(GraphStore):
    def __init__(self):
        self._nodes: dict[str, dict] = {}
        self._relations: dict[str, dict] = {}

    def connect(self) -> "MemoryStore":
        return self

    def close(self) -> None:
        pass

    def create_schema(self) -> None:
        pass

    # -- nodes ------------------------------------------------------------

    def create_node(self, node: Node) -> Node:
        if node.id in self._nodes:
            raise ValueError(f"node already exists: {node.id}")
        self._nodes[node.id] = node.to_dict()
        return node

    def get_node(self, node_id: str) -> Node | None:
        raw = self._nodes.get(node_id)
        return Node.from_dict(raw) if raw else None

    def update_node(self, node: Node) -> Node:
        if node.id not in self._nodes:
            raise KeyError(f"node does not exist: {node.id}")
        self._nodes[node.id] = node.to_dict()
        return node

    def delete_node(self, node_id: str) -> None:
        self._nodes.pop(node_id, None)
        for rel_id in list(self._relations):
            r = self._relations[rel_id]
            if r["source_id"] == node_id or r["target_id"] == node_id:
                del self._relations[rel_id]

    def find_nodes(self, filters: dict | None = None) -> list[Node]:
        filters = filters or {}
        out = []
        for raw in self._nodes.values():
            if all(raw.get(k) == v for k, v in filters.items()):
                out.append(Node.from_dict(raw))
        return out

    # -- relationships ----------------------------------------------------

    def create_relation(self, relation: Relation) -> Relation:
        if relation.id in self._relations:
            raise ValueError(f"relation already exists: {relation.id}")
        self._relations[relation.id] = relation_to_row(relation)
        return relation

    def delete_relation(self, relation_id: str) -> None:
        self._relations.pop(relation_id, None)

    def find_relations(self, filters: dict | None = None) -> list[Relation]:
        filters = filters or {}
        out = []
        for raw in self._relations.values():
            if all(raw.get(k) == v for k, v in filters.items()):
                out.append(row_to_relation(raw))
        return out

    def get_neighbors(
        self,
        node_id: str,
        direction: str = "out",
        rel_types: set[str] | None = None,
    ) -> list[tuple[Node, Relation]]:
        out = []
        for raw in self._relations.values():
            rel = row_to_relation(raw)
            if rel_types and rel.type not in rel_types:
                continue
            if direction == "out" and rel.source_id == node_id:
                nbr = self.get_node(rel.target_id)
                if nbr:
                    out.append((nbr, rel))
            elif direction == "in" and rel.target_id == node_id:
                nbr = self.get_node(rel.source_id)
                if nbr:
                    out.append((nbr, rel))
            elif direction == "both":
                if rel.source_id == node_id:
                    nbr = self.get_node(rel.target_id)
                elif rel.target_id == node_id:
                    nbr = self.get_node(rel.source_id)
                else:
                    continue
                if nbr:
                    out.append((nbr, rel))
        return out
