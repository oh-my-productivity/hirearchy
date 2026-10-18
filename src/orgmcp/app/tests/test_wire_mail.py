"""``wire_mail``: the runtime has the mail ports, built from the kernel's ports and the process resources, and the dashboard's lenient variant."""

from __future__ import annotations

from pathlib import Path

import pytest

import orgmcp.core as core
from orgmcp.agents import AgentDirectory
from orgmcp.agents.testing import MemoryAgents
from orgmcp.app import wire_mail, wiring
from orgmcp.kernel import Message, OrgLayout, OrgPaths
from orgmcp.mail import BatchStore, MailboxReader, MailboxWriter, MailFingerprint, MessageIndex, MessageParser, TaskQuery
from orgmcp.mail._batch import FsBatchStore
from orgmcp.mail._caching import DirectoryProbe, DirMtimeCachingMailbox
from orgmcp.mail._index import FsMessageIndex
from orgmcp.mail._mailbox import FsMailbox
from orgmcp.mail._parser import CachingMessageParser
from orgmcp.mail._tasks import DerivedTaskQuery
from orgmcp.mail.testing import CountingMessageParser, MemoryMailbox


class FixedProbe(DirectoryProbe):
    """Every directory was last modified at this time (-1: there is none)."""

    def __init__(self, mtime: int) -> None:
        self._mtime = mtime

    def mtime(self, addr: str, name: str) -> int:
        return self._mtime


def note(n: int, sender: str = "ceo", to: str = "ceo/eng") -> Message:
    return Message(sender=sender, to=to, type="task", body="b", id=f"20260101T0000000000{n:02d}-{sender}-aaaa", created="2026-01-01T00:00:00+00:00")


def test_the_runtime_has_the_real_mail_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.message_parser, CachingMessageParser) and isinstance(runtime.message_parser, MessageParser)
    assert isinstance(runtime.mailbox, FsMailbox) and isinstance(runtime.mailbox, MailboxReader)
    assert isinstance(runtime.mailbox_writer, FsMailbox) and isinstance(runtime.mailbox_writer, MailboxWriter)
    assert isinstance(runtime.mail_fingerprint, FsMailbox) and isinstance(runtime.mail_fingerprint, MailFingerprint)
    assert isinstance(runtime.batches, FsBatchStore) and isinstance(runtime.batches, BatchStore)
    assert isinstance(runtime.task_query, DerivedTaskQuery) and isinstance(runtime.task_query, TaskQuery)
    assert isinstance(runtime.message_index, FsMessageIndex) and isinstance(runtime.message_index, MessageIndex)


def test_building_the_mail_ports_does_no_io(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path / "absent")
    assert runtime.mailbox.unread("ceo") == 0 and runtime.mail_fingerprint.fingerprint("ceo") == (frozenset(), frozenset())
    assert runtime.message_index.scan() == [] and not (tmp_path / "absent").exists()


def test_the_parser_and_the_meta_cache_are_the_process_resources(tmp_path: Path) -> None:
    """ARCHITECTURE.md 2.4: two runtimes in one process share the parse cache and the front-matter cache, as the module globals did."""
    first, second = wiring.open_runtime(tmp_path / "a"), wiring.open_runtime(tmp_path / "b")
    assert first.message_parser is second.message_parser is wiring.process_resources().message_parser
    index = first.message_index
    assert isinstance(index, FsMessageIndex) and index._meta is wiring.process_resources().meta_cache


def test_every_runtime_has_its_own_mail_ports(tmp_path: Path) -> None:
    first, second = wiring.open_runtime(tmp_path), wiring.open_runtime(tmp_path)
    assert first.mailbox is not second.mailbox and first.batches is not second.batches


def test_the_ports_look_at_the_runtime_root(tmp_path: Path) -> None:
    (tmp_path / "ceo" / "inbox").mkdir(parents=True)
    (tmp_path / "ceo" / "AGENT.md").write_text("---\nrole: R\n---\nx\n", encoding="utf-8")
    msg = note(1, sender="root", to="ceo")
    (tmp_path / "ceo" / "inbox" / f"{msg.id}.md").write_text(msg.to_text(), encoding="utf-8")
    runtime = wiring.open_runtime(tmp_path)
    assert [m.id for m in runtime.mailbox.messages("ceo", "inbox")] == [msg.id] and runtime.mailbox.unread("ceo") == 1
    assert [m.id for m in runtime.task_query.open_tasks("ceo")] == [msg.id]
    assert [f.id for f in runtime.message_index.scan()] == [msg.id]
    assert [m.id for m in runtime.batches.begin("ceo")] == [msg.id] and runtime.mailbox.has_inflight("ceo")


