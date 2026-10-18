"""``FsRetiredArchive`` and ``OsArchiveFiles``: the retired trees as the operating system shows them."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.agents import RetiredArchive, RetiredTree
from orgmcp.agents._retired import ArchiveFiles, FsRetiredArchive, OsArchiveFiles
from orgmcp.kernel import OrgPaths

from ._support import message


def archive(tmp_path: Path) -> FsRetiredArchive:
    return FsRetiredArchive(OrgPaths(tmp_path), OsArchiveFiles())


def test_the_classes_implement_their_ports(tmp_path: Path) -> None:
    assert isinstance(archive(tmp_path), RetiredArchive)
    assert isinstance(OsArchiveFiles(), ArchiveFiles)


def test_building_it_looks_at_nothing(tmp_path: Path) -> None:
    archive(tmp_path / "nowhere")
    assert not (tmp_path / "nowhere").exists()


def test_a_tree_has_the_path_of_its_directory(tmp_path: Path) -> None:
    (tmp_path / ".retired" / "ceo.eng-S").mkdir(parents=True)
    assert archive(tmp_path).trees() == [RetiredTree("ceo.eng-S", False, tmp_path / ".retired" / "ceo.eng-S")]


def test_a_symbolic_link_to_a_directory_is_a_tree(tmp_path: Path) -> None:
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / ".retired").mkdir()
    (tmp_path / ".retired" / "ceo-S").symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    assert [t.name for t in archive(tmp_path).trees()] == ["ceo-S"]


def test_an_unreadable_retired_directory_has_no_trees(tmp_path: Path) -> None:
    (tmp_path / ".retired").write_text("not a directory", encoding="utf-8")
    assert archive(tmp_path).trees() == [] and archive(tmp_path).run_count() == 0


def test_a_message_that_cannot_be_decoded_adds_nothing(tmp_path: Path) -> None:
    top = tmp_path / ".retired" / "ceo-S"
    (top / "inbox").mkdir(parents=True)
    (top / "AGENT.md").write_text("x", encoding="utf-8")
    (top / "inbox" / "good.md").write_text(message(5), encoding="utf-8")
    (top / "inbox" / "bad.md").write_bytes(b"---\nfrom: \xff\xfe\nto: x\ntype: y\nbudget: 100\n---\n")
    assert archive(tmp_path).unspent_budget(RetiredTree("ceo-S", True, top)) == 5


def test_a_mailbox_that_cannot_be_listed_adds_nothing(tmp_path: Path) -> None:
    top = tmp_path / ".retired" / "ceo-S"
    top.mkdir(parents=True)
    (top / "AGENT.md").write_text("x", encoding="utf-8")
    (top / "inbox").write_text("a file where a directory should be", encoding="utf-8")
    (top / "sent").mkdir()
    (top / "sent" / "a.md").write_text(message(2), encoding="utf-8")
    assert archive(tmp_path).unspent_budget(RetiredTree("ceo-S", True, top)) == -2


def test_a_tree_that_is_not_there_holds_nothing(tmp_path: Path) -> None:
    assert archive(tmp_path).unspent_budget(RetiredTree("ceo-S", True, tmp_path / ".retired" / "ceo-S")) == 0


def test_os_files_walk_like_os_walk_and_let_the_caller_prune(tmp_path: Path) -> None:
    for place in ("a/b", "a/c", "d"):
        (tmp_path / place).mkdir(parents=True)
    (tmp_path / "a" / "f.txt").write_text("x", encoding="utf-8")
    seen: list[Path] = []
    for here, dirs, files in OsArchiveFiles().walk(tmp_path):
        seen.append(here)
        if here == tmp_path / "a":
            assert files == ["f.txt"]
            dirs[:] = [d for d in dirs if d != "b"]
    assert sorted(seen) == sorted([tmp_path, tmp_path / "a", tmp_path / "a" / "c", tmp_path / "d"])
    assert all(isinstance(p, Path) for p in seen)


def test_os_files_walk_of_a_file_or_of_nothing_is_empty(tmp_path: Path) -> None:
    (tmp_path / "file").write_text("x", encoding="utf-8")
    assert list(OsArchiveFiles().walk(tmp_path / "file")) == [] and list(OsArchiveFiles().walk(tmp_path / "nowhere")) == []


def test_os_files_list_read_and_ask(tmp_path: Path) -> None:
    files = OsArchiveFiles()
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "x.md").write_text("é\r\n", encoding="utf-8")
    assert files.listdir(tmp_path / "d") == ["x.md"] and files.is_dir(tmp_path / "d") and not files.is_dir(tmp_path / "d" / "x.md")
    assert files.read_text(tmp_path / "d" / "x.md") == "é\n"
    with pytest.raises(OSError):
        files.listdir(tmp_path / "nowhere")
    with pytest.raises(OSError):
        files.read_text(tmp_path / "nowhere")
