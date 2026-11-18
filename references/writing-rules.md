# Writing rules

These rules govern how content is split into graph nodes. They apply to prose (`Paragraph` nodes). Code blocks are exempt from atomicity rules — see `references/artifact-handling.md`.

## The 10 content atomicity rules

1. **Single semantic idea.** Each node expresses exactly one idea, claim, or step. Do not bundle a second, separable idea into the same node.
2. **No unrelated decisions combined.** A statement of fact and a decision about that fact belong in different nodes (the decision becomes a `Decision` node).
3. **Enough context to stand alone.** A node must be understandable without its neighbors; avoid dangling pronouns ("it", "this") that only resolve in surrounding text.
4. **Not excessively long.** Stay within the length guidance below. A node that runs long usually encodes more than one idea.
5. **Stable identifiers.** Ids are allocated, never derived from content, and never reused — see `references/content-model.md`.
6. **Relationships to relevant nodes.** A node links to the nodes it depends on, refines, supports, implements, or references. Unlinked content is discouraged (see the `require_relationships` and `allow_unlinked_content` config).
7. **References its source document.** Every node carries its owning document identity (`document_id`) and provenance pointing back to the source file.
8. **Not created without a valid contextual relationship.** A new node must relate to existing content or to the requested change; orphan nodes are not allowed when `require_relationships` is true.
9. **Avoid excessive fragmentation.** Do not split every sentence into its own node. Split only at real semantic boundaries, so retrieval and impact stay meaningful.
10. **Atomicity is semantic, not a word-count.** The goal is one idea per node, not hitting a target length. A short sentence that is a complete idea is atomic; a long paragraph with one idea may still be atomic.

## Length guidance

| Bound | Value | Meaning |
| --- | --- | --- |
| Default maximum | **120 words** | A paragraph above this length is flagged for splitting. |
| Recommended | **80 words** | Aim here for comfortable retrieval and review. |

These are configurable via `authoring.maximum_paragraph_words` and `authoring.recommended_paragraph_words`.

## Splitting policy

The LLM may **recommend** a split when a node violates the rules or length bounds, but the system must **not auto-split** a node on its own. A split must:

- preserve the full meaning of the original (no information loss);
- preserve provenance (each child keeps a `derived_from` link back to the original);
- produce children that each satisfy rules 1–10.

If a split cannot preserve meaning and provenance, leave the node whole and flag it for human review instead.
