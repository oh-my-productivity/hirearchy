"""In-memory mailboxes and the registry the contract suites iterate over (skeleton: red step of A-mail)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..agents.testing import MemoryAgents
from ..kernel import AtomicWriter, Message, OrgPaths
from ..kernel.testing import FailingAtomicWriter, fs_atomic_writer, system_clock
from ._batch import FsBatchStore
from ._caching import DirMtimeCachingMailbox, FsDirectoryProbe
from ._index import FsMessageIndex, StampCachedMetaReader
from ._mailbox import FsMailbox
from ._parser import CachingMessageParser
from ._tasks import DerivedTaskQuery
from .api import (
    BatchStore,
    MailboxReader,
    MailboxWriter,
    MailFingerprint,
    MessageFile,
    MessageIndex,
    MessageParser,
    TaskQuery,
)


class CountingMessageParser(CachingMessageParser):
    """A ``CachingMessageParser`` that counts: ``loaded`` lists every file asked for, ``parses`` counts the files actually parsed."""

    loaded: list[Path]
    parses: int

    def __init__(self, max_entries: int = 50_000) -> None:
        raise NotImplementedError


class MemoryMailbox(MailboxReader, MailboxWriter, BatchStore, MailFingerprint, MessageIndex):
    """The mailboxes of an organization kept in memory (the file tree of a ``MemoryAgents``): five ports at once."""

    agents: MemoryAgents
    fails: Callable[[str], bool] | None

    def __init__(self, agents: MemoryAgents | None = None) -> None:
        raise NotImplementedError

    def messages(self, addr: str, *boxes: str) -> list[Message]:
        raise NotImplementedError

    def received(self, addr: str) -> list[Message]:
        raise NotImplementedError

    def sent(self, addr: str) -> list[Message]:
        raise NotImplementedError

    def find_received(self, addr: str, msg_id: str) -> Message | None:
        raise NotImplementedError

    def find_anywhere(self, addr: str, msg_id: str) -> Message | None:
        raise NotImplementedError

    def unread(self, addr: str) -> int:
        raise NotImplementedError

    def has_inflight(self, addr: str) -> bool:
        raise NotImplementedError

    def store(self, msg: Message) -> None:
        raise NotImplementedError

    def begin(self, addr: str) -> list[Message]:
        raise NotImplementedError

    def end(self, addr: str, ok: bool) -> None:
        raise NotImplementedError

    def recover(self) -> list[str]:
        raise NotImplementedError

    def redeliver_orphans(self) -> list[str]:
        raise NotImplementedError

    def fingerprint(self, addr: str) -> tuple[frozenset[str], frozenset[str]]:
        raise NotImplementedError

    def scan(self) -> list[MessageFile]:
        raise NotImplementedError


# ------------------------------------------------------------------------------ harnesses and the registry


@dataclass(frozen=True)
class MailHarness:
    """The ports of the mailboxes over one organization, and the means to prepare and inspect its files behind their back.

    Paths are relative to the organization (``""`` is the organization itself) and use ``/``.
    """

    reader: MailboxReader
    writer: MailboxWriter
    batches: BatchStore
    fingerprint: MailFingerprint
    index: MessageIndex
    tasks: TaskQuery
    agent: Callable[[str], None]  # make ``addr`` an agent (its charter), so that it exists
    put: Callable[[str, str], None]  # a file with this text (parents are created)
    read: Callable[[str], str | None]  # the text of a file, None when there is none
    listing: Callable[[str], list[str] | None]  # the sorted entry names of a directory, None when there is none
    path_of: Callable[[str], Path]  # the path a message parsed from this file has
    fail_writes: Callable[[Callable[[str], bool] | None], None]  # make writes of the paths the predicate accepts fail; None: stop failing
    parser: MessageParser | None = None  # the parser behind the reader, when there is one


def fs_mailbox(tmp_path: Path) -> MailHarness:
    raise NotImplementedError


def memory_mailbox(tmp_path: Path) -> MailHarness:
    raise NotImplementedError


def caching_mailbox(tmp_path: Path) -> MailHarness:
    raise NotImplementedError


@dataclass(frozen=True)
class ParserHarness:
    parser: MessageParser
    parses: Callable[[], int]  # how many files were actually parsed (not served from the cache) so far


def caching_parser(tmp_path: Path) -> ParserHarness:
    raise NotImplementedError


def counting_parser(tmp_path: Path) -> ParserHarness:
    raise NotImplementedError


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    MessageParser: [caching_parser, counting_parser],
    MailboxReader: [fs_mailbox, memory_mailbox, caching_mailbox],
    MailboxWriter: [fs_mailbox, memory_mailbox],
    BatchStore: [fs_mailbox, memory_mailbox],
    TaskQuery: [fs_mailbox, memory_mailbox],
    MailFingerprint: [fs_mailbox, memory_mailbox],
    MessageIndex: [fs_mailbox, memory_mailbox],
}
