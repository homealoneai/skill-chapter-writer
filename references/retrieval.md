# Retrieval

`chapter-writer` retrieval is hybrid: it merges lexical similarity, graph traversal, and document-scope relevance into a single ranking. Retrieval returns **context** — matching nodes plus their relationships and provenance — not just a list of paragraphs.

## Lexical retrieval (TF-IDF)

Lexical relevance uses TF-IDF via scikit-learn:

```python
TfidfVectorizer(ngram_range=(1, 2), lowercase=True, strip_accents="unicode")
```

- `ngram_range=(1, 2)` — unigrams and bigrams capture multi-word terms like "token renewal".
- `lowercase=True`, `strip_accents="unicode"` — normalize case and accents.
- Similarity is **cosine similarity** between the query vector and node-content vectors.

The index is:

- **rebuildable** — `chapter-writer index` reconstructs it from all in-scope documents;
- **incrementally updated** — changes to individual nodes update the index without a full rebuild.

## Graph traversal

Graph relevance expands from seed nodes across the relationship graph:

- **Direct relationships** — neighbors of a seed node contribute.
- **Neighbor expansion** — traversal can go deeper than direct neighbors.
- **Configurable depth** — `retrieval.graph.default_depth` (default `1`) sets the normal hop count; `retrieval.graph.maximum_depth` (default `3`) caps it.
- **Filtering** — traversal can filter by relationship type, document, and node type.
- **Impact traversal** — following `depends_on`, `implements`, `contradicts`, and related edges to find nodes affected by a change.
- **Deterministic** — given the same graph, seed nodes, and parameters, traversal yields the same result.

## Hybrid ranking

Lexical, graph, and document-scope scores are merged with configurable weights (from `retrieval.hybrid`):

| Signal | Default weight | What it measures |
| --- | --- | --- |
| Lexical | `0.45` | Query/content text similarity. |
| Graph | `0.35` | Proximity in the relationship graph. |
| Document scope | `0.20` | Relevance of the node's document to the query/scope. |

Weights are configurable in `.graph-md/config.yaml`.

## Result shape

Each retrieved node is returned as:

```json
{
  "node_id": "P-0001",
  "score": 0.91,
  "retrieval_reasons": ["lexical_match", "direct_dependency", "same_document"]
}
```

| Field | Meaning |
| --- | --- |
| `node_id` | Stable node id. |
| `score` | Merged relevance score (0–1). |
| `retrieval_reasons` | Which signals contributed (e.g. `lexical_match`, `direct_dependency`, `same_document`). |

## Context, not a paragraph list

Alongside the ranked nodes, retrieval returns the **context** needed to act on them:

- the node's **relationships** (so the caller sees what depends on or supports it);
- the node's **provenance** (which document it came from and how it was derived);
- the containing **document** identity.

A caller using only the paragraph text is using half the result; the relationships and provenance are what make the change consistent and reviewable.
