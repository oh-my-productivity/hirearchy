"""``FsDeliverableFolder``: the only code that touches a contract's deliverable folder (design 6.3, DR-43, DR-45). Real files in ``tmp_path``.

Nothing outside the named place is opened: a link is reported and never followed (also one that appears after the path was resolved), a traverse-only
parent is walked through, a FIFO never blocks, and the bytes are bounded (4 MiB a file, 32 MiB a call, 200 entries)."""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from hirearchy.reflection._deliverables import FsDeliverableFolder, carried_unchanged, read_one, release, walk
from hirearchy.reflection._ports import DeliverableFolder, FolderRead, Located

MIB = 1024 * 1024
BUDGET = 32 * MIB
needs_modes = pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file modes")


def make(path: Path, text: str = "text\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def located(path: Path | str) -> Located:
    place = FsDeliverableFolder().locate(str(path))
    assert place is not None
    return place


def read(path: Path | str, budget: int = BUDGET) -> FolderRead:
    return FsDeliverableFolder().read(located(path), budget)


def names(found: FolderRead) -> list[str]:
    return [f.name for f in found.files]


@contextmanager
def modes(path: Path, mode: int) -> Iterator[None]:
    """``path`` has this mode for the block; the mode it had is restored in a ``finally`` (so pytest can clean the directory)."""
    before = path.stat().st_mode & 0o777
    path.chmod(mode)
    try:
        yield
    finally:
        path.chmod(before)


def test_it_is_a_deliverable_folder() -> None:
    assert isinstance(FsDeliverableFolder(), DeliverableFolder)


# ------------------------------------------------------------------------------------------------------------------------ what a path names


def test_a_relative_or_non_string_path_is_skipped() -> None:
    folder = FsDeliverableFolder()
    for raw in ("deliverables", "./deliverables", "", "   ", None, 3, ["/tmp"], {"path": "/tmp"}, b"/tmp"):
        assert folder.locate(raw) is None, raw


def test_dotdot_in_the_contract_path_is_normalized(tmp_path: Path) -> None:
    make(tmp_path / "b" / "inside.md")
    make(tmp_path / "a" / "elsewhere.md")
    place = located(f"{tmp_path}/a/../b")
    assert place.target == (tmp_path / "b").resolve() and place.named == Path(os.path.normpath(tmp_path / "b"))
    assert names(read(f"{tmp_path}/a/../b")) == ["inside.md"]  # the place the path names after `..`, not the one it started in
    assert names(read(f"{tmp_path}/a/./")) == ["elsewhere.md"]


def test_a_symlink_entry_is_a_link_and_never_read(tmp_path: Path) -> None:
    secret = make(tmp_path / "outside" / "secret.txt", "TOP SECRET\n")
    folder = tmp_path / "deliverables"
    make(folder / "memo.md", "the memo\n")
    (folder / "evil.md").symlink_to(secret)
    (folder / "evil-dir").symlink_to(tmp_path / "outside", target_is_directory=True)
    if os.geteuid() != 0:
        secret.chmod(0)  # a read of the target would fail loudly; the check must not even try
    try:
        found = read(folder)
    finally:
        secret.chmod(0o644)
    assert found.state == "folder"
    kinds = {f.name: f.kind for f in found.files}
    assert kinds == {"evil-dir": "link", "evil.md": "link", "memo.md": "file"}
    assert all(b"TOP SECRET" not in f.data and f.data == b"" for f in found.files if f.kind == "link")


def test_the_folder_itself_a_symlink_gives_the_folder_link_line_and_no_names(tmp_path: Path) -> None:
    make(tmp_path / "ssh" / "id_rsa", "KEY\n")
    (tmp_path / "deliverables").symlink_to(tmp_path / "ssh", target_is_directory=True)
    place = located(tmp_path / "deliverables")
    assert place.link is True
    folder = FsDeliverableFolder()
    assert folder.kind(place) == "link"
    found = folder.read(place, BUDGET)
    assert (found.state, found.files, found.used) == ("link", (), 0)
    assert found.folder == str(tmp_path / "deliverables")  # the place the contract names, not where it leads


def test_a_missing_folder_or_file_gives_nothing(tmp_path: Path) -> None:
    folder = FsDeliverableFolder()
    for path in (tmp_path / "nope", tmp_path / "nope" / "deeper", tmp_path / "nope" / "memo.md"):
        place = located(path)
        assert folder.kind(place) == "missing"
        found = folder.read(place, BUDGET)
        assert (found.state, found.files) == ("missing", ())
    (tmp_path / "empty").mkdir()
    assert read(tmp_path / "empty").state == "folder" and read(tmp_path / "empty").files == ()


def test_a_contract_that_names_a_file_is_opened_through_its_folder(tmp_path: Path) -> None:
    make(tmp_path / "d" / "memo.md", "the memo\n")
    make(tmp_path / "d" / "other.md", "not mine\n")
    place = located(tmp_path / "d" / "memo.md")
    folder = FsDeliverableFolder()
    assert folder.kind(place) == "file"
    found = folder.read(place, BUDGET)
    assert (found.state, found.folder) == ("file", str((tmp_path / "d").resolve()))
    assert [(f.name, f.kind, f.data) for f in found.files] == [("memo.md", "file", b"the memo\n")]  # that one file, none of its neighbours
    assert found.used == len(b"the memo\n")


# ------------------------------------------------------------------------------------------------------------------------ links that appear later (DR-43)


def swap_for_link(path: Path, to: Path) -> None:
    """Replace ``path`` by a symbolic link to ``to`` (what an agent with a shell and an overlapping workspace could do)."""
    path.rename(path.with_name(path.name + ".was"))
    path.symlink_to(to, target_is_directory=to.is_dir())


def test_a_component_swapped_for_a_link_after_the_resolve_reports_link(tmp_path: Path) -> None:
    make(tmp_path / "a" / "b" / "deliverables" / "memo.md")
    make(tmp_path / "other" / "b" / "deliverables" / "secret.md", "TOP SECRET\n")
    place = located(tmp_path / "a" / "b" / "deliverables")  # resolved while `a` was a real folder
    swap_for_link(tmp_path / "a", tmp_path / "other")
    opened = walk(place.target)  # the seam: the stale target is walked, not resolved again
    try:
        assert opened.kind == "link"
    finally:
        release(opened)
    found = FsDeliverableFolder().read(place, BUDGET)
    assert (found.state, found.files) == ("link", ())  # nothing of the other folder was read
    assert "secret.md" not in str(found)


def test_a_last_component_swapped_for_a_link_reports_link(tmp_path: Path) -> None:
    make(tmp_path / "deliverables" / "memo.md")
    make(tmp_path / "other" / "secret.md", "TOP SECRET\n")
    folder_place = located(tmp_path / "deliverables")
    file_place = located(tmp_path / "deliverables" / "memo.md")
    swap_for_link(tmp_path / "deliverables" / "memo.md", tmp_path / "other" / "secret.md")
    assert FsDeliverableFolder().read(file_place, BUDGET).state == "link"  # the file contract: its file became a link
    swap_for_link(tmp_path / "deliverables", tmp_path / "other")
    found = FsDeliverableFolder().read(folder_place, BUDGET)
    assert (found.state, found.files) == ("link", ())  # the folder contract: its folder became a link


def test_a_link_swapped_in_for_a_single_file_is_link(tmp_path: Path) -> None:
    secret = make(tmp_path / "secret.md", "TOP SECRET\n")
    make(tmp_path / "d" / "memo.md")
    place = located(tmp_path / "d" / "memo.md")
    (tmp_path / "d" / "memo.md").unlink()
    (tmp_path / "d" / "memo.md").symlink_to(secret)
    found = FsDeliverableFolder().read(place, BUDGET)
    assert (found.state, found.files) == ("link", ())


@needs_modes
def test_a_traverse_only_parent_gives_no_unreadable(tmp_path: Path) -> None:
    """``p`` has mode ``--x`` for its owner: it can be passed through, not listed. The folder below it is read; no finding says ``unreadable``."""
    make(tmp_path / "p" / "deliverables" / "memo.md", "the memo\n")
    with modes(tmp_path / "p", 0o311):
        place = located(tmp_path / "p" / "deliverables")
        found = FsDeliverableFolder().read(place, BUDGET)
        assert (found.state, names(found)) == ("folder", ["memo.md"]), found
        assert FsDeliverableFolder().kind(place) == "folder"
        single = FsDeliverableFolder().read(located(tmp_path / "p" / "deliverables" / "memo.md"), BUDGET)
        assert (single.state, names(single)) == ("file", ["memo.md"])  # the same for a file contract below it


@needs_modes
def test_two_traverse_only_parents_are_walked_through(tmp_path: Path) -> None:
    make(tmp_path / "p" / "q" / "deliverables" / "memo.md")
    with modes(tmp_path / "p", 0o311), modes(tmp_path / "p" / "q", 0o311):
        found = FsDeliverableFolder().read(located(tmp_path / "p" / "q" / "deliverables"), BUDGET)
        assert (found.state, names(found)) == ("folder", ["memo.md"])


@needs_modes
def test_a_traverse_only_parent_swapped_for_a_link_reports_link(tmp_path: Path) -> None:
    make(tmp_path / "p" / "deliverables" / "memo.md")
    make(tmp_path / "other" / "deliverables" / "secret.md", "TOP SECRET\n")
    with modes(tmp_path / "p", 0o311):
        place = located(tmp_path / "p" / "deliverables")
    swap_for_link(tmp_path / "p", tmp_path / "other")
    found = FsDeliverableFolder().read(place, BUDGET)
    assert (found.state, found.files) == ("link", ())
    assert "secret.md" not in str(found)


def test_a_carried_component_that_changed_is_detected(tmp_path: Path) -> None:
    """The walk re-checks every traverse-only component it carried once the next open succeeds: one that is no longer the same directory, or is now
    a link, ends the walk with `link` (the check on its own, since the swap happens between two steps of the walk)."""
    make(tmp_path / "p" / "d" / "memo.md")
    make(tmp_path / "other" / "d" / "secret.md")
    fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        before = os.stat("p", dir_fd=fd, follow_symlinks=False)
        carried = [("p", before.st_dev, before.st_ino)]
        assert carried_unchanged(fd, carried) is True
        swap_for_link(tmp_path / "p", tmp_path / "other")  # now a link
        assert carried_unchanged(fd, carried) is False
        (tmp_path / "p").unlink()
        (tmp_path / "p").mkdir()  # a different directory under the same name
        assert carried_unchanged(fd, carried) is False
        (tmp_path / "p").rmdir()
        assert carried_unchanged(fd, carried) is False  # gone
    finally:
        os.close(fd)


@needs_modes
def test_a_folder_that_cannot_be_listed_is_unreadable(tmp_path: Path) -> None:
    make(tmp_path / "deliverables" / "memo.md")
    with modes(tmp_path / "deliverables", 0o311):  # may be passed through, not opened for listing
        place = located(tmp_path / "deliverables")
        folder = FsDeliverableFolder()
        assert folder.kind(place) == "unreadable"
        found = folder.read(place, BUDGET)
        assert (found.state, found.files) == ("unreadable", ()) and found.error and "deliverables" not in found.error


@needs_modes
def test_a_file_that_cannot_be_read_is_unreadable_for_that_file_only(tmp_path: Path) -> None:
    make(tmp_path / "d" / "a.md")
    locked = make(tmp_path / "d" / "locked.md")
    with modes(locked, 0o000):
        found = read(tmp_path / "d")
    assert {f.name: f.kind for f in found.files} == {"a.md": "file", "locked.md": "unreadable"}
    assert [f.error for f in found.files if f.kind == "unreadable"][0]


def test_descriptors_are_closed(tmp_path: Path) -> None:
    make(tmp_path / "d" / "a.md")
    (tmp_path / "d" / "l.md").symlink_to(tmp_path / "d" / "a.md")
    place, file_place = located(tmp_path / "d"), located(tmp_path / "d" / "a.md")
    folder = FsDeliverableFolder()

    def open_descriptors() -> int:
        return len(os.listdir("/dev/fd"))

    before = open_descriptors()
    for _ in range(20):
        folder.kind(place)
        folder.read(place, BUDGET)
        folder.read(file_place, BUDGET)
        folder.read(located(tmp_path / "nope"), BUDGET)
    assert open_descriptors() == before


# ------------------------------------------------------------------------------------------------------------------------ what is read, and how much


def test_a_fifo_is_skipped_and_one_swapped_in_does_not_block(tmp_path: Path) -> None:
    make(tmp_path / "d" / "a.md")
    os.mkfifo(tmp_path / "d" / "pipe")
    result: list[FolderRead] = []
    worker = threading.Thread(target=lambda: result.append(read(tmp_path / "d")), daemon=True)
    worker.start()
    worker.join(5)  # the guard: a read that blocks on the pipe would never finish
    assert not worker.is_alive(), "the folder read blocked on a FIFO"
    assert names(result[0]) == ["a.md"]  # listed as not a regular file: skipped, never opened
    # an entry that was a regular file when it was listed and is a FIFO when it is opened (swapped in between): O_NONBLOCK, then fstat
    dfd = os.open(tmp_path / "d", os.O_RDONLY | os.O_DIRECTORY)
    try:
        swapped: list[object] = []
        opener = threading.Thread(target=lambda: swapped.append(read_one(dfd, "pipe", BUDGET)), daemon=True)
        opener.start()
        opener.join(5)
        assert not opener.is_alive(), "opening the swapped-in FIFO blocked"
        assert swapped == [None]
    finally:
        os.close(dfd)


def test_a_file_over_4_mib_is_large(tmp_path: Path) -> None:
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "exact.bin").write_bytes(b"x" * (4 * MIB))
    (tmp_path / "d" / "over.bin").write_bytes(b"x" * (4 * MIB + 1))
    found = read(tmp_path / "d")
    assert {f.name: f.kind for f in found.files} == {"exact.bin": "file", "over.bin": "large"}
    assert [len(f.data) for f in found.files] == [4 * MIB, 0]  # the large one is not kept
    assert found.used == 4 * MIB


