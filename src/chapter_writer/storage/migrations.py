"""Graph schema (DDL) and lightweight schema-version management."""

from __future__ import annotations

import json
import os

SCHEMA_VERSION = 1

# A single generic node table keeps the model extensible: new node kinds are new
# ``kind`` values, not new tables.
NODE_TABLE_DDL = (
    "CREATE NODE TABLE Node("
    "id STRING PRIMARY KEY, "
    "kind STRING, "
    "document_id STRING, "
    "content STRING, "
    "heading STRING, "
    "position INT64, "
    "content_hash STRING, "
    "version INT64, "
    "status STRING, "
    "meta STRING, "
    "provenance STRING, "
    "created_at STRING, "
    "updated_at STRING)"
)

# A single generic relationship table; ``type`` holds one of RELATIONSHIP_TYPES.
REL_TABLE_DDL = (
    "CREATE REL TABLE Relation("
    "FROM Node TO Node, "
    "id STRING, "
    "type STRING, "
    "description STRING, "
    "created_at STRING, "
    "created_by STRING)"
)


def schema_state_path(state_dir: str) -> str:
    return os.path.join(state_dir, "schema.json")


def read_schema_version(state_dir: str) -> int:
    path = schema_state_path(state_dir)
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return int(json.load(fh).get("schema_version", 0))
    except (ValueError, OSError, TypeError):
        return 0


def write_schema_version(state_dir: str, version: int = SCHEMA_VERSION) -> None:
    os.makedirs(state_dir, exist_ok=True)
    with open(schema_state_path(state_dir), "w", encoding="utf-8") as fh:
        json.dump({"schema_version": version}, fh)


def ensure_schema(store, state_dir: str) -> None:
    """Create the schema if it has not been initialized for this workspace."""
    current = read_schema_version(state_dir)
    if current == SCHEMA_VERSION:
        return
    if current > SCHEMA_VERSION:
        raise RuntimeError(
            f"workspace graph schema v{current} is newer than supported v{SCHEMA_VERSION}"
        )
    store.create_schema()
    write_schema_version(state_dir, SCHEMA_VERSION)
