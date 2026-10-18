"""``FsOrgSettings``: ORG.md of one organization directory, written through the injected atomic writer."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import OrgPaths
from orgmcp.kernel import AtomicWriter
from orgmcp.kernel.testing import FailingAtomicWriter, MemoryAtomicWriter, fs_atomic_writer
from orgmcp.settings import DEFAULT_CONFIG, OrgDocumentStore, OrgSettings
from orgmcp.settings._fs import FsOrgSettings
from orgmcp.settings.tests._red import red


def make(root: Path, writer: AtomicWriter | None = None) -> FsOrgSettings:
    return FsOrgSettings(OrgPaths(root), writer or fs_atomic_writer(root).writer)


def test_it_is_both_the_settings_and_the_document_store(tmp_path: Path) -> None:
    fs = make(tmp_path)
    assert isinstance(fs, OrgSettings) and isinstance(fs, OrgDocumentStore)


def test_building_it_touches_nothing(tmp_path: Path) -> None:
    root = tmp_path / "does-not-exist"
    make(root)
    assert not root.exists()


@red
def test_it_reads_and_writes_the_file_ORG_md_of_the_root(tmp_path: Path) -> None:
    fs = make(tmp_path)
    fs.write_raw("---\nmax_depth: 9\n---\nbody\n")
    assert (tmp_path / "ORG.md").read_text(encoding="utf-8") == "---\nmax_depth: 9\n---\nbody\n"
    (tmp_path / "ORG.md").write_text("---\nmax_depth: 2\n---\nother\n", encoding="utf-8")
    assert fs.config()["max_depth"] == 2 and fs.rules() == "other"


@red
def test_a_directory_called_ORG_md_is_not_a_document(tmp_path: Path) -> None:
    (tmp_path / "ORG.md").mkdir()
    assert make(tmp_path).exists() is False


@red
def test_the_write_goes_through_the_injected_writer(tmp_path: Path) -> None:
    writer = MemoryAtomicWriter()
    make(tmp_path, writer).write_raw("text\n")
    assert writer.files == {tmp_path / "ORG.md": "text\n"}
    assert not (tmp_path / "ORG.md").exists()


@red
def test_a_failed_write_leaves_the_old_document_and_no_temporary_file(tmp_path: Path) -> None:
    (tmp_path / "ORG.md").write_text("old\n", encoding="utf-8")
    broken = FailingAtomicWriter(fs_atomic_writer(tmp_path).writer)
    with pytest.raises(OSError):
        make(tmp_path, broken).write_raw("new\n")
    assert broken.attempts == [tmp_path / "ORG.md"]
    assert (tmp_path / "ORG.md").read_text(encoding="utf-8") == "old\n"
    assert [p.name for p in tmp_path.iterdir()] == ["ORG.md"]


@red
def test_the_settings_never_change_the_file(tmp_path: Path) -> None:
    (tmp_path / "ORG.md").write_text("---\nmax_depth: 2\n---\nbody\n", encoding="utf-8")
    fs = make(tmp_path)
    before = (tmp_path / "ORG.md").stat().st_mtime_ns
    fs.config(), fs.rules(), fs.default_model(), fs.number("max_depth"), fs.message_cap(), fs.exists(), fs.read_raw()
    assert (tmp_path / "ORG.md").stat().st_mtime_ns == before


@red
def test_the_config_is_a_new_mapping_every_time(tmp_path: Path) -> None:
    (tmp_path / "ORG.md").write_text("---\nmax_depth: 2\n---\nbody\n", encoding="utf-8")
    fs = make(tmp_path)
    first = fs.config()
    first["max_depth"] = 99
    assert fs.config()["max_depth"] == 2 and fs.config() is not fs.config()
    assert first is not DEFAULT_CONFIG


@red
def test_windows_line_ends_are_read_like_every_text_file_here(tmp_path: Path) -> None:
    """The legacy readers open ORG.md in text mode (``read_text``): a CRLF file reads with LF, so its frontmatter is found."""
    (tmp_path / "ORG.md").write_bytes(b"---\r\nmax_depth: 2\r\n---\r\nbody\r\n")
    fs = make(tmp_path)
    assert fs.read_raw() == "---\nmax_depth: 2\n---\nbody\n"
    assert fs.config()["max_depth"] == 2 and fs.rules() == "body"
