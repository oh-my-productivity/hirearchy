"""``FsOrgDocumentStamp``: ``(mtime_ns, size)`` of ORG.md."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from orgmcp.kernel import OrgPaths
from orgmcp.settings._stamp import FsOrgDocumentStamp, OrgDocumentStamp


def test_it_is_a_stamp(tmp_path: Path) -> None:
    assert isinstance(FsOrgDocumentStamp(OrgPaths(tmp_path)), OrgDocumentStamp)


def test_the_stamp_is_the_modification_time_and_the_size(tmp_path: Path) -> None:
    path = tmp_path / "ORG.md"
    path.write_text("12345", encoding="utf-8")
    os.utime(path, ns=(1_000_000_000, 1_700_000_000_123_456_789))
    assert FsOrgDocumentStamp(OrgPaths(tmp_path)).stamp() == (1_700_000_000_123_456_789, 5)


def test_the_stamp_follows_the_file(tmp_path: Path) -> None:
    path = tmp_path / "ORG.md"
    stamps = FsOrgDocumentStamp(OrgPaths(tmp_path))
    path.write_text("abc", encoding="utf-8")
    os.utime(path, ns=(1, 1_000))
    first = stamps.stamp()
    os.utime(path, ns=(1, 2_000))
    assert stamps.stamp() != first
    path.write_text("abcd", encoding="utf-8")
    os.utime(path, ns=(1, 2_000))
    assert stamps.stamp() == (2_000, 4)


def test_a_missing_document_is_an_os_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        FsOrgDocumentStamp(OrgPaths(tmp_path)).stamp()
