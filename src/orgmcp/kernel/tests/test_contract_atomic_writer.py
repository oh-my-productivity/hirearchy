"""Contract of ``AtomicWriter``: what a reader sees after ``write``. Filesystem-only facts (temp file names, cleanup after a
failure) are in ``test_system.py``."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import AtomicWriter
from orgmcp.kernel.testing import IMPLEMENTATIONS, WriterHarness


@pytest.fixture(params=IMPLEMENTATIONS[AtomicWriter], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> WriterHarness:
    made = cast(Callable[[Path], WriterHarness], request.param)(tmp_path)
    assert isinstance(made.writer, AtomicWriter)
    return made


def test_what_was_written_is_read_back(h: WriterHarness) -> None:
    h.writer.write(h.base / "a.txt", "hello\n")
    assert h.read(h.base / "a.txt") == "hello\n"


def test_a_path_never_written_reads_as_nothing(h: WriterHarness) -> None:
    h.writer.write(h.base / "other.txt", "x")
    assert h.read(h.base / "nope.txt") is None


def test_missing_parent_directories_are_created(h: WriterHarness) -> None:
    h.writer.write(h.base / "a" / "b" / "c.txt", "deep")
    assert h.read(h.base / "a" / "b" / "c.txt") == "deep"


def test_a_second_write_replaces_the_first_completely(h: WriterHarness) -> None:
    h.writer.write(h.base / "a.txt", "a long first text\nwith lines\n")
    h.writer.write(h.base / "a.txt", "short")
    assert h.read(h.base / "a.txt") == "short"


def test_the_text_is_stored_exactly(h: WriterHarness) -> None:
    text = "é ✓ 日本\r\nsecond\tline\n\n\ntrailing  "
    h.writer.write(h.base / "t.txt", text)
    assert h.read(h.base / "t.txt") == text


def test_an_empty_text_is_a_file_not_a_missing_one(h: WriterHarness) -> None:
    h.writer.write(h.base / "empty.txt", "")
    assert h.read(h.base / "empty.txt") == ""


def test_files_do_not_affect_each_other(h: WriterHarness) -> None:
    h.writer.write(h.base / "one.txt", "1")
    h.writer.write(h.base / "two.txt", "2")
    h.writer.write(h.base / "one.txt", "11")
    assert (h.read(h.base / "one.txt"), h.read(h.base / "two.txt")) == ("11", "2")
