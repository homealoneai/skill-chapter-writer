"""Ladybug-backed GraphStore (the primary backend).

Ladybug (https://ladybugdb.com) is an embedded graph database with a Kuzu-like
Python API: ``lb.Database(path)`` + ``lb.Connection(db)`` and Cypher execution
via ``conn.execute(cypher, parameters)``. Results are read positionally from
``list(result)``, which the API guarantees as list-of-lists.
"""

from __future__ import annotations

import os

from ..models import Node, Relation
from . import migrations
from .graph_store import (
    GraphStore,
    node_to_row,
    relation_to_row,
    row_to_node,
    row_to_relation,
)

try:
    import ladybug as lb
except ImportError:  # pragma: no cover - handled by the factory
    lb = None

_NODE_COLS = [
    "id",
    "kind",
    "document_id",
    "content",
    "heading",
    "position",
    "content_hash",
    "version",
    "status",
    "meta",
    "provenance",
    "created_at",
    "updated_at",
]

_REL_COLS = ["id", "type", "description", "created_at", "created_by"]


class LadybugStore(GraphStore):
    def __init__(self, path: str, **kwargs):
        self.path = path
        self._db = None
        self._conn = None
        self._schema_created = False

    # -- lifecycle --------------------------------------------------------

    def connect(self) -> "LadybugStore":
        if lb is None:
            raise RuntimeError("ladybug package is not installed")
        if self._conn is not None:
            return self
        parent = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(parent, exist_ok=True)
        self._db = lb.Database(self.path)
        self._conn = lb.Connection(self._db)
        return self

    def close(self) -> None:
        if self._conn is not None:
            close = getattr(self._conn, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # pragma: no cover
                    pass
            self._conn = None
        self._db = None
        self._schema_created = False

    def _execute(self, cypher: str, params: dict | None = None):
        if self._conn is None:
            raise RuntimeError("store is not connected")
        return self._conn.execute(cypher, params or {})

    def _rows(self, cypher: str, params: dict | None = None) -> list[list]:
        return [list(r) for r in self._execute(cypher, params)]

    def _node_return(self, alias: str) -> str:
        return ", ".join(f"{alias}.{c}" for c in _NODE_COLS)

    def _node_from_values(self, values: list) -> Node:
        record = dict(zip(_NODE_COLS, values))
        return row_to_node(record)

    # -- schema -----------------------------------------------------------

    def create_schema(self) -> None:
        if self._schema_created:
            return
        existing = self._existing_tables()
        if "Node" not in existing:
            self._execute(migrations.NODE_TABLE_DDL)
        if "Relation" not in existing:
            self._execute(migrations.REL_TABLE_DDL)
        self._schema_created = True

    def _existing_tables(self) -> set[str]:
        try:
            rows = self._rows("CALL SHOW_TABLES() RETURN *")
        except Exception:  # pragma: no cover - fall back to empty
            return set()
        names: set[str] = set()
        for row in rows:
            for cell in row:
                if isinstance(cell, str):
                    names.add(cell)
        return names

    # -- nodes ------------------------------------------------------------

    def create_node(self, node: Node) -> Node:
        row = node_to_row(node)
        cols = ", ".join(f"n.{c}" for c in _NODE_COLS)
        params = {f"p_{c}": row[c] for c in _NODE_COLS}
        placeholders = ", ".join(f"{c}: $p_{c}" for c in _NODE_COLS)
        self._execute(f"CREATE (n:Node {{ {placeholders} }})", params)
        return node

    def get_node(self, node_id: str) -> Node | None:
        rows = self._rows(
            f"MATCH (n:Node) WHERE n.id = $id RETURN {self._node_return('n')}",
            {"id": node_id},
        )
        return self._node_from_values(rows[0]) if rows else None

    def update_node(self, node: Node) -> Node:
        row = node_to_row(node)
        params = {"id": node.id}
        sets = []
        for c in _NODE_COLS:
            if c == "id":
                continue
            params[f"p_{c}"] = row[c]
            sets.append(f"n.{c} = $p_{c}")
        self._execute(
            f"MATCH (n:Node) WHERE n.id = $id SET {', '.join(sets)}", params
        )
        return node

    def delete_node(self, node_id: str) -> None:
        self._execute(
            "MATCH (n:Node) WHERE n.id = $id DETACH DELETE n", {"id": node_id}
        )

    def find_nodes(self, filters: dict | None = None) -> list[Node]:
        filters = {k: v for k, v in (filters or {}).items() if k in _NODE_COLS}
        params = {}
        wheres = []
        for k, v in filters.items():
            params[f"p_{k}"] = v
            wheres.append(f"n.{k} = $p_{k}")
        where = f"WHERE {' AND '.join(wheres)}" if wheres else ""
        rows = self._rows(
            f"MATCH (n:Node) {where} RETURN {self._node_return('n')}", params
        )
        return [self._node_from_values(r) for r in rows]

    # -- relationships ----------------------------------------------------

    def create_relation(self, relation: Relation) -> Relation:
        params = {"source": relation.source_id, "target": relation.target_id}
        props = relation_to_row(relation)
        for c in _REL_COLS:
            params[f"p_{c}"] = props[c]
        assigns = ", ".join(f"{c}: $p_{c}" for c in _REL_COLS)
        self._execute(
            "MATCH (a:Node), (b:Node) WHERE a.id = $source AND b.id = $target "
            f"CREATE (a)-[:Relation {{ {assigns} }}]->(b)",
            params,
        )
        return relation

    def delete_relation(self, relation_id: str) -> None:
        self._execute(
            "MATCH (a:Node)-[r:Relation]->(b:Node) WHERE r.id = $rid DELETE r",
            {"rid": relation_id},
        )

    def find_relations(self, filters: dict | None = None) -> list[Relation]:
        filters = filters or {}
        params = {}
        wheres = []
        col_map = {"source_id": "a.id", "target_id": "b.id"}
        for k, v in filters.items():
            if k in _REL_COLS:
                params[f"p_{k}"] = v
                wheres.append(f"r.{k} = $p_{k}")
            elif k in col_map:
                params[f"p_{k}"] = v
                wheres.append(f"{col_map[k]} = $p_{k}")
        where = f"WHERE {' AND '.join(wheres)}" if wheres else ""
        rows = self._rows(
            "MATCH (a:Node)-[r:Relation]->(b:Node) "
            f"{where} RETURN a.id, b.id, r.id, r.type, r.description, r.created_at, r.created_by",
            params,
        )
        out = []
        for src, tgt, rid, rtype, desc, created, by in rows:
            out.append(
                Relation(
                    id=rid,
                    source_id=src,
                    target_id=tgt,
                    type=rtype,
                    description=desc or "",
                    created_at=created or "",
                    created_by=by or "",
                )
            )
        return out

    def get_neighbors(
        self,
        node_id: str,
        direction: str = "out",
        rel_types: set[str] | None = None,
    ) -> list[tuple[Node, Relation]]:
        rel_filter = ""
        if rel_types:
            quoted = ", ".join(f"'{t}'" for t in sorted(rel_types))
            rel_filter = f" AND r.type IN [{quoted}]"

        if direction == "out":
            cypher = (
                "MATCH (a:Node)-[r:Relation]->(b:Node) "
                f"WHERE a.id = $id{rel_filter} "
                f"RETURN {self._node_return('b')}, r.id, r.type, r.description, r.created_at, r.created_by"
            )
        elif direction == "in":
            cypher = (
                "MATCH (a:Node)-[r:Relation]->(b:Node) "
                f"WHERE b.id = $id{rel_filter} "
                f"RETURN {self._node_return('a')}, r.id, r.type, r.description, r.created_at, r.created_by"
            )
        else:
            # 'both'
            cypher = (
                "MATCH (a:Node)-[r:Relation]->(b:Node) "
                f"WHERE (a.id = $id OR b.id = $id){rel_filter} "
                f"RETURN {self._node_return('a')}, {self._node_return('b')}, r.id, r.type, r.description, r.created_at, r.created_by"
            )

        rows = self._rows(cypher, {"id": node_id})
        out = []
        n = len(_NODE_COLS)
        for row in rows:
            if direction in ("out", "in"):
                node = self._node_from_values(row[:n])
                rel = _rel_from_values(row[n:])
            else:
                a = self._node_from_values(row[:n])
                b = self._node_from_values(row[n : 2 * n])
                rel = _rel_from_values(row[2 * n :])
                node = a if a.id == node_id else b
            out.append((node, rel))
        return out


def _rel_from_values(values: list) -> Relation:
    record = dict(zip(_REL_COLS, values))
    rel = row_to_relation(
        {
            "id": record.get("id", ""),
            "source_id": "",
            "target_id": "",
            "type": record.get("type", ""),
            "description": record.get("description", ""),
            "created_at": record.get("created_at", ""),
            "created_by": record.get("created_by", ""),
        }
    )
    return rel
