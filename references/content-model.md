# Content model

This document defines the graph-node model: node types, properties, stable ids, document identity, and the HTML-comment markers that tie graph nodes to the Markdown source.

## Node types

| Kind | Meaning |
| --- | --- |
| `Document` | A Markdown file in the workspace, identified by its document identity. |
| `Paragraph` | A single semantic unit of prose (the basic unit of authored content). |
| `Artifact` | A non-prose content item, with a subtype. |
| `Question` | An open, unresolved point that must not be answered by invention. |
| `Decision` | A recorded resolution of a Question. |

### Artifact subtypes

`Artifact` nodes carry a subtype (stored in `metadata.subtype`):

| Subtype | Meaning |
| --- | --- |
| `image` | A raster image (PNG, JPEG, WebP, …). |
| `diagram` | A structured diagram (Mermaid, PlantUML, SVG, PNG). |
| `table` | A Markdown table. |
| `code` | A code block. |
| `file` | Another non-text file referenced by the document. |

See `references/artifact-handling.md` for how each subtype is handled.

## Node properties

Every node carries these properties (validated by `schemas/node.schema.json`):

| Property | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable, allocation-based node id (see below). |
| `kind` | string | `Document` \| `Paragraph` \| `Artifact` \| `Question` \| `Decision`. |
| `document_id` | string | Identity of the owning document: `DOC:<normalized path>`. |
| `content` | string | Node text content; for artifacts, the description or source form (never a replacement for the original). |
| `heading` | string | Section heading the node falls under, when applicable. |
| `position` | integer | 1-based ordinal position of the node within its document. |
| `content_hash` | string | Stable hash of the content, used for change detection. |
| `version` | integer | Content version, incremented on each update. |
| `status` | string | Node lifecycle status (e.g. `active`, `draft`, `archived`). |
| `metadata` | object | Free-form metadata; for artifacts, `metadata.subtype` holds the subtype. |
| `provenance` | array | Provenance references: source document(s), origin nodes, or external citations. |
| `created_at` | string | Creation timestamp (ISO 8601). |
| `updated_at` | string | Last-update timestamp (ISO 8601). |

## Stable node ids

Ids are allocated from a fixed prefix per kind/subtype:

| Prefix | Node kind / subtype |
| --- | --- |
| `P` | Paragraph |
| `IMG` | Artifact / image |
| `FLOW` | Artifact / diagram |
| `TABLE` | Artifact / table |
| `CODE` | Artifact / code |
| `Q` | Question |
| `DEC` | Decision |

Examples: `P-0001`, `IMG-0001`, `FLOW-0001`, `TABLE-0001`, `CODE-0001`, `Q-0001`, `DEC-0001`.

`Document` nodes are identified by the document identity (`DOC:<path>`) rather than a numbered prefix. The `file` artifact subtype is recorded as an `Artifact` node; it shares the Artifact kind and its subtype is carried in `metadata.subtype`.

### Id rules

1. **Allocation-based** — ids come from a monotonically increasing per-prefix counter, never from hashing or abbreviating content.
2. **Never derived from content text** — the id carries no information about what the node says.
3. **Never reused** — a deleted node's id is not reissued.
4. **Stable across edits and moves** — editing the content, changing the heading, or moving the paragraph within or between documents does not change the id.

These rules keep ids permanent and content-agnostic, so relationships and external references never dangle when text changes.

## Document identity

Every document is identified by `DOC:<normalized workspace-relative path>`, where the path is normalized to forward slashes with redundant segments collapsed (for example `DOC:docs/authentication.md`). This identity is used as the `document_id` on every node that belongs to the document and as the id of the document's own `Document` node.

The document identity is derived from the file location, not from the document's title or content, so renaming a file changes only the identity — node ids stay stable.

## HTML-comment markers

The graph is anchored to the Markdown source with HTML-comment markers, so the CLI can keep the two in sync. Agents must preserve these markers and let the CLI manage them.

- **Document marker** — placed at the top of each indexed document:

  ```html
  <!-- chapter-writer:document DOC:docs/authentication.md -->
  ```

- **Node marker** — placed immediately before each content node's content:

  ```html
  <!-- chapter-writer:node P-0001 -->
  ```

The markers are the contract between the Markdown file and the graph. The CLI reads them to locate nodes and writes them when content is added or removed. Never edit, renumber, or hand-place markers — the CLI is the only writer.
