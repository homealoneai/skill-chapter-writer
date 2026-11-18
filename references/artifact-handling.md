# Artifact handling

Artifacts — images, diagrams, tables, and code blocks — are first-class graph nodes, not decoration. Each artifact is an `Artifact` node with a subtype (in `metadata.subtype`) and requires a purpose and relationships, just like prose. The original artifact is always preserved; a textual description is metadata, never a replacement.

## Images

Images (PNG, JPEG, WebP, …) are registered as `Artifact` nodes with subtype `image` (id prefix `IMG`).

Principles:

- **Register** the image as a node in its owning document.
- **Store the relative path** — the workspace-relative path to the image file, not a copy.
- **Extract a visual description** of what the image actually shows.
- **Identify the purpose** — what the image explains or supports.
- **Propose relationships** — typically `illustrates` (the image depicts a paragraph) or `supports`.
- **Validate** — artifact purpose and relationship integrity.
- **Persist** — via the CLI.
- **Preserve the original** — never alter, recompress, or replace the image file.

The description is metadata that helps retrieval; it is **not a replacement** for the image. The image remains the source of truth and stays in the document.

### Image registration flow (8 steps)

1. **Detect** the image reference in the Markdown document.
2. **Resolve and verify** the image path relative to the workspace root (confirm it exists and is in scope).
3. **Register the relative path** on the artifact node; leave the original file untouched.
4. **Extract a visual description** of the image's actual content (via vision/LLM).
5. **Identify the artifact's purpose** — what the image explains or supports in its document.
6. **Propose relationships** (`illustrates`, `supports`, `references`) to the relevant nodes.
7. **Validate** — artifact-purpose and relationship-integrity checks must pass.
8. **Persist** the `Artifact` node and its relationships through the CLI, preserving the original image.

## Diagrams

Diagrams are registered as `Artifact` nodes with subtype `diagram` (id prefix `FLOW`). Supported forms include Mermaid, PlantUML, SVG, and PNG.

For diagrams, maintain **both**:

- the **original visual** (the rendered PNG/SVG as it appears in the document), and
- the **editable structured form** (the Mermaid/PlantUML source), when available.

Keep the source and the render in sync; the structured form is what lets the diagram be edited and diffed, while the render is what the reader sees.

## Tables

Tables are registered as `Artifact` nodes with subtype `table` (id prefix `TABLE`). Treat a table as a structured artifact:

- **Preserve the schema** — the columns and their types/units.
- **Preserve the semantic purpose** — what relationship the table communicates (comparison, mapping, reference data).

Never flatten a table into prose. The structure is the content.

## Code blocks

Code blocks are registered as `Artifact` nodes with subtype `code` (id prefix `CODE`).

- **Preserve formatting** — exact indentation, line breaks, and language fence.
- **Do NOT apply paragraph atomicity** — a code block is one artifact regardless of length; do not split it into lines.
- **Link to requirements/decisions** — relate the code to the `Decision` or `Paragraph` nodes it implements (`implements`) or supports (`supports`).

## Common rule

Every artifact must have a purpose and at least one valid relationship (unless `authoring.allow_unlinked_content` is true). An artifact with no identifiable purpose fails validation.
