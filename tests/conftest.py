"""Pytest fixtures (self-contained; no cross-directory imports needed)."""

import os

import pytest

from chapter_writer.engine import Engine

SAMPLE_DOC = """---
title: Architecture
purpose: Describe the system architecture.
---

# Architecture

The system is composed of three layers.

The API layer exposes HTTP endpoints.

The data layer persists records.

```python
print("hello")
```

```mermaid
graph LR
  A-->B
```

| Layer | Role |
|---|---|
| API | Entry point |

![diagram](assets/arch.png)
"""


def write_doc(root: str, relpath: str, text: str) -> str:
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path) or root, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return relpath


@pytest.fixture
def engine(tmp_path):
    eng = Engine.open(str(tmp_path))
    eng.init(name="Test Workspace")
    yield eng
    eng.ws.close()


@pytest.fixture
def make_doc():
    return write_doc


@pytest.fixture
def sample_doc():
    return SAMPLE_DOC


@pytest.fixture
def seeded_engine(engine, tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "assets"), exist_ok=True)
    with open(os.path.join(root, "assets", "arch.png"), "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\nfake-png-bytes")
    write_doc(root, "docs/architecture.md", SAMPLE_DOC)
    engine.index()
    return engine
