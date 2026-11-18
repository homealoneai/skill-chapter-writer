"""Paragraph atomicity helpers.

These provide *deterministic* checks and *suggestions*. The system never
auto-splits or auto-merges content: the LLM proposes such changes and provenance
is recorded, per the atomicity rules.
"""

from __future__ import annotations

import re

_WORD_RE = re.compile(r"\S+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(text or ""))


def check_length(text: str, maximum: int = 120) -> tuple[int, bool]:
    """Return ``(word_count, is_too_long)``."""
    n = word_count(text)
    return n, n > maximum


def suggest_splits(text: str, maximum: int = 120) -> list[str]:
    """Suggest sentence-boundary splits so each part stays under ``maximum``.

    This is a deterministic *suggestion* only; the caller (LLM/agent) is
    responsible for confirming splits and preserving meaning and provenance.
    """
    text = (text or "").strip()
    if word_count(text) <= maximum:
        return [text] if text else []

    sentences = [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]
    parts: list[str] = []
    current: list[str] = []
    current_words = 0
    for sentence in sentences:
        w = word_count(sentence)
        if current and current_words + w > maximum:
            parts.append(" ".join(current))
            current = [sentence]
            current_words = w
        else:
            current.append(sentence)
            current_words += w
    if current:
        parts.append(" ".join(current))
    return parts if parts else [text]
