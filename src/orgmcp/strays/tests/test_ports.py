"""``FsMtimeReader``: the modification time of a file or directory on disk, None for what cannot be statted."""

from __future__ import annotations

import os
from pathlib import Path

from orgmcp.strays._ports import FsMtimeReader, MtimeReader


def test_it_is_an_mtime_reader() -> None:
    assert isinstance(FsMtimeReader(), MtimeReader)


def test_a_file_and_a_directory_have_their_mtime(tmp_path: Path) -> None:
    (tmp_path / "f").write_text("x")
    (tmp_path / "d").mkdir()
    os.utime(tmp_path / "f", (1234.5, 1234.5))
    os.utime(tmp_path / "d", (99.0, 99.0))
    reader = FsMtimeReader()
    assert reader.mtime(tmp_path / "f") == 1234.5 and reader.mtime(tmp_path / "d") == 99.0


def test_a_path_that_is_not_there_has_none(tmp_path: Path) -> None:
    assert FsMtimeReader().mtime(tmp_path / "missing") is None


def test_a_path_below_a_file_has_none(tmp_path: Path) -> None:
    (tmp_path / "f").write_text("x")
    assert FsMtimeReader().mtime(tmp_path / "f" / "child") is None