def test_the_messages_are_written_through_the_atomic_writer_of_the_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``core.atomic_write`` is a patch point of the tests until they are converted: the writer of the runtime reads it at the time of the call."""
    written: list[Path] = []
    monkeypatch.setattr(core, "atomic_write", lambda path, text: written.append(path))
    msg = note(1)
    wiring.open_runtime(tmp_path).mailbox_writer.store(msg)
    assert written == [tmp_path / "ceo" / "sent" / f"{msg.id}.md", tmp_path / "ceo" / "eng" / "inbox" / f"{msg.id}.md"]


def test_an_override_of_the_parser_is_the_one_every_mail_port_reads_through(tmp_path: Path) -> None:
    (tmp_path / "ceo" / "inbox").mkdir(parents=True)
    msg = note(1, sender="root", to="ceo")
    (tmp_path / "ceo" / "inbox" / f"{msg.id}.md").write_text(msg.to_text(), encoding="utf-8")
    counting = CountingMessageParser()
    runtime = wiring.open_runtime(tmp_path, {MessageParser: counting})
    assert runtime.message_parser is counting
    runtime.mailbox.messages("ceo", "inbox")
    runtime.task_query.open_tasks("ceo")
    runtime.mailbox.unread("ceo")
    assert counting.loaded and counting.parses == 1  # one file, parsed once however often it was asked for


def test_an_override_replaces_the_port_and_what_is_derived_from_it_follows(tmp_path: Path) -> None:
    fake = MemoryMailbox()
    fake.agents.put("ceo/AGENT.md", "---\nrole: R\n---\nx\n")
    runtime = wiring.open_runtime(tmp_path, {MailboxReader: fake})
    assert runtime.mailbox is fake and runtime.mailbox_writer is not fake
    fake.store(note(1, sender="root", to="ceo"))
    assert [m.id for m in runtime.task_query.open_tasks("ceo")] == [note(1, sender="root", to="ceo").id]  # derived from the override


def test_the_layout_the_ports_are_built_on_is_the_runtimes(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path, {OrgLayout: OrgPaths(tmp_path / "elsewhere")})
    msg = note(1, sender="root", to="ceo")
    runtime.mailbox_writer.store(msg)
    assert (tmp_path / "elsewhere" / "ceo" / "inbox" / f"{msg.id}.md").is_file()


# ------------------------------------------------------------------------------ the dashboard's variant


def test_lenient_puts_the_decorator_on_the_reader_and_derives_the_task_views_from_it(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    lenient, mailbox = wire_mail.lenient(runtime, FixedProbe(-1))
    assert lenient.mailbox is mailbox and isinstance(mailbox, DirMtimeCachingMailbox)
    assert isinstance(lenient.task_query, DerivedTaskQuery) and lenient.task_query is not runtime.task_query
    assert lenient.mailbox_writer is runtime.mailbox_writer and lenient.batches is runtime.batches
    assert lenient.message_parser is runtime.message_parser and isinstance(lenient.message_index, FsMessageIndex)
    assert lenient.root == runtime.root and lenient.clock is runtime.clock
    assert lenient.mailbox.messages("anyone", "inbox") == []  # the probe says there is no such directory


def test_the_lenient_index_walks_the_agents_of_the_runtime_it_is_given(tmp_path: Path) -> None:
    (tmp_path / "ceo" / "inbox").mkdir(parents=True)
    (tmp_path / "ceo" / "AGENT.md").write_text("---\nrole: R\n---\nx\n", encoding="utf-8")
    msg = note(1, sender="root", to="ceo")
    (tmp_path / "ceo" / "inbox" / f"{msg.id}.md").write_text(msg.to_text(), encoding="utf-8")
    runtime = wiring.open_runtime(tmp_path)
    assert [f.id for f in runtime.message_index.scan()] == [msg.id]
    quiet_agents = wiring.open_runtime(tmp_path, {AgentDirectory: MemoryAgents()})  # an agent directory that knows nobody
    assert [f.id for f in wire_mail.lenient(quiet_agents, FixedProbe(-1))[0].message_index.scan()] == []


def test_what_the_probe_says_is_quiet_is_read_once(tmp_path: Path) -> None:
    (tmp_path / "ceo" / "inbox").mkdir(parents=True)
    lenient, _ = wire_mail.lenient(wiring.open_runtime(tmp_path), FixedProbe(1))  # modified at the epoch: long quiet
    one = note(1, sender="root", to="ceo")
    (tmp_path / "ceo" / "inbox" / f"{one.id}.md").write_text(one.to_text(), encoding="utf-8")
    assert [m.id for m in lenient.mailbox.messages("ceo", "inbox")] == [one.id]
    two = note(2, sender="root", to="ceo")
    (tmp_path / "ceo" / "inbox" / f"{two.id}.md").write_text(two.to_text(), encoding="utf-8")
    assert [m.id for m in lenient.mailbox.messages("ceo", "inbox")] == [one.id]  # trusted: the probe still says nothing changed
