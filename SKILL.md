---
name: chapter-writer
description: Use whenever you create, edit, review, or maintain Markdown documentation that must stay consistent across multiple related files, by keeping a persistent per-workspace knowledge graph that tracks paragraphs, artifacts, questions, and decisions plus the relationships between them, so every change is grounded in retrieved context, validated for consistency, and checked for downstream impact.
---

# chapter-writer

`chapter-writer` is a generic, harness-independent agent skill for creating, modifying, reviewing, and maintaining Markdown documents with the help of a persistent knowledge graph. Markdown files remain the human-readable source of truth. A per-workspace graph (`.graph-md/`) acts as the semantic index and context-management layer.

The Markdown files are the artifacts; the graph is the index. **The CLI is the only writer.** Never edit anything under `.graph-md/` (the graph database, the index, or the config) by hand — always use the `chapter-writer` CLI. The CLI keeps the graph and the Markdown markers in sync.

## When to invoke

Invoke this skill when the task is any of:

- Adding, editing, or removing prose in a Markdown document that lives in a graph-maintained workspace.
- Reviewing a document for consistency with other documents, decisions, or artifacts.
- Answering a question about how parts of the docs relate — "what depends on this?", "what breaks if I change this?".
- Finding or resolving contradictions between statements across documents.
- Indexing, searching, or validating a documentation workspace.

Do not invoke it for a single throwaway Markdown file that is not part of a graph-maintained workspace and needs no cross-document consistency.

## Subagent usage

`chapter-writer` is designed to be invoked by a subagent with a limited context:

1. Load only this `SKILL.md` (plus the one reference file relevant to the task).
2. Identify the workspace (`.graph-md/config.yaml`) and the target document.
3. Run the `chapter-writer` CLI with `--json` for every step; never read or edit files under `.graph-md/` directly.
4. Report the structured JSON result verbatim.

The CLI plus this file are the whole contract — no implementation source, database access, or interactive prompt is required.

## Identify the workspace

1. Find the workspace root by looking for `.graph-md/config.yaml`, starting in the current directory and walking upward.
2. If it is not found, treat the directory you were told to work in (or the repository root) as the workspace root and run `chapter-writer init` to create the config and the graph.
3. Run every later command from the workspace root, or pass `--workspace <root>`.

The workspace root is the security boundary: all document and artifact paths resolve relative to it, and the graph only indexes files inside it.

## Identify the target document

1. The target document is the Markdown file the user asked you to change, or the file that best matches the requested change when none is named.
2. Its identity is `DOC:<normalized workspace-relative path>` (for example `DOC:docs/authentication.md`). Normalization uses forward slashes and collapses redundant segments.
3. Confirm the file exists and is covered by the `documents.include` / `documents.exclude` patterns in `.graph-md/config.yaml`.

## The seven-step workflow

Always follow these steps in order. Details and the operation JSON contract are in `references/workflow.md`.

1. **Intake** — restate the request, the workspace, and the target document.
2. **Scope** — decide which documents and node kinds are in scope.
3. **Context retrieval** — run `chapter-writer context` for the target document and query.
4. **Proposal** — state the exact changes (adds, edits, deletions, links) before writing anything.
5. **Consistency validation** — run `chapter-writer validate` on the proposal.
6. **Impact analysis & questions** — run `chapter-writer impact` on every node you would change; register Questions for anything unresolved.
7. **Commit** — persist the approved changes with `chapter-writer add|update|delete|link`, then re-run `chapter-writer validate`.

## Retrieve context

Run `chapter-writer context` before proposing any change:

```bash
chapter-writer context --workspace . --document docs/authentication.md --query "token renewal"
```

Add `--json` for machine-readable results. The result is **context, not just a paragraph list**: it includes the matching nodes, their relationships, and their provenance (which document each came from). Use it to ground your proposal in what already exists.

## Propose changes

1. Write your proposal as a concrete set of operations — new paragraphs, edits, deletions, and links — with the source document and content for each.
2. Do not write to the Markdown file or the graph before validation and impact analysis.
3. Keep each paragraph a single semantic idea, within the length limits (default 120 words max, 80 recommended). See `references/writing-rules.md`.

## Contradictions and unresolved questions

