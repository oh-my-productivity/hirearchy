"""``FsBatchStore`` only: the moves go through the file system and the redelivery through the injected atomic writer."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.agents.testing import MemoryAgents
from hirearchy.kernel import OrgPaths
from hirearchy.kernel.testing import FailingAtomicWriter, MemoryAtomicWriter
from hirearchy.mail import BatchStore
from hirearchy.mail._batch import FsBatchStore
from hirearchy.mail._mailbox import FsMailbox
from hirearchy.mail.testing import CountingMessageParser

from ._support import message_text, mid


def store(root: Path, agents: list[str], writer: MemoryAtomicWriter | FailingAtomicWriter | None = None) -> tuple[FsBatchStore, CountingMessageParser]:
    directory = MemoryAgents()
    for addr in agents:
        directory.put(f"{addr}/AGENT.md", "---\nrole: R\n---\nx\n")
        (root / addr).mkdir(parents=True, exist_ok=True)
    layout, parser, atomic = OrgPaths(root), CountingMessageParser(), writer or MemoryAtomicWriter()
    return FsBatchStore(layout, directory, FsMailbox(layout, parser, atomic), parser, atomic), parser


def sent_file(root: Path, n: int, to: str) -> Path:
    path = root / "ceo" / "sent" / f"{mid(n, 'ceo')}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(message_text(mid(n, "ceo"), sender="ceo", to=to), encoding="utf-8")
    return path


def test_it_is_a_batch_store(tmp_path: Path) -> None:
    assert isinstance(store(tmp_path, ["ceo"])[0], BatchStore)


def test_building_one_touches_nothing(tmp_path: Path) -> None:
    FsBatchStore(OrgPaths(tmp_path / "absent"), MemoryAgents(), FsMailbox(OrgPaths(tmp_path), CountingMessageParser(), MemoryAtomicWriter()),
                 CountingMessageParser(), MemoryAtomicWriter())
    assert list(tmp_path.iterdir()) == []


def test_begin_of_an_agent_without_a_directory_fails_like_mkdir(tmp_path: Path) -> None:
    """The batch of an agent that is not there cannot start; only ``end`` is a no-op for a vanished agent."""
    batches, _ = store(tmp_path, [])
    with pytest.raises(FileNotFoundError):
        batches.begin("ghost")


def test_the_batch_returned_by_begin_is_read_from_the_inflight_box_once(tmp_path: Path) -> None:
    batches, parser = store(tmp_path, ["ceo"])
    inbox = tmp_path / "ceo" / "inbox"
    inbox.mkdir()
    for n in range(3):
        (inbox / f"{mid(n)}.md").write_text(message_text(mid(n), to="ceo"), encoding="utf-8")
    assert len(batches.begin("ceo")) == 3 and parser.parses == 3


def test_redelivery_writes_through_the_atomic_writer(tmp_path: Path) -> None:
    writer = MemoryAtomicWriter()
    batches, _ = store(tmp_path, ["ceo", "ceo/eng"], writer)
    path = sent_file(tmp_path, 1, "ceo/eng")
    assert batches.redeliver_orphans() == [mid(1, "ceo")]
    assert writer.files == {tmp_path / "ceo" / "eng" / "inbox" / path.name: path.read_text(encoding="utf-8")}


def test_a_failing_redelivery_raises_and_delivers_nothing(tmp_path: Path) -> None:
    writer = FailingAtomicWriter(MemoryAtomicWriter())
    batches, _ = store(tmp_path, ["ceo", "ceo/eng"], writer)
    sent_file(tmp_path, 1, "ceo/eng")
    with pytest.raises(OSError):
        batches.redeliver_orphans()
    assert not (tmp_path / "ceo" / "eng" / "inbox").exists()


def test_a_sent_file_is_parsed_only_when_no_copy_is_known(tmp_path: Path) -> None:
    """The file names of the received boxes find the orphans; the whole history is not parsed."""
    batches, parser = store(tmp_path, ["ceo", "ceo/eng"])
    for n in range(5):
        path = sent_file(tmp_path, n, "ceo/eng")
        (tmp_path / "ceo" / "eng" / "read").mkdir(parents=True, exist_ok=True)
        (tmp_path / "ceo" / "eng" / "read" / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    sent_file(tmp_path, 9, "ceo/eng")
    assert batches.redeliver_orphans() == [mid(9, "ceo")] and parser.parses == 1
