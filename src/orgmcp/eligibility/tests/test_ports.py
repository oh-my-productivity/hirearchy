"""``FsDirectoryProbe`` and ``FsLedgerShape``: what the decorator and the failure counter ask of the disk."""

from __future__ import annotations

import os
from pathlib import Path

from orgmcp.eligibility._ports import DirectoryProbe, FsDirectoryProbe, FsLedgerShape, LedgerShape
from orgmcp.kernel import OrgPaths

from ._support import RED

pytestmark = RED


def test_the_probe_is_a_directory_probe() -> None:
    assert isinstance(FsDirectoryProbe(OrgPaths(Path("/nowhere"))), DirectoryProbe)


def test_a_file_has_its_mtime_in_nanoseconds(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    (tmp_path / "ceo" / ".paused").write_text("x")
    os.utime(tmp_path / "ceo" / ".paused", ns=(5, 123_456_789))
    assert FsDirectoryProbe(OrgPaths(tmp_path)).mtime("ceo", ".paused") == 123_456_789


def test_a_file_that_is_not_there_is_minus_one(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    probe = FsDirectoryProbe(OrgPaths(tmp_path))
    assert probe.mtime("ceo", ".paused") == -1 and probe.mtime("ghost", ".paused") == -1


def test_the_flag_of_root_is_in_the_organization_itself(tmp_path: Path) -> None:
    (tmp_path / ".paused").write_text("x")
    os.utime(tmp_path / ".paused", ns=(5, 77))
    assert FsDirectoryProbe(OrgPaths(tmp_path)).mtime("root", ".paused") == 77


def test_the_directory_itself_for_an_empty_name(tmp_path: Path) -> None:
    (tmp_path / "ceo").mkdir()
    os.utime(tmp_path / "ceo", ns=(5, 99))
    assert FsDirectoryProbe(OrgPaths(tmp_path)).mtime("ceo", "") == 99


def test_the_shape_is_a_ledger_shape() -> None:
    assert isinstance(FsLedgerShape(OrgPaths(Path("/nowhere"))), LedgerShape)


def write(tmp_path: Path, raw: str) -> FsLedgerShape:
    (tmp_path / ".runtime").mkdir()
    (tmp_path / ".runtime" / "failures.json").write_text(raw)
    return FsLedgerShape(OrgPaths(tmp_path))


def test_json_that_is_not_an_object_is_damaged(tmp_path: Path) -> None:
    for raw in ("[]", "42", '"x"', "null", "true"):
        assert write(tmp_path, raw).damaged("failures") is True, raw


def test_an_object_is_sound(tmp_path: Path) -> None:
    assert write(tmp_path, '{"a": []}').damaged("failures") is False


def test_what_cannot_be_parsed_is_not_damaged_but_empty(tmp_path: Path) -> None:
    assert write(tmp_path, "{ broken").damaged("failures") is False


def test_a_ledger_that_is_not_there_is_not_damaged(tmp_path: Path) -> None:
    assert FsLedgerShape(OrgPaths(tmp_path)).damaged("failures") is False
