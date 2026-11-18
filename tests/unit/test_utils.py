"""Unit tests for utilities."""

import os

import pytest

from chapter_writer.utils import (
    allocate_id,
    content_hash,
    file_hash,
    is_document_id,
    is_valid_node_id,
    normalize_relpath,
)


def test_normalize_relpath():
    assert normalize_relpath("./docs//a.md") == "docs/a.md"


def test_normalize_rejects_escape():
    with pytest.raises(ValueError):
        normalize_relpath("../a.md")


def test_normalize_rejects_absolute():
    with pytest.raises(ValueError):
        normalize_relpath("/etc/passwd")


def test_allocate_id_never_reuses():
    assert allocate_id("P", {"P-0001", "P-0002"}) == "P-0003"


def test_allocate_id_skips_gaps():
    assert allocate_id("P", {"P-0001"}, start=1) == "P-0002"


def test_id_validators():
    assert is_valid_node_id("P-0001")
    assert is_valid_node_id("IMG-0001")
    assert not is_valid_node_id("P-1")
    assert is_document_id("DOC:docs/a.md")
    assert not is_document_id("P-0001")


def test_hashes(tmp_path):
    assert content_hash("x") == content_hash("x")
    assert content_hash("x") != content_hash("y")
    p = tmp_path / "f.txt"
    p.write_text("hello")
    assert file_hash(str(p)) == file_hash(str(p))
