"""Contract of ``OrgDocumentStore``: the file ORG.md and its in-memory fake."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.settings import OrgDocumentStore
from hirearchy.settings.testing import IMPLEMENTATIONS, DocumentHarness

TEXT = "---\nevents: false\nmax_depth: 3\n---\n# Mission é ✓\n\n  two trailing spaces  \n\n1. Rule.\n"


@pytest.fixture(params=IMPLEMENTATIONS[OrgDocumentStore], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> DocumentHarness:
    made = cast(Callable[[Path], DocumentHarness], request.param)(tmp_path)
    assert isinstance(made.store, OrgDocumentStore)
    return made


def test_a_store_without_a_document_does_not_exist(h: DocumentHarness) -> None:
    assert h.store.exists() is False
    assert h.stored() is None


def test_reading_a_document_that_does_not_exist_is_an_error(h: DocumentHarness) -> None:
    with pytest.raises(FileNotFoundError):
        h.store.read_raw()


def test_what_was_written_is_read_back_exactly(h: DocumentHarness) -> None:
    h.store.write_raw(TEXT)
    assert h.store.exists() is True
    assert h.store.read_raw() == TEXT
    assert h.stored() == TEXT


@pytest.mark.parametrize("text", ["", "\n", "no newline at the end", "a\n\n\n", "   \n  indented\n", "---\n---\n", "é\n✓\n日本\n"])
def test_the_text_is_not_touched(h: DocumentHarness, text: str) -> None:
    h.store.write_raw(text)
    assert h.store.read_raw() == text and h.stored() == text


def test_a_write_replaces_the_whole_document(h: DocumentHarness) -> None:
    h.store.write_raw(TEXT)
    h.store.write_raw("short\n")
    assert h.store.read_raw() == "short\n"
    assert h.stored() == "short\n"


def test_a_document_that_is_there_is_read(h: DocumentHarness) -> None:
    h.put(TEXT)
    assert h.store.exists() is True
    assert h.store.read_raw() == TEXT


def test_a_changed_document_is_read_again(h: DocumentHarness) -> None:
    h.store.write_raw("one\n")
    h.put("two\n")
    assert h.store.read_raw() == "two\n"
