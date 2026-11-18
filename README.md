# chapter-writer

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python >= 3.10](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](pyproject.toml)
[![release](https://img.shields.io/github/v/release/homealoneai/skill-chapter-writer)](https://github.com/homealoneai/skill-chapter-writer/releases)

Graph-based Markdown authoring skill. `chapter-writer` keeps a persistent per-workspace knowledge graph that acts as a semantic index and context-management layer for your Markdown documents.

The Markdown files remain the human-readable source of truth. A per-workspace graph (`.graph-md/`) tracks paragraphs, artifacts, questions, and decisions plus the relationships between them, so an agent can retrieve the exact context for a change, catch contradictions, and measure the impact of an edit before making it.

## Features

- **Persistent knowledge graph** per workspace, stored under `.graph-md/`.
- **Hybrid retrieval** — TF-IDF lexical search, graph traversal, and document-scope scoring, merged into one ranking.
- **Stable, allocation-based node ids** (`P-0001`, `IMG-0001`, `FLOW-0001`, …) that survive edits and moves.
- **Typed, directed relationships** (`depends_on`, `contradicts`, `supersedes`, …) with deterministic impact analysis.
- **Deterministic validation plus LLM semantic review** — structural rules enforced by code, semantics judged by the model.
- **First-class artifacts** — images, diagrams, tables, and code blocks are graph nodes with purpose and relationships.
- **Machine-readable `--json` output** for every command.

## Install

Requires Python >= 3.10.

```bash
pip install -e .
```

This installs the `chapter-writer` CLI (entry point `chapter_writer.cli:main`). Development dependencies are available with `pip install -e ".[dev]"`.

## Quickstart

```bash
# Initialize a workspace (creates .graph-md/config.yaml and the graph)
chapter-writer init --workspace .

# Build/update the index from all Markdown files in scope
chapter-writer index --workspace .

# Search for nodes
chapter-writer search --workspace . --query "token expiration"

# Retrieve context for a specific document and question
chapter-writer context --workspace . --document docs/authentication.md --query "token renewal"

# Add content (and later: update, delete, link)
chapter-writer add --workspace . --document docs/authentication.md --json

# Measure the impact of changing a node
chapter-writer impact --workspace . --node P-0003

# Validate the workspace
chapter-writer validate --workspace .
```

The full command set is `chapter-writer init|index|search|context|add|update|delete|link|question|decision|impact|validate|render|status`. Common flags are `--workspace <root>` (defaults to `.`) and `--json` for machine-readable output.

## Repository layout

```
.
├── SKILL.md                     # Agent-facing skill instructions
├── README.md                    # This file
├── pyproject.toml               # Package metadata and CLI entry point
├── requirements.txt             # Runtime and dev dependencies
├── references/                  # Detailed contract documentation
│   ├── workflow.md              #   Seven-step workflow + operation JSON contract
│   ├── content-model.md         #   Node types, properties, ids, markers
│   ├── relationship-types.md    #   10 relationship types and direction
│   ├── writing-rules.md         #   10 content atomicity rules + length guidance
│   ├── retrieval.md             #   Hybrid retrieval model
│   ├── validation.md            #   Deterministic + LLM validation rules
│   └── artifact-handling.md     #   Images, diagrams, tables, code blocks
├── schemas/                     # JSON Schemas (draft-07)
│   ├── workspace.schema.json    #   Workspace configuration
│   ├── node.schema.json         #   Graph node
│   ├── relation.schema.json     #   Relationship
│   └── operation.schema.json    #   Operation request/result
├── templates/
│   ├── workspace.yaml           #   Default configuration (verbatim)
│   └── document.md              #   Example document with markers
├── src/chapter_writer/          # Python implementation
└── tests/                       # Tests
```

## Config reference

Configuration lives at `.graph-md/config.yaml`. The default is `templates/workspace.yaml` and its shape is validated by `schemas/workspace.schema.json`.

| Section | Key | Default | Meaning |
| --- | --- | --- | --- |
| top-level | `version` | `1` | Config schema version. |
| `workspace` | `id`, `name`, `root` | `""`, `Documentation Workspace`, `.` | Workspace identity and root. |
| `storage.graph` | `provider`, `path` | `ladybugdb`, `.graph-md/graph.db` | Graph storage backend. |
| `storage.index` | `path` | `.graph-md/index` | Lexical index location. |
| `retrieval.lexical` | `enabled`, `algorithm`, `ngram_range` | `true`, `tfidf`, `[1, 2]` | TF-IDF lexical retrieval. |
| `retrieval.graph` | `enabled`, `default_depth`, `maximum_depth` | `true`, `1`, `3` | Graph traversal bounds. |
| `retrieval.hybrid` | `lexical_weight`, `graph_weight`, `document_scope_weight` | `0.45`, `0.35`, `0.20` | Hybrid ranking weights. |
| `authoring` | `maximum_paragraph_words`, `recommended_paragraph_words`, `require_relationships`, `allow_unlinked_content` | `120`, `80`, `true`, `false` | Content atomicity policy. |
| `documents` | `include`, `exclude` | `["**/*.md"]`, `[".graph-md/**", "node_modules/**", ".git/**"]` | Which files are indexed. |

## Security boundary

The workspace root — the directory containing `.graph-md/config.yaml` — is the filesystem boundary. All document and artifact paths are resolved relative to it, and the graph only indexes files under it. The CLI never reads or writes outside the workspace root. The graph directory (`.graph-md/`) is managed exclusively by the CLI; agents and humans must not edit it by hand.

## Testing

Tests live in `tests/` and run with `pytest` (`pip install -e ".[dev]"` then `pytest`). The documentation under `references/`, `schemas/`, and `templates/` is the source of truth for the contract; the code under `src/` implements it.

## Reference files

| File | Purpose |
| --- | --- |
| [`references/workflow.md`](references/workflow.md) | The seven-step workflow and the operation JSON contract. |
| [`references/content-model.md`](references/content-model.md) | Node types, properties, stable ids, and HTML markers. |
| [`references/relationship-types.md`](references/relationship-types.md) | The 10 relationship types and their direction. |
| [`references/writing-rules.md`](references/writing-rules.md) | The 10 content atomicity rules and length guidance. |
| [`references/retrieval.md`](references/retrieval.md) | Hybrid retrieval (TF-IDF + graph + document scope). |
| [`references/validation.md`](references/validation.md) | Deterministic and LLM validation rules. |
| [`references/artifact-handling.md`](references/artifact-handling.md) | Images, diagrams, tables, and code blocks. |
| [`schemas/workspace.schema.json`](schemas/workspace.schema.json) | Workspace configuration schema. |
| [`schemas/node.schema.json`](schemas/node.schema.json) | Graph node schema. |
| [`schemas/relation.schema.json`](schemas/relation.schema.json) | Relationship schema. |
| [`schemas/operation.schema.json`](schemas/operation.schema.json) | Operation request/result schema. |
