"""Small shared utilities: ids, hashes, paths, and timestamps."""

from __future__ import annotations

from datetime import datetime, timezone


def now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (second precision)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


from .hashing import content_hash, file_hash  # noqa: E402
from .ids import (  # noqa: E402
    NODE_KIND_PREFIX,
    allocate_id,
    document_id,
    document_path_from_id,
    is_document_id,
    is_valid_node_id,
    node_prefix,
)
from .paths import (  # noqa: E402
    ensure_within,
    normalize_relpath,
    resolve_abs,
)

__all__ = [
    "NODE_KIND_PREFIX",
    "allocate_id",
    "content_hash",
    "document_id",
    "document_path_from_id",
    "ensure_within",
    "file_hash",
    "is_document_id",
    "is_valid_node_id",
    "node_prefix",
    "normalize_relpath",
    "now_iso",
    "resolve_abs",
]
