"""Workspace configuration model."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import yaml

from ..utils import normalize_relpath

DEFAULT_CONFIG = {
    "version": 1,
    "workspace": {"id": "", "name": "Documentation Workspace", "root": "."},
    "storage": {
        "graph": {"provider": "ladybugdb", "path": ".graph-md/graph.db"},
        "index": {"path": ".graph-md/index"},
    },
    "retrieval": {
        "lexical": {"enabled": True, "algorithm": "tfidf", "ngram_range": [1, 2]},
        "graph": {"enabled": True, "default_depth": 1, "maximum_depth": 3},
        "hybrid": {
            "lexical_weight": 0.45,
            "graph_weight": 0.35,
            "document_scope_weight": 0.20,
        },
    },
    "authoring": {
        "maximum_paragraph_words": 120,
        "recommended_paragraph_words": 80,
        "require_relationships": True,
        "allow_unlinked_content": False,
    },
    "documents": {
        "include": ["**/*.md"],
        "exclude": [".graph-md/**", "node_modules/**", ".git/**"],
    },
}


@dataclass
class WorkspaceConfig:
    """The parsed ``.graph-md/config.yaml`` plus the absolute workspace root."""

    data: dict = field(default_factory=lambda: dict(DEFAULT_CONFIG))
    root: str = ""

    # -- constructors -----------------------------------------------------

    @classmethod
    def defaults(cls, root: str, name: str = "Documentation Workspace") -> "WorkspaceConfig":
        data = dict(DEFAULT_CONFIG)
        data = _deep_copy(DEFAULT_CONFIG)
        data["workspace"]["name"] = name
        data["workspace"]["root"] = "."
        return cls(data=data, root=os.path.abspath(root))

    @classmethod
    def load(cls, root: str) -> "WorkspaceConfig":
        """Load config from ``<root>/.graph-md/config.yaml`` or fall back to defaults."""
        root_abs = os.path.abspath(root)
        path = os.path.join(root_abs, ".graph-md", "config.yaml")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
            data = _merge(DEFAULT_CONFIG, raw)
        else:
            data = _deep_copy(DEFAULT_CONFIG)
        return cls(data=data, root=root_abs)

    # -- persistence ------------------------------------------------------

    def save(self) -> None:
        os.makedirs(os.path.join(self.root, ".graph-md"), exist_ok=True)
        path = os.path.join(self.root, ".graph-md", "config.yaml")
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(self.data, fh, sort_keys=False, default_flow_style=False)

    # -- accessors --------------------------------------------------------

    def get(self, dotted: str, default: Any = None) -> Any:
        cur: Any = self.data
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    @property
    def workspace_id(self) -> str:
        return self.get("workspace.id", "")

    @property
    def workspace_name(self) -> str:
        return self.get("workspace.name", "")

    @property
    def graph_provider(self) -> str:
        return self.get("storage.graph.provider", "ladybugdb")

    @property
    def graph_path(self) -> str:
        rel = self.get("storage.graph.path", ".graph-md/graph.db")
        return os.path.join(self.root, normalize_relpath(rel)) if rel else ""

    @property
    def index_path(self) -> str:
        rel = self.get("storage.index.path", ".graph-md/index")
        return os.path.join(self.root, normalize_relpath(rel)) if rel else ""

    @property
    def documents_include(self) -> list:
        return list(self.get("documents.include", ["**/*.md"]))

    @property
    def documents_exclude(self) -> list:
        return list(self.get("documents.exclude", []))

    @property
    def authoring(self) -> dict:
        return dict(self.get("authoring", {}))

    @property
    def retrieval(self) -> dict:
        return dict(self.get("retrieval", {}))


def _deep_copy(obj: Any) -> Any:
    import copy

    return copy.deepcopy(obj)


def _merge(base: dict, override: dict) -> dict:
    import copy

    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out
