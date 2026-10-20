"""Contract of ``OrgFileStore``: the files below the organization root as the guard sees them, on disk and in memory.

What holds only for the filesystem (symbolic links, invalid UTF-8, universal newlines, permissions, the atomic writer) is in
``test_fs_org_file_store.py``; what is only the fake's (its two trees) is in ``test_memory_org_file_store.py``."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orgmcp.orgfiles import OrgFileStore
from orgmcp.orgfiles.testing import IMPLEMENTATIONS, StoreHarness

from ._support import make_store


@pytest.fixture(params=IMPLEMENTATIONS[OrgFileStore], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> StoreHarness:
    made = make_store(request, tmp_path)
    assert isinstance(made.store, OrgFileStore)
    return made


# ------------------------------------------------------------------------------ resolve


def test_an_absolute_path_is_kept(h: StoreHarness) -> None:
    assert h.store.resolve(h.root / "ceo" / "work" / "x.md") == h.root / "ceo" / "work" / "x.md"
    assert h.store.resolve(h.outside / "a") == h.outside / "a"


def test_a_relative_path_is_relative_to_the_organization_root(h: StoreHarness) -> None:
    assert h.store.resolve(Path("ceo/work/x.md")) == h.root / "ceo" / "work" / "x.md"
    assert h.store.resolve(Path(".")) == h.root


def test_dots_are_resolved_before_the_path_is_compared(h: StoreHarness) -> None:
    assert h.store.resolve(h.root / "ceo" / ".." / "ops" / "." / "x") == h.root / "ops" / "x"
    assert h.store.resolve(Path("../outside.md")) == h.root.parent / "outside.md"
    assert h.store.resolve(h.root / ".." / ".." / "..").is_absolute()


def test_a_path_that_does_not_exist_resolves_too(h: StoreHarness) -> None:
    assert h.store.resolve(h.root / "nothing" / "here" / "yet.md") == h.root / "nothing" / "here" / "yet.md"


# ------------------------------------------------------------------------------ kind and entries


def test_kind_tells_directories_files_and_what_is_not_there(h: StoreHarness) -> None:
    h.put(h.root / "a" / "f.md", "x")
    assert h.store.kind(h.root / "a") == "dir"
    assert h.store.kind(h.root / "a" / "f.md") == "file"
    assert h.store.kind(h.root / "a" / "nope.md") == "missing"
    assert h.store.kind(h.root / "nope" / "deeper.md") == "missing"
    assert h.store.kind(h.root) == "dir"


def test_a_path_below_a_file_is_missing(h: StoreHarness) -> None:
    h.put(h.root / "f.md", "x")
    assert h.store.kind(h.root / "f.md" / "below") == "missing"


def test_kind_works_outside_the_organization_too(h: StoreHarness) -> None:
    h.put(h.outside / "ws" / "f.md", "x")
    assert (h.store.kind(h.outside / "ws"), h.store.kind(h.outside / "ws" / "f.md"), h.store.kind(h.outside / "x")) == ("dir", "file", "missing")


def test_entries_are_the_names_in_a_directory_hidden_ones_included(h: StoreHarness) -> None:
    h.put(h.root / "d" / "b.md", "1")
    h.put(h.root / "d" / "A.md", "2")
    h.put(h.root / "d" / ".hidden", "3")
    h.put_dir(h.root / "d" / "sub")
    assert sorted(h.store.entries(h.root / "d")) == [".hidden", "A.md", "b.md", "sub"]


def test_entries_of_an_empty_a_missing_or_no_directory_are_empty(h: StoreHarness) -> None:
    h.put_dir(h.root / "empty")
    h.put(h.root / "f.md", "x")
    assert h.store.entries(h.root / "empty") == []
    assert h.store.entries(h.root / "nope") == []
    assert h.store.entries(h.root / "f.md") == []


def test_entries_keep_the_spelling_of_the_names(h: StoreHarness) -> None:
    h.put(h.root / "d" / "Plan.md", "x")
    assert h.store.entries(h.root / "d") == ["Plan.md"]


# ------------------------------------------------------------------------------ read_text


def test_a_file_reads_back_as_it_was_written(h: StoreHarness) -> None:
    h.put(h.root / "f.md", "héllo — 世界\nsecond line\n")
    assert h.store.read_text(h.root / "f.md") == "héllo — 世界\nsecond line\n"
    assert h.store.read_text(h.root / "f.md", "replace") == "héllo — 世界\nsecond line\n"


def test_an_empty_file_reads_as_the_empty_text(h: StoreHarness) -> None:
    h.put(h.root / "e.md", "")
    assert h.store.read_text(h.root / "e.md") == ""


def test_reading_a_missing_file_is_file_not_found(h: StoreHarness) -> None:
    with pytest.raises(FileNotFoundError):
        h.store.read_text(h.root / "nope.md")


def test_reading_a_directory_is_an_error_of_the_operating_system(h: StoreHarness) -> None:
    h.put_dir(h.root / "d")
    with pytest.raises(IsADirectoryError):
        h.store.read_text(h.root / "d")


# ------------------------------------------------------------------------------ modified


def test_modified_is_an_aware_utc_time(h: StoreHarness) -> None:
    h.put(h.root / "f.md", "x")
    h.touch(h.root / "f.md", datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc))
    modified = h.store.modified(h.root / "f.md")
    assert modified.utcoffset() == timedelta(0)
    assert abs((modified - datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)).total_seconds()) < 1


def test_modified_works_for_a_directory(h: StoreHarness) -> None:
    h.put_dir(h.root / "d")
    h.touch(h.root / "d", datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc))
    assert abs((h.store.modified(h.root / "d") - datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)).total_seconds()) < 1


def test_a_write_is_a_change_of_the_modification_time(h: StoreHarness) -> None:
    h.put(h.root / "f.md", "old")
    h.touch(h.root / "f.md", datetime(2020, 1, 1, tzinfo=timezone.utc))
    h.store.write_text(h.root / "f.md", "new")
    assert h.store.modified(h.root / "f.md") > datetime(2020, 1, 2, tzinfo=timezone.utc)


def test_the_modification_time_of_a_missing_path_is_file_not_found(h: StoreHarness) -> None:
    with pytest.raises(FileNotFoundError):
        h.store.modified(h.root / "nope")


# ------------------------------------------------------------------------------ write_text


def test_a_write_makes_the_file_and_the_directories_above_it(h: StoreHarness) -> None:
    h.store.write_text(h.root / "ceo" / "work" / "deep" / "n.md", "hello\n")
    assert h.read(h.root / "ceo" / "work" / "deep" / "n.md") == "hello\n"
    assert h.store.kind(h.root / "ceo" / "work" / "deep") == "dir"


def test_a_write_replaces_the_whole_file(h: StoreHarness) -> None:
    h.put(h.root / "f.md", "a much longer old text")
    h.store.write_text(h.root / "f.md", "new")
    assert h.read(h.root / "f.md") == "new"
    h.store.write_text(h.root / "f.md", "")
    assert h.read(h.root / "f.md") == ""


def test_the_text_is_written_exactly_and_as_utf_8(h: StoreHarness) -> None:
    text = "  leading and trailing blanks \n\n\ntabs\tand — dashes 世界\n"
    h.store.write_text(h.root / "f.md", text)
    assert h.read(h.root / "f.md") == text
    assert h.store.read_text(h.root / "f.md") == text


def test_a_write_leaves_no_other_file_behind(h: StoreHarness) -> None:
    h.store.write_text(h.root / "d" / "f.md", "x")
    h.store.write_text(h.root / "d" / "f.md", "y")
    assert h.store.entries(h.root / "d") == ["f.md"]


def test_a_write_outside_the_organization_works_the_same(h: StoreHarness) -> None:
    h.store.write_text(h.outside / "ws" / "n.md", "w")
    assert h.read(h.outside / "ws" / "n.md") == "w" and h.store.kind(h.outside / "ws" / "n.md") == "file"
