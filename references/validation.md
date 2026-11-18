# Validation

Validation checks that a proposal (and, after commit, the whole workspace) is consistent. It splits into two layers: **deterministic rules** enforced by code, and **LLM semantic analysis** judged by the model.

## Validation rules

| Rule | Kind | Description |
| --- | --- | --- |
| Paragraph atomicity | deterministic + semantic | Each `Paragraph` expresses a single semantic idea (see `references/writing-rules.md`). |
| Paragraph length | deterministic | Paragraphs must not exceed `authoring.maximum_paragraph_words` (default 120). |
| Relationship integrity | deterministic | No missing targets, no self-relations, no invalid types, no prohibited cycles. |
| Document scope | deterministic | Every node belongs to a document inside the workspace; paths resolve within the workspace root. |
| Missing context | semantic | A change that depends on content that is not retrieved or linked (and `require_relationships` is true). |
| Potential contradictions | semantic | New content conflicts with existing nodes; flagged for a `Question` node. |
| Existing-content duplication | semantic | New content duplicates an existing node; prefer linking to the existing node. |
| Invalid references | deterministic + semantic | Markdown links/images that point to missing or out-of-scope targets. |
| Artifact purpose | semantic | Every artifact has an identifiable purpose and appropriate relationships (see `references/artifact-handling.md`). |
| Document-purpose alignment | semantic | A change is consistent with the document's stated purpose and audience. |

## Deterministic rules (enforced by code)

These are structural and always enforced, with no model judgment:

- **Relationship integrity** — a relationship's `source_id` and `target_id` must resolve to existing nodes; self-relations are rejected; `type` must be one of the 10 valid types; cycles are prohibited for types where a cycle is meaningless (for example a chain of `depends_on` that loops back on itself).
- **Document scope** — node paths must be inside the workspace root and match the `documents.include` / `documents.exclude` patterns.
- **Paragraph length** — a hard word-count ceiling.
- **Invalid references** — links and image paths that cannot be resolved.

Deterministic failures produce `validation_failed` and must be fixed before commit.

## LLM semantic analysis

These require understanding the meaning of content, so they are judged by the model:

- atomicity in the semantic sense (is this really one idea?),
- missing context (does the change lean on unstated facts?),
- potential contradictions,
- duplication of existing content,
- artifact purpose,
- document-purpose alignment.

Semantic findings are reported as warnings or failures with an explanation. The model may recommend changes but must not silently rewrite content to make validation pass.

## Split summary

| Layer | Who enforces | Examples |
| --- | --- | --- |
| Deterministic | Code | Relationship integrity, scope, length, resolvable references. |
| Semantic | LLM | Contradictions, duplication, missing context, purpose alignment. |

`chapter-writer validate` returns a `validation` object: `{"valid": <bool>, "warnings": [...]}`. A proposal with `valid: false` must not be committed.
