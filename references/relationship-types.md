# Relationship types

Relationships are directed: they point from a **source** node to a **target** node. Each relationship has an `id`, `source_id`, `target_id`, `type`, and an optional `description` (see `schemas/relation.schema.json`).

There are exactly 10 relationship types.

| Type | Direction & semantics |
| --- | --- |
| `depends_on` | **source requires target to stay valid.** If the target changes, the source must be re-checked. |
| `refines` | **source adds detail about target.** Source is a more specific statement of the target. |
| `supports` | **source provides justification or evidence for target.** Source backs the target's claim. |
| `implements` | **source describes an implementation of target.** Source realizes a requirement, decision, or design stated by target. |
| `references` | **source references target without depending on it.** A pointer or cross-mention with no validity obligation. |
| `contradicts` | **source conflicts with target.** The two statements cannot both be true as written. |
| `supersedes` | **source replaces target.** Target is obsolete once source is accepted. |
| `derived_from` | **source was created using target as its origin.** Source is a transformation, extraction, or restatement of target. |
| `illustrates` | **an artifact visually explains another node.** Source (an image/diagram/table) depicts the target's content. |
| `contains` | **a document or section contains a content node.** Source (the container) owns the target (the content). |

## Reading direction

The arrow reads "source → target", for example:

- `P-0002 → depends_on → P-0001` means P-0002 stays valid only if P-0001 does.
- `DEC-0001 → supersedes → DEC-0000` means DEC-0001 replaces DEC-0000.
- `IMG-0001 → illustrates → P-0003` means the image depicts paragraph P-0003.
- `DOC:docs/authentication.md → contains → P-0001` means the document owns that paragraph.

## Multiple relationships

Multiple relationships between the same pair of nodes are allowed when each is semantically valid. For example, an artifact may both `illustrate` a paragraph and `supports` the decision that paragraph depends on. Each relationship is stored separately with its own id and description.

## Guidance

- Prefer the most specific type that is true. Use `references` only when none of the stronger types (`depends_on`, `refines`, `supports`, `implements`) apply.
- Use `contradicts` deliberately: it triggers `required_review` on impact analysis and should be accompanied by a `Question` node until resolved.
- Keep `contains` structural (container → content); do not use it as a catch-all for "appears in".
