"""Image artifact handling."""

from __future__ import annotations

import os

from ..models import Artifact
from ..utils import content_hash, ensure_within, file_hash, normalize_relpath
from .markdown import ParsedUnit

_HTTP_PREFIXES = ("http://", "https://", "data:")


def is_external(src: str) -> bool:
    return src.startswith(_HTTP_PREFIXES)


def image_artifact_from_unit(
    unit: ParsedUnit, document_id: str, node_id: str
) -> Artifact:
    """Build an image artifact from a parsed standalone image unit."""
    src = unit.meta.get("src", "")
    alt = unit.meta.get("alt", "")
    external = is_external(src)
    path = "" if external else (normalize_relpath(src) if src else "")
    return Artifact(
        id=node_id,
        document_id=document_id,
        type="image",
        path=path,
        description=alt,
        purpose="",
        content="",
        content_hash=content_hash(src or alt),
        metadata={"alt": alt, "src": src, "external": external},
    )


def validate_image_file(root: str, relpath: str) -> tuple[bool, str]:
    """Check that a local image file exists inside the workspace root."""
    if not relpath:
        return False, "image has no path"
    if is_external(relpath):
        return True, "external"
    try:
        abs_path = ensure_within(root, os.path.join(root, normalize_relpath(relpath)))
    except ValueError as exc:
        return False, str(exc)
    if not os.path.isfile(abs_path):
        return False, f"image file not found: {relpath}"
    return True, abs_path


def hash_image_file(root: str, relpath: str) -> str:
    """Return the SHA-256 of a local image file, or '' if unavailable."""
    ok, result = validate_image_file(root, relpath)
    if not ok or result == "external":
        return ""
    return file_hash(result)
