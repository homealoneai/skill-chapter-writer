"""Command-line interface for chapter-writer.

The CLI is harness-independent and JSON-friendly. Pass ``--json`` for machine
output; without it a concise human summary is printed. It never prompts
interactively.
"""

from __future__ import annotations

import argparse
import json
import sys

from .engine import Engine


def _emit(data, as_json: bool) -> int:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chapter-writer", description="Graph-based Markdown authoring.")
    sub = parser.add_subparsers(dest="command", required=True)

    def ws(p):
        p.add_argument("--workspace", default=".", help="workspace root (default: .)")
        p.add_argument("--json", action="store_true", help="emit JSON output")

    p = sub.add_parser("init", help="initialize a workspace")
    ws(p)
    p.add_argument("--name", default=None)

    p = sub.add_parser("index", help="index all Markdown documents")
    ws(p)
    p.add_argument("--no-write-markers", action="store_true")

    p = sub.add_parser("search", help="hybrid search")
    ws(p)
    p.add_argument("--query", required=True)
    p.add_argument("--document", default=None)
    p.add_argument("--top-k", type=int, default=10)

    p = sub.add_parser("context", help="retrieve context for a query")
    ws(p)
    p.add_argument("--query", required=True)
    p.add_argument("--document", default=None)
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--nodes", default=None, help="comma-separated explicit node ids")

    p = sub.add_parser("add", help="add a paragraph to a document")
    ws(p)
    p.add_argument("--document", required=True)
    p.add_argument("--content", required=True)
    p.add_argument("--heading", default="")
    p.add_argument("--relationships", default=None, help="JSON list of {target, type, description}")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("update", help="update a node's content")
    ws(p)
    p.add_argument("--document", required=True)
    p.add_argument("--node", required=True)
    p.add_argument("--content", required=True)
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("delete", help="delete a node")
    ws(p)
    p.add_argument("--document", required=True)
    p.add_argument("--node", required=True)
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("link", help="create a typed relationship")
    ws(p)
    p.add_argument("--source", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--type", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("question", help="register an unresolved question")
    ws(p)
    p.add_argument("--document", required=True)
    p.add_argument("--question", required=True)
    p.add_argument("--reason", default="")
    p.add_argument("--related", default="", help="comma-separated node ids")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("decision", help="register a confirmed decision")
    ws(p)
    p.add_argument("--document", required=True)
    p.add_argument("--decision", required=True)
    p.add_argument("--rationale", default="")
    p.add_argument("--source", default="")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("impact", help="calculate impact of a node")
    ws(p)
    p.add_argument("--node", required=True)
    p.add_argument("--depth", type=int, default=3)

    p = sub.add_parser("validate", help="validate the graph")
    ws(p)

    p = sub.add_parser("render", help="(re)write node markers by re-indexing")
    ws(p)

    p = sub.add_parser("status", help="workspace status")
    ws(p)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    as_json = getattr(args, "json", False)
    ws_arg = getattr(args, "workspace", ".")

    try:
        eng = Engine.open(ws_arg)
        cmd = args.command

        if cmd == "init":
            return _emit(eng.init(name=args.name), as_json)
        if cmd == "index":
            return _emit(eng.index(write_markers=not args.no_write_markers), as_json)
        if cmd == "search":
            return _emit(eng.search(args.query, document=args.document, top_k=args.top_k), as_json)
        if cmd == "context":
            explicit = [x for x in (args.nodes or "").split(",") if x]
            return _emit(
                eng.context(args.query, document=args.document, top_k=args.top_k, explicit_ids=explicit),
                as_json,
            )
        if cmd == "add":
            rels = json.loads(args.relationships) if args.relationships else []
            from .models import Operation
            return _emit(
                eng.run(
                    Operation(
                        operation="add", workspace=ws_arg, document=args.document,
                        content=args.content, options={"heading": args.heading, "dry_run": args.dry_run},
                        relationships=rels,
                    )
                ),
                as_json,
            )
        if cmd == "update":
            from .models import Operation
            return _emit(
                eng.run(
                    Operation(
                        operation="update", workspace=ws_arg, document=args.document,
                        node_id=args.node, content=args.content,
                        options={"dry_run": args.dry_run},
                    )
                ),
                as_json,
            )
        if cmd == "delete":
            from .models import Operation
            return _emit(
                eng.run(
                    Operation(
                        operation="delete", workspace=ws_arg, document=args.document,
                        node_id=args.node, options={"dry_run": args.dry_run},
                    )
                ),
                as_json,
            )
        if cmd == "link":
            return _emit(
                _link_via_engine(eng, ws_arg, args), as_json
            )
        if cmd == "question":
            from .models import Operation
            related = [x for x in (args.related or "").split(",") if x]
            return _emit(
                eng.run(
                    Operation(
                        operation="add_question", workspace=ws_arg, document=args.document,
                        content=args.question, target_nodes=related,
                        options={"reason": args.reason, "dry_run": args.dry_run},
                    )
                ),
                as_json,
            )
        if cmd == "decision":
            from .models import Operation
            return _emit(
                eng.run(
                    Operation(
                        operation="add_decision", workspace=ws_arg, document=args.document,
                        content=args.decision,
                        options={"rationale": args.rationale, "source": args.source, "dry_run": args.dry_run},
                    )
                ),
                as_json,
            )
        if cmd == "impact":
            return _emit(eng.impact(args.node, depth=args.depth), as_json)
        if cmd == "validate":
            return _emit(eng.validate(), as_json)
        if cmd == "render":
            return _emit(eng.index(write_markers=True), as_json)
        if cmd == "status":
            return _emit(eng.status(), as_json)

        return _emit({"status": "error", "summary": f"unknown command: {cmd}"}, as_json)
    except Exception as exc:  # pragma: no cover - top-level guard
        return _emit({"status": "error", "summary": str(exc)}, as_json)


def _link_via_engine(eng: Engine, ws_arg: str, args) -> dict:
    from .models import Operation

    return eng.run(
        Operation(
            operation="link", workspace=ws_arg, node_id=args.source,
            target_nodes=[args.target], options={"type": args.type, "description": args.description, "dry_run": args.dry_run},
        )
    )


if __name__ == "__main__":
    sys.exit(main())