- If retrieved context conflicts with the requested change, or two documents disagree, do **not** invent an answer and do not silently pick one side.
- Register a **Question** node (`Q-0001`, …) with `chapter-writer question --document <doc> --question "…" --reason "…" --related P-0003,P-0004`, capturing exactly what is unresolved, and link it to the conflicting nodes with `chapter-writer link … --type contradicts` (or `references` when the disagreement is only partial).
- Report the conflict and the Question id in your result; wait for a human answer or a **Decision** node before resolving it.
- Record a resolution with `chapter-writer decision --document <doc> --decision "…" --rationale "…"`; a **Decision** node (`DEC-0001`, …) records the resolution. Link it to the Question with `refines` or `supersedes` as appropriate.

## Non-text artifacts

Images, diagrams, tables, and code blocks are first-class content nodes, not decoration:

- Register them as **Artifact** nodes and give each a purpose and relationships.
- Preserve the original exactly (image bytes, source diagram, table schema, code formatting).
- A textual description is metadata, never a replacement for the artifact itself.
- Do not apply paragraph atomicity rules to code blocks; preserve their formatting verbatim.

See `references/artifact-handling.md`.

## Validate

Run `chapter-writer validate` after every proposal and again after every commit:

```bash
chapter-writer validate --workspace .
```

Validation combines deterministic rules (paragraph atomicity, length, relationship integrity such as missing targets / self-relations / invalid types / prohibited cycles, invalid references) with LLM semantic analysis (missing context, potential contradictions, duplication, artifact purpose, document-purpose alignment). A change that fails validation must be fixed or reported — never silently committed. See `references/validation.md`.

## Persist

Only after validation passes, persist the change with the CLI — never by editing the graph files directly:

- `chapter-writer add` — add new paragraphs or artifacts.
- `chapter-writer update` — modify an existing node's content.
- `chapter-writer delete` — remove a node and its markers.
- `chapter-writer link` — add or remove relationships between nodes.
- `chapter-writer question` — register an unresolved question.
- `chapter-writer decision` — record a confirmed decision.

Always pass `--workspace .` (or the root), and `--json` when you want machine-readable results.

## Report results

End every turn with a structured JSON summary in your reply (with `--json` the CLI emits this itself):

```json
{
  "status": "completed",
  "operation": "add",
  "document": "docs/authentication.md",
  "summary": "Added token renewal documentation.",
  "nodes_created": ["P-0014"],
  "nodes_modified": [],
  "nodes_deleted": [],
  "relations_created": [],
  "impact": {"required_review": [], "recommended_review": [], "optional_review": []},
  "questions": [],
  "validation": {"valid": true, "warnings": []}
}
```

`status` is one of `completed | needs_input | validation_failed | conflict | error`. Report it verbatim; never claim `completed` when validation failed or questions remain.

## Reference files

| File | Purpose |
| --- | --- |
| `references/workflow.md` | The seven-step workflow and the operation JSON contract. |
| `references/content-model.md` | Node types, properties, stable ids, and HTML markers. |
| `references/relationship-types.md` | The 10 relationship types and their direction. |
| `references/writing-rules.md` | The 10 content atomicity rules and length guidance. |
| `references/retrieval.md` | Hybrid retrieval (TF-IDF + graph + document scope). |
| `references/validation.md` | Deterministic and LLM validation rules. |
| `references/artifact-handling.md` | Images, diagrams, tables, and code blocks. |
| `schemas/*.json` | JSON Schemas for workspace, node, relation, operation. |
| `templates/workspace.yaml` | The default workspace configuration. |

## Failure modes

| Symptom | Cause | Response |
| --- | --- | --- |
| "Workspace not initialized" | No `.graph-md/config.yaml` at or above the working directory | Run `chapter-writer init` at the intended root. |
| Change appears to do nothing | You edited `.graph-md/` or the Markdown file by hand | Only the CLI writes the graph; re-issue the operation through `chapter-writer`. |
| Validation fails with a missing target | You linked to a node id that does not exist | Look up the correct id with `chapter-writer search` or `context`; never invent ids. |
| Duplicate paragraph detected | The same content already exists in scope | Link to the existing node instead of adding a near-duplicate. |
| Impact reports a required review | A node `depends_on` or `implements` what you changed | Review the listed node before committing. |
