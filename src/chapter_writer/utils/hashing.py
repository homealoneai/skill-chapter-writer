"""Content and file hashing helpers."""

from __future__ import annotations

import hashlib


def content_hash(text: str) -> str:
    """Return the SHA-256 hex digest of a text string (UTF-8)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_hash(path: str) -> str:
    """Return the SHA-256 hex digest of a file's bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
