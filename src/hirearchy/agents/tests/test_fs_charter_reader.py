"""``FsCharterReader`` over ``AGENT.md`` and ``MEMORY.md``."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.agents import CharterReader
from hirearchy.agents._charters import FsCharterReader
from hirearchy.kernel import OrgPaths


def test_it_is_a_charter_reader(tmp_path: Path) -> None:
    assert isinstance(FsCharterReader(OrgPaths(tmp_path)), CharterReader)


def test_the_files_are_read_as_utf_8_with_universal_newlines(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    (tmp_path / "ceo" / "AGENT.md").write_bytes("---\r\nrole: É\r\n---\r\nline one\r\nline two\r\n".encode())
    (tmp_path / "ceo" / "MEMORY.md").write_bytes("a\r\nb\r\n".encode())
    reader = FsCharterReader(OrgPaths(tmp_path))
    assert reader.charter("ceo") == ({"role": "É"}, "line one\nline two")
    assert reader.memory("ceo") == "a\nb\n"


def test_a_charter_that_is_not_utf_8_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    (tmp_path / "ceo" / "AGENT.md").write_bytes(b"---\nrole: \xff\xfe\n---\n")
    with pytest.raises(UnicodeDecodeError):
        FsCharterReader(OrgPaths(tmp_path)).charter("ceo")


def test_roots_charter_is_fixed_and_the_disk_is_not_looked_at(tmp_path: Path) -> None:
    assert FsCharterReader(OrgPaths(tmp_path / "nowhere")).charter("root") == ({"role": "human (root of the organization)"}, "")


def test_the_fixed_charter_is_a_new_mapping_each_time(tmp_path: Path) -> None:
    reader = FsCharterReader(OrgPaths(tmp_path))
    reader.charter("root")[0]["role"] = "changed"
    assert reader.charter("root")[0]["role"] == "human (root of the organization)"
