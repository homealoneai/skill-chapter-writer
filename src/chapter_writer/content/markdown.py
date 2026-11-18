"""Round-trip Markdown parsing.

The parser identifies atomic units for indexing *without* rewriting the file.
Every unit keeps its exact source lines (``raw``), so indexing and marker
insertion preserve unknown Markdown syntax verbatim. ``chapter-writer`` HTML-comment
marker lines are treated as invisible metadata: they never become units and do
not consume ``position`` slots, so unit positions are stable between a marked
file and the same file with markers stripped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_FENCE_RE = re.compile(r"^(```|~~~)(.*)$")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:\-|]+\|?\s*$")
_IMAGE_RE = re.compile(r"^!\s*\[([^\]]*)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)\s*$")
_MARKER_RE = re.compile(r"^\s*<!--\s*chapter-writer:(node|document)\s+(\S+)\s*-->\s*$")
_LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
_BLOCKQUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
_HR_RE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
_FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$")

MERMAID_LANGS = {"mermaid", "mmd"}
PLANTUML_LANGS = {"plantuml", "puml"}

NODEABLE_KINDS = {"paragraph", "code", "table", "image", "diagram"}


@dataclass
class ParsedUnit:
    """One atomic unit recognized by the parser."""

    kind: str  # heading | paragraph | code | table | image | diagram | other
    text: str = ""  # searchable plain text
    raw: str = ""  # exact source lines
    heading: str = ""  # nearest enclosing heading text
    start_line: int = 0  # 1-based, inclusive
    end_line: int = 0  # 1-based, inclusive
    position: int = 0  # ordinal among non-marker units
    lang: str = ""
    meta: dict = field(default_factory=dict)


@dataclass
class ParseResult:
    title: str
    frontmatter: dict
    units: list[ParsedUnit]


def parse_markdown(text: str) -> ParseResult:
    """Parse Markdown text into a title, frontmatter, and ordered units."""
    lines = text.split("\n")
    frontmatter: dict = {}
    title = ""
    i = 0

    if lines and lines[0].strip() == "---":
        buf = []
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            buf.append(lines[i])
            i += 1
        if i < len(lines):
            i += 1  # consume closing ---
        frontmatter = _parse_frontmatter("\n".join(buf))
        title = frontmatter.get("title", "")

    units: list[ParsedUnit] = []
    current_heading = ""
    position = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if _MARKER_RE.match(line):
            i += 1  # invisible metadata
            continue

        fence = _FENCE_RE.match(line)
        if fence:
            lang = (fence.group(2) or "").strip()
            start = i
            buf = [line]
            i += 1
            while i < len(lines) and not _FENCE_RE.match(lines[i]):
                buf.append(lines[i])
                i += 1
            if i < len(lines):
                buf.append(lines[i])
                i += 1
            raw = "\n".join(buf)
            if lang.lower() in MERMAID_LANGS or lang.lower() in PLANTUML_LANGS:
                kind = "diagram"
            else:
                kind = "code"
            units.append(
                ParsedUnit(
                    kind=kind,
                    text=raw,
                    raw=raw,
                    heading=current_heading,
                    start_line=start + 1,
                    end_line=i,
                    position=position,
                    lang=lang,
                )
            )
            position += 1
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            htext = heading.group(2).strip()
            current_heading = htext
            if not title:
                title = htext
            units.append(
                ParsedUnit(
                    kind="heading",
                    text=htext,
                    raw=line,
                    heading=htext,
                    start_line=i + 1,
                    end_line=i + 1,
                    position=position,
                    meta={"level": len(heading.group(1))},
                )
            )
            position += 1
            i += 1
            continue

        image = _IMAGE_RE.match(stripped)
        if image:
            alt = image.group(1) or ""
            src = image.group(2) or ""
            units.append(
                ParsedUnit(
                    kind="image",
                    text=alt or src,
                    raw=line,
                    heading=current_heading,
                    start_line=i + 1,
                    end_line=i + 1,
                    position=position,
                    meta={"alt": alt, "src": src},
                )
            )
            position += 1
            i += 1
            continue

        if _TABLE_ROW_RE.match(stripped):
            start = i
            buf = [line]
            i += 1
            if i < len(lines) and _TABLE_SEP_RE.match(lines[i].strip()):
                buf.append(lines[i])
                i += 1
            while i < len(lines) and _TABLE_ROW_RE.match(lines[i].strip()):
                buf.append(lines[i])
                i += 1
            raw = "\n".join(buf)
            units.append(
                ParsedUnit(
                    kind="table",
                    text=_table_text(raw),
                    raw=raw,
                    heading=current_heading,
                    start_line=start + 1,
                    end_line=i,
                    position=position,
                )
            )
            position += 1
            continue

        start = i
        buf = []
        while i < len(lines) and lines[i].strip() and not _is_special_start(lines[i]):
            buf.append(lines[i])
            i += 1
        raw = "\n".join(buf)
        if raw.strip():
            units.append(
                ParsedUnit(
                    kind="paragraph",
                    text=_plain_text(raw),
                    raw=raw,
                    heading=current_heading,
                    start_line=start + 1,
                    end_line=i,
                    position=position,
                )
            )
            position += 1

    if not title:
        for u in units:
            if u.kind not in ("marker",) and u.text:
                title = u.text.splitlines()[0][:80]
                break

    return ParseResult(title=title, frontmatter=frontmatter, units=units)


def _is_special_start(line: str) -> bool:
    s = line.strip()
    return bool(
        _HEADING_RE.match(s)
        or _FENCE_RE.match(s)
        or _TABLE_ROW_RE.match(s)
        or _IMAGE_RE.match(s)
        or _MARKER_RE.match(line)
        or _HR_RE.match(s)
    )


def _plain_text(raw: str) -> str:
    out = []
    for line in raw.split("\n"):
        s = line.strip()
        bq = _BLOCKQUOTE_RE.match(s)
        if bq:
            s = bq.group(1).strip()
        lm = _LIST_RE.match(s)
        if lm:
            s = lm.group(3).strip()
        if s:
            out.append(s)
    return "\n".join(out).strip()


def _table_text(raw: str) -> str:
    cells = []
    for line in raw.split("\n"):
        if _TABLE_SEP_RE.match(line.strip()):
            continue
        parts = [c.strip() for c in line.strip().strip("|").split("|")]
        cells.extend(p for p in parts if p)
    return " ".join(cells)


def _parse_frontmatter(text: str) -> dict:
    out: dict = {}
    for line in text.split("\n"):
        m = _FRONTMATTER_KEY_RE.match(line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip("\"'")
    return out


# -- markers ---------------------------------------------------------------


def extract_node_markers(text: str) -> dict:
    """Return ``{unit_position: node_id}`` from ``chapter-writer:node`` markers.

    A marker is associated with the nodeable unit immediately preceding it, so
    positions are stable regardless of whether markers are present.
    """
    parsed = parse_markdown(text)
    lines = text.split("\n")
    markers: dict = {}
    for u in parsed.units:
        if u.kind not in NODEABLE_KINDS:
            continue
        next_idx = u.end_line  # 0-based index of the line right after the unit
        if next_idx < len(lines):
            m = _MARKER_RE.match(lines[next_idx])
            if m and m.group(1) == "node":
                markers[u.position] = m.group(2)
    return markers


def extract_document_id(text: str) -> str | None:
    """Return the ``DOC:...`` id from a ``chapter-writer:document`` marker, if any."""
    for line in text.split("\n"):
        m = _MARKER_RE.match(line)
        if m and m.group(1) == "document":
            return m.group(2)
    return None


def strip_markers(text: str) -> str:
    """Remove all ``chapter-writer:`` marker lines."""
    return "\n".join(l for l in text.split("\n") if not _MARKER_RE.match(l))


def render_with_markers(
    text: str,
    document_id: str,
    node_id_by_position: dict[int, str],
    *,
    title_line: int | None = None,
) -> str:
    """Insert invisible ``chapter-writer`` markers into ``text`` and return it.

    ``node_id_by_position`` maps a unit's ``position`` to its node id (positions
    are stable, so a clean text's positions match a marked text's positions).
    Markers are inserted bottom-up so line numbers never shift.
    """
    parsed = parse_markdown(text)
    lines = text.split("\n")

    if title_line is None:
        title_line = _document_marker_line(parsed, lines)

    insertions: list[tuple[int, str]] = []
    if document_id:
        insertions.append((title_line, f"<!-- chapter-writer:document {document_id} -->"))

    for u in parsed.units:
        if u.kind not in NODEABLE_KINDS:
            continue
        node_id = node_id_by_position.get(u.position)
        if node_id:
            insertions.append((u.end_line, f"<!-- chapter-writer:node {node_id} -->"))

    for line_no, marker in sorted(insertions, key=lambda x: -x[0]):
        idx = min(line_no, len(lines))
        lines.insert(idx, marker)

    return "\n".join(lines)


def _document_marker_line(parsed: ParseResult, lines: list[str]) -> int:
    for u in parsed.units:
        if u.kind == "heading":
            return u.end_line
    if lines and lines[0].strip() == "---":
        for idx, line in enumerate(lines):
            if idx > 0 and line.strip() == "---":
                return idx + 1
    return 1