def test_nine_4_mib_files_read_eight_and_the_ninth_is_limit(tmp_path: Path) -> None:
    (tmp_path / "d").mkdir()
    for n in range(9):
        (tmp_path / "d" / f"f{n}.bin").write_bytes(bytes([n]) * (4 * MIB))
    found = read(tmp_path / "d")
    assert [f.kind for f in found.files] == ["file"] * 8 + ["limit"]
    assert found.used == 32 * MIB and found.files[8].data == b""
    assert [f.kind for f in read(tmp_path / "d", 4 * MIB).files][:3] == ["file", "limit", "limit"]  # the budget the caller still has


def test_a_hard_link_is_read(tmp_path: Path) -> None:
    make(tmp_path / "d" / "a.md", "same\n")
    os.link(tmp_path / "d" / "a.md", tmp_path / "d" / "b.md")
    found = read(tmp_path / "d")
    assert [(f.name, f.kind, f.data) for f in found.files] == [("a.md", "file", b"same\n"), ("b.md", "file", b"same\n")]


def test_a_subfolder_is_skipped(tmp_path: Path) -> None:
    make(tmp_path / "d" / "a.md")
    make(tmp_path / "d" / "sub" / "inner.md")
    assert names(read(tmp_path / "d")) == ["a.md"]  # never recursive


def test_hidden_entries_are_skipped(tmp_path: Path) -> None:
    make(tmp_path / "d" / "a.md")
    make(tmp_path / "d" / ".DS_Store")
    make(tmp_path / "d" / ".hidden.md")
    assert names(read(tmp_path / "d")) == ["a.md"]


def test_201_entries_read_200(tmp_path: Path) -> None:
    (tmp_path / "d").mkdir()
    for n in range(201):
        (tmp_path / "d" / f"f{n:03d}.md").write_text("x", encoding="utf-8")
    found = read(tmp_path / "d")
    assert len(found.files) == 200 and names(found)[0] == "f000.md" and names(found)[-1] == "f199.md"  # in name order


def test_files_carry_their_content_and_their_mtime_in_microseconds(tmp_path: Path) -> None:
    path = make(tmp_path / "d" / "a.md", "hello\n")
    os.utime(path, ns=(1_700_000_000_123_456_789, 1_700_000_000_123_456_789))
    (found,) = read(tmp_path / "d").files
    assert (found.data, found.mtime_us) == (b"hello\n", 1_700_000_000_123_456)
