"""Workspace manager: owns ``.graph-md`` and wires config, store, and counters."""

from __future__ import annotations

import fnmatch
import json
import os
from pathlib import Path

from ..models import WorkspaceConfig
from ..utils import node_prefix, normalize_relpath
from . import migrations
from .graph_store import GraphStore, get_graph_store


class WorkspaceStore:
    """A single workspace: configuration, graph store, and metadata directories."""

    def __init__(self, root: str, config: WorkspaceConfig | None = None):
        self.root = os.path.abspath(root)
        self.config = config or WorkspaceConfig.load(self.root)
        self._graph: GraphStore | None = None
        self._counters: dict[str, int] = {}

    # -- paths ------------------------------------------------------------

    @property
    def meta_dir(self) -> str:
        return os.path.join(self.root, ".graph-md")

    @property
    def state_dir(self) -> str:
        return os.path.join(self.meta_dir, "state")

    @property
    def index_dir(self) -> str:
        return self.config.index_path

    @property
    def cache_dir(self) -> str:
        return os.path.join(self.meta_dir, "cache")

    # -- lifecycle --------------------------------------------------------

    @classmethod
    def open(cls, root: str) -> "WorkspaceStore":
        ws = cls(root)
        ws._open_graph()
        return ws

    def _open_graph(self) -> None:
        self._graph = get_graph_store(self.config.graph_provider, self.config.graph_path)

    @property
    def graph(self) -> GraphStore:
        if self._graph is None:
            self._open_graph()
        return self._graph

    def init(self, name: str | None = None) -> "WorkspaceStore":
        """Create the workspace metadata layout and initialize the graph."""
        os.makedirs(self.meta_dir, exist_ok=True)
        os.makedirs(self.state_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.index_dir, exist_ok=True)

        if name:
            self.config.data.setdefault("workspace", {})["name"] = name
        if not self.config.workspace_id:
            self.config.data.setdefault("workspace", {})["id"] = _derive_workspace_id(self.root)
        self.config.save()

        self._open_graph()
        migrations.ensure_schema(self.graph, self.state_dir)
        self._load_counters()
        return self

    def close(self) -> None:
        if self._graph is not None:
            self._graph.close()

    # -- id allocation ----------------------------------------------------

    def _counters_path(self) -> str:
        return os.path.join(self.state_dir, "ids.json")

    def _load_counters(self) -> None:
        path = self._counters_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    self._counters = {k: int(v) for k, v in json.load(fh).items()}
            except (ValueError, OSError):
                self._counters = {}
        else:
            self._counters = {}

    def _save_counters(self) -> None:
        os.makedirs(self.state_dir, exist_ok=True)
        with open(self._counters_path(), "w", encoding="utf-8") as fh:
            json.dump(self._counters, fh)

    def allocate_node_id(self, kind: str, width: int = 4) -> str:
        """Allocate the next monotonic, never-reused id for a node kind."""
        prefix = node_prefix(kind)
        nxt = self._counters.get(prefix, 1)
        while True:
            candidate = f"{prefix}-{nxt:0{width}d}"
            nxt += 1
            if self.graph.get_node(candidate) is None:
                break
        self._counters[prefix] = nxt
        self._save_counters()
        return candidate

    # -- document discovery ----------------------------------------------

    def discover_documents(self) -> list[str]:
        """Return normalized workspace-relative paths of included Markdown files."""
        include = self.config.documents_include
        exclude = self.config.documents_exclude
        found: list[str] = []
        root = Path(self.root)
        for pattern in include:
            for p in root.rglob(pattern) if "**" in pattern else root.glob(pattern):
                if not p.is_file():
                    continue
                rel = normalize_relpath(str(p.relative_to(root)))
                if rel.endswith(".md") and not _excluded(rel, exclude):
                    found.append(rel)
        return sorted(set(found))


def _excluded(relpath: str, patterns: list[str]) -> bool:
    for pat in patterns:
        pat = normalize_relpath(pat) if pat else pat
        if fnmatch.fnmatch(relpath, pat) or fnmatch.fnmatch(relpath, pat.rstrip("/") + "/*"):
            return True
    return False


def _derive_workspace_id(root: str) -> str:
    import hashlib

    digest = hashlib.sha256(os.path.abspath(root).encode("utf-8")).hexdigest()[:12]
    return f"workspace-{digest}"
