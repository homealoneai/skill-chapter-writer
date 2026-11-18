# Changelog

All notable changes to `chapter-writer` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-17

### Added

- Initial MVP of the `chapter-writer` skill: a persistent per-workspace knowledge
  graph that acts as a semantic index and context-management layer for Markdown.
- Workspace model with `init`, configurable storage/retrieval/authoring settings,
  and a `.graph-md/` metadata directory.
- Graph storage behind a `GraphStore` interface: LadybugDB backend (primary) and a
  pure-Python in-memory fallback.
- Markdown parser and indexing/sync pipeline that preserves unknown syntax and
  inserts invisible `<!-- chapter-writer:node … -->` markers.
- Stable, allocation-based node ids (`P-0001`, `IMG-0001`, `FLOW-0001`,
  `TABLE-0001`, `CODE-0001`, `Q-0001`, `DEC-0001`) and `DOC:<path>` document ids.
- Typed, directed relationships: `depends_on`, `refines`, `supports`, `implements`,
  `references`, `contradicts`, `supersedes`, `derived_from`, `illustrates`,
  `contains`.
- Hybrid retrieval: TF-IDF lexical search + deterministic graph traversal +
  document-scope scoring, with per-result `retrieval_reasons`.
- Seven-step authoring workflow and structured operation contract with JSON
  results (`completed | needs_input | validation_failed | conflict | error`).
- Deterministic impact analysis categorized into `required_review`,
  `recommended_review`, and `optional_review`.
- Validation: graph integrity, prohibited cycles, paragraph atomicity/length,
  missing targets, and unlinked-content warnings.
- Artifact handling for images, Mermaid/PlantUML diagrams, tables, and code
  blocks, preserving the original representation.
- JSON-capable CLI: `init`, `index`, `search`, `context`, `add`, `update`,
  `delete`, `link`, `question`, `decision`, `impact`, `validate`, `render`,
  `status`.
- Documentation: `SKILL.md`, `README.md`, seven reference documents, JSON
  Schemas, and templates.
- 56 automated tests covering graph integrity, retrieval, indexing/sync,
  authoring, impact analysis, artifacts, questions/decisions, and workspace
  isolation.
- Example workspace in [`examples/independencia-brasileira.md`](examples/independencia-brasileira.md).

[Unreleased]: https://github.com/homealoneai/skill-chapter-writer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/homealoneai/skill-chapter-writer/releases/tag/v0.1.0
