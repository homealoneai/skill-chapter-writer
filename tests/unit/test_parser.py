"""Unit tests for the Markdown parser and markers."""

from chapter_writer.content import (
    check_length,
    extract_node_markers,
    parse_markdown,
    render_with_markers,
    strip_markers,
    word_count,
)


def test_parse_kinds():
    text = "# T\n\npara\n\n```python\nx\n```\n\n| a | b |\n|---|---|\n\n![x](y.png)\n"
    kinds = {u.kind for u in parse_markdown(text).units}
    assert {"heading", "paragraph", "code", "table", "image"} <= kinds


def test_parse_diagram_kind():
    text = "```mermaid\ngraph TD\n A-->B\n```\n"
    units = parse_markdown(text).units
    assert units[0].kind == "diagram"


def test_preserves_unknown_syntax():
    text = "# T\n\n[link](x) and **bold** and <custom-tag/>\n"
    parsed = parse_markdown(text)
    raw = next(u.raw for u in parsed.units if u.kind == "paragraph")
    assert "<custom-tag/>" in raw


def test_marker_roundtrip_positions_stable():
    text = "# T\n\npara one\n\npara two\n"
    marked = render_with_markers(text, "DOC:d.md", {1: "P-0001", 2: "P-0002"})
    markers = extract_node_markers(marked)
    assert markers == {1: "P-0001", 2: "P-0002"}
    assert strip_markers(marked) == text


def test_word_count_and_length():
    assert word_count("one two three") == 3
    n, too_long = check_length("x " * 130, 120)
    assert too_long and n == 130
