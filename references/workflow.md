# Workflow

This document describes the seven-step workflow every chapter-writer operation follows, plus the structured JSON contract for operations and the operation statuses.

## The seven steps

### 1. Intake

Restate the request in concrete terms and capture:

- **Workspace** — the absolute path to the workspace root (the directory containing `.graph-md/config.yaml`).
- **Target document** — the workspace-relative path of the Markdown file to change, and its identity `DOC:<normalized path>`.
- **Intent** — what the user wants (add, edit, remove, review, or answer a question).

If the workspace has no `.graph-md/config.yaml`, run `chapter-writer init` first. If the target document is ambiguous, ask rather than guessing.

### 2. Scope

Decide the boundaries of the change:

- Which documents are in scope (the target plus any documents that directly relate to it).
- Which node kinds matter (Paragraph, Artifact, Question, Decision, Document).
- Which existing nodes are candidates for modification or linking.

Scope keeps retrieval and impact analysis focused. It does not authorize skipping validation: any node you touch, even outside the primary document, must be validated and impact-checked.

### 3. Context retrieval

Run `chapter-writer context` against the target document and the query that best expresses the intent:

```bash
chapter-writer context --workspace . --document docs/authentication.md --query "token renewal"
```

Retrieval is hybrid (lexical + graph + document scope). The result is context — matching nodes with their relationships and provenance — not a bare list of paragraphs. See `references/retrieval.md`.

### 4. Proposal

Before writing anything, state the exact operations you intend to perform:

- **add** — new paragraphs or artifacts, with document, content, and proposed relationships.
- **update** — node ids and the new content.
- **delete** — node ids to remove.
- **link** — pairs of `(source_id, target_id, type)` to add or remove.

The proposal is the plan; nothing is persisted yet. Keep every new paragraph a single semantic idea within the length limits (`references/writing-rules.md`).

### 5. Consistency validation

Run `chapter-writer validate` on the proposal. Validation runs deterministic rules plus LLM semantic analysis and reports failures and warnings. Fix any `validation_failed` issues before proceeding. See `references/validation.md`.

### 6. Impact analysis & questions

For every node the proposal would change or link, run `chapter-writer impact`:

```bash
chapter-writer impact --workspace . --node P-0003
```

Impact is computed deterministically by the graph engine and grouped into three categories (see below). The agent explains the semantic meaning of the impact but does not choose the initial impact set.

If anything is unresolved — a conflict, a missing decision, an ambiguity — register a **Question** node (`Q-0001`, …) and link it to the relevant nodes. Never invent an answer.

### 7. Commit

Persist the approved change with the CLI:

```bash
chapter-writer add --workspace . --document docs/authentication.md ...
chapter-writer update --workspace . ...
chapter-writer delete --workspace . ...
chapter-writer link --workspace . ...
```

Then re-run `chapter-writer validate` to confirm the workspace is consistent after the commit. Report the structured result.

## Operation input contract

An operation is expressed as a JSON request:

```json
{
  "operation": "add",
  "workspace": "/path/to/workspace",
  "document": "docs/authentication.md",
  "content": "Add a description of token renewal.",
  "target_nodes": [],
  "options": {"dry_run": false}
}
```

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `operation` | string | yes | `add` \| `update` \| `delete` \| `link`. |
| `workspace` | string | yes | Absolute path to the workspace root. |
| `document` | string | yes | Workspace-relative path of the target document. |
| `content` | string | no | The content or instruction for the operation. |
| `target_nodes` | string[] | no | Node ids the operation targets (update, delete, or link). Defaults to `[]`. |
| `options` | object | no | Extra flags; `options.dry_run` (`false`) computes and reports the effect without persisting. |

## Operation result contract

An operation returns a structured result:

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
  "impact": {
    "required_review": [],
    "recommended_review": [],
    "optional_review": []
  },
  "questions": [],
  "validation": {"valid": true, "warnings": []}
}
```

| Field | Meaning |
| --- | --- |
| `status` | One of the five statuses below. |
| `operation` | Echoes the requested operation. |
| `document` | The target document path. |
| `summary` | One-line human-readable description of what happened. |
| `nodes_created` / `nodes_modified` / `nodes_deleted` | Node ids affected, by kind of change. |
| `relations_created` | Relationship ids created. |
| `impact` | Impact buckets computed by the graph engine (see below). |
| `questions` | Question node ids (or inline questions) raised by the operation. |
| `validation` | `valid` boolean plus `warnings`; mirrors `chapter-writer validate`. |

The exact shapes are validated by `schemas/operation.schema.json`.

## Operation statuses

| Status | Meaning |
| --- | --- |
| `completed` | The operation succeeded and the workspace is consistent. |
| `needs_input` | The operation cannot proceed without an answer from the user; one or more Questions are open. |
| `validation_failed` | Deterministic or semantic validation rejected the change. |
| `conflict` | The change contradicts existing content or another in-flight change. |
| `error` | An unexpected failure (bad path, unreadable file, backend error). |

Report the status verbatim. Never report `completed` when validation failed or questions remain.

## Impact categories

Impact is computed deterministically by the graph engine from the relationships of the changed nodes. The mapping is fixed:

| Category | Relationship types |
| --- | --- |
| `required_review` | `depends_on`, `implements`, `contradicts` |
| `recommended_review` | `refines`, `supports`, `references`, `derived_from`, `contains` |
| `optional_review` | `supersedes`, `illustrates` |

The agent explains the semantic meaning of the impact but does not choose the initial impact set.
