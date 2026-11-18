"""Stable identifier helpers.

Node identifiers are allocation-based, never derived from content text, and are
never silently reused. A monotonic counter (persisted in ``.graph-md/state``) is
the source of truth for the next number per prefix; ``allocate_id`` simply finds
the next unused candidate given the set of already-taken ids.
"""

from __future__ import annotations

import re

from .paths import normalize_relpath

NODE_KIND_PREFIX = {
    "document": "DOC",
    "paragraph": "P",
    "image": "IMG",
    "diagram": "FLOW",
    "table": "TABLE",
    "code": "CODE",
    "file": "FILE",
    "question": "Q",
    "decision": "DEC",
}

PREFIX_KIND = {v: k for k, v in NODE_KIND_PREFIX.items()}

_NODE_ID_RE = re.compile(r"^(P|IMG|FLOW|TABLE|CODE|FILE|Q|DEC)-(\d{4,})$")
_DOC_ID_RE = re.compile(r"^DOC:(.+)$")


def node_prefix(kind: str) -> str:
    """Return the id prefix for a node kind."""
    if kind not in NODE_KIND_PREFIX:
        raise ValueError(f"unknown node kind: {kind!r}")
    return NODE_KIND_PREFIX[kind]


def document_id(relpath: str) -> str:
    """Build a stable document id from a normalized workspace-relative path."""
    return f"DOC:{normalize_relpath(relpath)}"


def is_document_id(value: str) -> bool:
    return bool(_DOC_ID_RE.match(value))


def document_path_from_id(value: str) -> str | None:
    """Extract the normalized path from a document id, or None."""
    m = _DOC_ID_RE.match(value)
    return m.group(1) if m else None


def is_valid_node_id(value: str) -> bool:
    return bool(_NODE_ID_RE.match(value))


def allocate_id(prefix: str, taken, start: int = 1, width: int = 4) -> str:
    """Return the next unused id for ``prefix``, never reusing a taken id."""
    taken = set(taken)
    n = start
    while True:
        candidate = f"{prefix}-{n:0{width}d}"
        if candidate not in taken:
            return candidate
        n += 1
