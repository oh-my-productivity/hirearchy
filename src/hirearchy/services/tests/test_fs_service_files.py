"""``OsServiceFiles``: the continuation reads the files of a retired copy exactly as they were written and never through a link (nothing is read
outside the organization because a link was put where a copy or a file should be)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.services._store import OsServiceFiles
from hirearchy.services.testing import fs_world

from ._support import answer, define, populated
from ._support import request as ask


def test_a_file_is_read_exactly_as_written(tmp_path: Path) -> None:
    text = "---\nversion: 2\n---\r\nTwo  spaces, ünïcode and a CRLF\r\nno trailing newline"
    (tmp_path / "SERVICE.md").write_bytes(text.encode("utf-8"))
    assert OsServiceFiles().read_text(tmp_path / "SERVICE.md") == text


def test_what_is_no_regular_file_is_no_text(tmp_path: Path) -> None:
    (tmp_path / "dir").mkdir()
    (tmp_path / "real.md").write_text("x", encoding="utf-8")
    (tmp_path / "link.md").symlink_to(tmp_path / "real.md")
    files = OsServiceFiles()
    assert [files.read_text(tmp_path / n) for n in ("missing.md", "dir", "link.md", "real.md/inside.md")] == [None, None, None, None]


def test_a_file_that_is_not_text_is_an_os_error(tmp_path: Path) -> None:
    (tmp_path / "SERVICE.md").write_bytes(b"\xff\xfe not text")
    with pytest.raises(OSError, match="not valid UTF-8"):
        OsServiceFiles().read_text(tmp_path / "SERVICE.md")


def test_what_is_no_directory_lists_nothing(tmp_path: Path) -> None:
    (tmp_path / "dir").mkdir()
    (tmp_path / "dir" / "b.md").write_text("b", encoding="utf-8")
    (tmp_path / "dir" / "a.md").write_text("a", encoding="utf-8")
    (tmp_path / "file.md").write_text("x", encoding="utf-8")
    (tmp_path / "link").symlink_to(tmp_path / "dir")
    files = OsServiceFiles()
    assert sorted(files.listdir(tmp_path / "dir")) == ["a.md", "b.md"]
    assert [files.listdir(tmp_path / n) for n in ("missing", "file.md", "link", "file.md/inside")] == [[], [], [], []]


def test_a_link_where_a_copy_or_a_file_should_be_is_not_followed(tmp_path: Path) -> None:
    """A copy that is a link to a directory outside the organization, and a ``SERVICE.md`` that is a link to a file outside it, are no copies."""
    outside = tmp_path / "outside"
    org = tmp_path / "org"
    org.mkdir()
    w = populated(fs_world(org))
    define(w)
    answer(w, ask(w))
    text = w.text("ceo/services/weekly-brief/SERVICE.md")
    assert text is not None
    (outside / "weekly-brief-20261018T100000000001").mkdir(parents=True)
    (outside / "weekly-brief-20261018T100000000001" / "SERVICE.md").write_text(text, encoding="utf-8")
    retired = org / "ceo" / "services" / ".retired"
    retired.mkdir(parents=True)
    (retired / "weekly-brief-20261018T100000000001").symlink_to(outside / "weekly-brief-20261018T100000000001")
    assert w.continued.continued("ceo", "weekly-brief") is None
    real = retired / "weekly-brief-20261018T100000000002"
    real.mkdir()
    (real / "SERVICE.md").symlink_to(outside / "weekly-brief-20261018T100000000001" / "SERVICE.md")
    assert w.continued.continued("ceo", "weekly-brief") is None
