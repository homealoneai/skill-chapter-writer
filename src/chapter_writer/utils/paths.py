"""Path normalization and filesystem-boundary enforcement.

All persistent document identities are *workspace-relative*, POSIX-normalized
paths. Absolute paths are only ever used transiently when touching the
filesystem, never as graph identifiers.
"""

from __future__ import annotations

import os
import posixpath


def normalize_relpath(path: str) -> str:
    """Normalize a workspace-relative path to a stable POSIX string.

    Rejects absolute paths and paths that lexically escape the workspace root
    (``..``). The result never carries a leading ``./`` and always uses ``/``.
    """
    if not isinstance(path, str):
        raise TypeError(f"path must be a string, got {type(path).__name__}")

    p = path.replace(os.sep, "/")
    p = p.strip()

    if p == "":
        return ""

    if p.startswith("/") or (len(p) >= 2 and p[1] == ":"):
        raise ValueError(f"absolute paths are not valid workspace paths: {path!r}")

    p = posixpath.normpath(p)
    if p in (".", ""):
        return ""
    if p == ".." or p.startswith("../"):
        raise ValueError(f"path escapes the workspace root: {path!r}")

    return p


def resolve_abs(root: str, relpath: str) -> str:
    """Resolve a workspace-relative path against an absolute workspace root."""
    rel = normalize_relpath(relpath)
    if rel == "":
        return os.path.abspath(root)
    return os.path.abspath(os.path.join(root, rel))


def ensure_within(root: str, path: str, *, real: bool = True) -> str:
    """Assert that ``path`` lives inside ``root`` and return its absolute form.

    With ``real=True`` (default) symlinks are resolved so a symlink pointing
    outside the workspace is rejected. Raises ``ValueError`` otherwise.
    """
    root_abs = os.path.abspath(root)
    path_abs = os.path.abspath(path)

    if real:
        root_real = os.path.realpath(root_abs)
        path_real = os.path.realpath(path_abs)
        if path_real != root_real and not path_real.startswith(root_real + os.sep):
            raise ValueError(f"path escapes the workspace root: {path!r}")
    else:
        if path_abs != root_abs and not path_abs.startswith(root_abs + os.sep):
            raise ValueError(f"path escapes the workspace root: {path!r}")

    return path_abs


def is_within(root: str, path: str) -> bool:
    """Return True if ``path`` is inside ``root`` (symlinks resolved)."""
    try:
        ensure_within(root, path, real=True)
        return True
    except ValueError:
        return False
