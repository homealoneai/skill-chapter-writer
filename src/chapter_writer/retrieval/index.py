"""TF-IDF lexical index.

The index is a thin corpus wrapper around scikit-learn's ``TfidfVectorizer``.
It is *rebuildable*: the persisted corpus (node id → text + minimal metadata)
can always be re-vectorized from disk, and it is also rebuilt from the graph and
Markdown files by the indexing pipeline. On any content change the corpus is
updated and the vectorizer is lazily refit.
"""

from __future__ import annotations

import json
import os

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class LexicalIndex:
    def __init__(
        self,
        ngram_range: tuple[int, int] = (1, 2),
        lowercase: bool = True,
        strip_accents: str | None = "unicode",
    ):
        self.ngram_range = ngram_range
        self.lowercase = lowercase
        self.strip_accents = strip_accents
        self._corpus: dict[str, dict] = {}  # node_id -> {"text": str, "kind": str, "document_id": str}
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._ids: list[str] = []

    # -- corpus management ------------------------------------------------

    def add(self, node_id: str, text: str, kind: str = "", document_id: str = "") -> None:
        self._corpus[node_id] = {"text": text or "", "kind": kind, "document_id": document_id}
        self._vectorizer = None

    def update(self, node_id: str, text: str, kind: str = "", document_id: str = "") -> None:
        self.add(node_id, text, kind, document_id)

    def remove(self, node_id: str) -> None:
        if node_id in self._corpus:
            del self._corpus[node_id]
            self._vectorizer = None

    def clear(self) -> None:
        self._corpus.clear()
        self._vectorizer = None

    def __len__(self) -> int:
        return len(self._corpus)

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._corpus

    # -- scoring ----------------------------------------------------------

    def _ensure_fit(self) -> None:
        if self._vectorizer is not None:
            return
        if not self._corpus:
            self._matrix = None
            self._ids = []
            self._vectorizer = None
            return
        self._vectorizer = TfidfVectorizer(
            ngram_range=self.ngram_range,
            lowercase=self.lowercase,
            strip_accents=self.strip_accents,
        )
        self._ids = list(self._corpus.keys())
        texts = [self._corpus[nid]["text"] for nid in self._ids]
        self._matrix = self._vectorizer.fit_transform(texts)

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
        kinds: set[str] | None = None,
    ) -> list[tuple[str, float]]:
        """Return ``[(node_id, cosine_score), ...]`` in descending order."""
        self._ensure_fit()
        if not query or self._matrix is None:
            return []
        qvec = self._vectorizer.transform([query])
        sims = cosine_similarity(qvec, self._matrix).flatten()
        scored = []
        for idx, nid in enumerate(self._ids):
            score = float(sims[idx])
            if score <= 0:
                continue
            if filters and not _matches(self._corpus[nid], filters):
                continue
            if kinds and self._corpus[nid].get("kind") not in kinds:
                continue
            scored.append((nid, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    # -- persistence ------------------------------------------------------

    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, "corpus.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self._corpus, fh, ensure_ascii=False)

    def load(self, directory: str) -> None:
        path = os.path.join(directory, "corpus.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                self._corpus = json.load(fh)
        else:
            self._corpus = {}
        self._vectorizer = None


def _matches(entry: dict, filters: dict) -> bool:
    return all(entry.get(k) == v for k, v in filters.items())
