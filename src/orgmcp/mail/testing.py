"""In-memory mailboxes and the registry the contract suites iterate over.

``MemoryMailbox`` is the reader, the writer, the batch store, the fingerprint and the index at once, over the in-memory file tree of a
``MemoryAgents``. It passes the same contract suites as the real implementations (``tests/test_contract_*.py``), so a consumer's unit
test may use it instead of directories on disk. ``CountingMessageParser`` is the real parse cache with counters, for the tests that
guard the cache hits (the count, not a time).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..agents.testing import MemoryAgents, fs_agents
from ..kernel import BOXES, ROOT, RUNTIME, JsonObject, Message, OrgPaths, norm, split_frontmatter
from ..kernel.testing import FailingAtomicWriter, fs_atomic_writer, system_clock
from ._batch import FsBatchStore
from ._caching import DirMtimeCachingMailbox, FsDirectoryProbe
from ._index import FsMessageIndex, StampCachedMetaReader, describe
from ._mailbox import FsMailbox
from ._parser import CachingMessageParser, M, Split
from ._reads import DerivedMailboxReads
from ._rules import RECEIVED_BOXES, is_message_name, is_plain_id
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

AGENT_FILE = "---\nrole: Worker\n---\n# Role: Worker\n\nDo the work.\n"  # the charter the harnesses give an agent


class CountingMessageParser(CachingMessageParser):
    """A ``CachingMessageParser`` that counts: ``loaded`` lists every file asked for, ``parses`` counts the files actually parsed."""

    def __init__(self, max_entries: int = 50_000, split: Split = split_frontmatter) -> None:
        super().__init__(max_entries, split)
        self.loaded: list[Path] = []
        self.parses = 0

    def parse_as(self, cls: type[M], path: Path) -> M:
        self.loaded.append(path)
        return super().parse_as(cls, path)

    def _split_text(self, text: str) -> tuple[JsonObject, str]:
        self.parses += 1
        return super()._split_text(text)


class MemoryMailbox(DerivedMailboxReads, MailboxWriter, BatchStore, MailFingerprint, MessageIndex):
    """The mailboxes of an organization kept in memory (the file tree of a ``MemoryAgents``): five ports at once.

    Files are prepared and inspected through ``agents`` (``put``, ``read``, ``listing``). ``fails`` makes a write fail like a full disk
    for the paths (relative to the organization) it accepts. The fake keeps no file times: every message file is one second old.
    """

    def __init__(self, agents: MemoryAgents | None = None) -> None:
        self.agents = agents or MemoryAgents()
        self.fails: Callable[[str], bool] | None = None

    # ------------------------------------------------------------------ the tree

    @staticmethod
    def _dir(addr: str, box: str) -> str:
        """The directory of a box, relative to the organization (the boxes of root are in the organization itself)."""
        a = norm(addr)
        return box if a == ROOT else f"{a}/{box}"

    def _names(self, addr: str, box: str) -> list[str]:
        """The sorted names of the message files in a box (``[]`` when there is no such box)."""
        d = self._dir(addr, box)
        return [n for n in self.agents.listing(d) or [] if is_message_name(n) and f"{d}/{n}" in self.agents.files]

    def _parse(self, addr: str, box: str, name: str) -> Message:
        key = f"{self._dir(addr, box)}/{name}"
        return Message.parse(self.agents.files[key], self.agents.root / key)

    def _write(self, key: str, text: str) -> None:
        if self.fails is not None and self.fails(key):
            raise OSError(28, "No space left on device")
        self.agents.put(key, text)

    def _move(self, source: str, target: str) -> None:
        self.agents.put(target, self.agents.files.pop(source))

    # ------------------------------------------------------------------ MailboxReader

    def messages(self, addr: str, *boxes: str) -> list[Message]:
        out = [self._parse(addr, box, n) for box in boxes for n in self._names(addr, box)]
        return sorted(out, key=lambda m: m.id)

    def find_anywhere(self, addr: str, msg_id: str) -> Message | None:
        if not is_plain_id(msg_id):
            return None
        for box in BOXES:
            if f"{self._dir(addr, box)}/{msg_id}.md" in self.agents.files:
                try:
                    return self._parse(addr, box, f"{msg_id}.md")
                except Exception:  # noqa: BLE001 - a file that does not parse is no answer
                    return None
        return None

    def unread(self, addr: str) -> int:
        return sum(1 for n in self._names(addr, "inbox") if self._wakes(addr, n))

    def _wakes(self, addr: str, name: str) -> bool:
        try:
            return self._parse(addr, "inbox", name).wake
        except Exception:  # noqa: BLE001 - an unreadable file still counts as mail: a run should look at it
            return True

    def has_inflight(self, addr: str) -> bool:
        return bool(self._names(addr, "inflight"))

    # ------------------------------------------------------------------ MailboxWriter

    def store(self, msg: Message) -> None:
        text = msg.to_text()
        if msg.sender != RUNTIME:
            self._write(f"{self._dir(msg.sender, 'sent')}/{msg.id}.md", text)
        self._write(f"{self._dir(msg.to, 'inbox')}/{msg.id}.md", text)

    # ------------------------------------------------------------------ BatchStore

    def begin(self, addr: str) -> list[Message]:
        if norm(addr) != ROOT and norm(addr) not in self.agents.dirs:
            raise FileNotFoundError(2, "No such file or directory", self._dir(addr, "inflight"))
        self.agents.put_dir(self._dir(addr, "inflight"))
        for n in self._names(addr, "inbox"):
            self._move(f"{self._dir(addr, 'inbox')}/{n}", f"{self._dir(addr, 'inflight')}/{n}")
        return self.messages(addr, "inflight")

    def end(self, addr: str, ok: bool) -> None:
        if not self.agents.exists(addr):
            return
        target = "read" if ok else "inbox"
        self.agents.put_dir(self._dir(addr, target))
        for n in self._names(addr, "inflight"):
            self._move(f"{self._dir(addr, 'inflight')}/{n}", f"{self._dir(addr, target)}/{n}")

    def recover(self) -> list[str]:
        out = []
        for a in self.agents.agents():
            if self.messages(a, "inflight"):
                self.end(a, ok=False)
                out.append(a)
        self.redeliver_orphans()
        return out

    def redeliver_orphans(self) -> list[str]:
        owners = [ROOT, *self.agents.agents()]
        have = {n.removesuffix(".md") for a in owners for box in RECEIVED_BOXES for n in self._names(a, box)}
        out = []
        for a in owners:
            for n in self._names(a, "sent"):
                if n.removesuffix(".md") in have:
                    continue
                try:
                    msg = self._parse(a, "sent", n)
                except Exception:  # noqa: BLE001 - an unreadable file is not ours to fix here
                    continue
                to = norm(msg.to)
                if self.agents.exists(to):
                    self._write(f"{self._dir(to, 'inbox')}/{n}", self.agents.files[f"{self._dir(a, 'sent')}/{n}"])
                    out.append(msg.id)
        return out

    # ------------------------------------------------------------------ MailFingerprint

    def fingerprint(self, addr: str) -> tuple[frozenset[str], frozenset[str]]:
        received = frozenset(n for box in RECEIVED_BOXES for n in self._names(addr, box))
        return received, frozenset(self._names(addr, "sent"))

    # ------------------------------------------------------------------ MessageIndex

    def scan(self) -> list[MessageFile]:
        out = []
        for owner in (ROOT, *self.agents.agents()):
            for box in BOXES:
                for n in self._names(owner, box):
                    key = f"{self._dir(owner, box)}/{n}"
                    meta, error = describe(self.agents.files[key])
                    out.append(MessageFile(self.agents.root / key, owner, box, meta, error, str((meta or {}).get("id") or n.removesuffix(".md")), 1.0))
        return out


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


@dataclass(frozen=True)
class _Fs:
    """The mailboxes on disk with their collaborators (shared by the real harness and by the decorator's)."""

    paths: OrgPaths
    parser: CountingMessageParser
    mailbox: FsMailbox
    batches: FsBatchStore
    index: FsMessageIndex
    meta: StampCachedMetaReader
    harness: MailHarness


def _disk(root: Path) -> tuple[
    Callable[[str, str], None], Callable[[str], str | None], Callable[[str], list[str] | None]
]:
    def put(path: str, text: str) -> None:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def read(path: str) -> str | None:
        target = root / path
        return target.read_text(encoding="utf-8") if target.is_file() else None

    def listing(path: str) -> list[str] | None:
        target = root / path
        return sorted(os.listdir(target)) if target.is_dir() else None

    return put, read, listing


def _fs(tmp_path: Path) -> _Fs:
    paths = OrgPaths(tmp_path)
    failing: list[Callable[[str], bool] | None] = [None]  # which writes fail, switched by the test through ``MailHarness.fail_writes``

    def fails(path: Path) -> bool:
        when = failing[0]
        return when is not None and when(paths.rel(path))

    writer = FailingAtomicWriter(fs_atomic_writer(tmp_path).writer, fails=fails)
    parser, meta = CountingMessageParser(), StampCachedMetaReader()
    directory = fs_agents(tmp_path).directory  # the real directory of agents
    mailbox = FsMailbox(paths, parser, writer)
    batches = FsBatchStore(paths, directory, mailbox, parser, writer)
    index = FsMessageIndex(paths, directory, meta)
    put, read, listing = _disk(tmp_path)

    def fail_writes(when: Callable[[str], bool] | None) -> None:
        failing[0] = when

    harness = MailHarness(
        mailbox, mailbox, batches, mailbox, index, DerivedTaskQuery(mailbox),
        lambda addr: put(f"{addr}/AGENT.md", AGENT_FILE), put, read, listing, lambda path: tmp_path / path, fail_writes, parser,
    )
    return _Fs(paths, parser, mailbox, batches, index, meta, harness)


def fs_mailbox(tmp_path: Path) -> MailHarness:
    return _fs(tmp_path).harness


def memory_mailbox(tmp_path: Path) -> MailHarness:
    box = MemoryMailbox()

    def fail_writes(when: Callable[[str], bool] | None) -> None:
        box.fails = when

    agents = box.agents
    return MailHarness(
        box, box, box, box, box, DerivedTaskQuery(box),
        lambda addr: agents.put(f"{addr}/AGENT.md", AGENT_FILE), agents.put, agents.read, agents.listing,
        lambda path: agents.root / path, fail_writes,
    )


def caching_mailbox(tmp_path: Path) -> MailHarness:
    """The dashboard's decorator over the mailboxes on disk."""
    fs = _fs(tmp_path)
    reader = DirMtimeCachingMailbox(fs.mailbox, fs.paths, fs.parser, FsDirectoryProbe(fs.paths), system_clock(tmp_path))
    h = fs.harness
    return MailHarness(reader, h.writer, h.batches, h.fingerprint, h.index, DerivedTaskQuery(reader),
                       h.agent, h.put, h.read, h.listing, h.path_of, h.fail_writes, fs.parser)


@dataclass(frozen=True)
class ParserHarness:
    parser: MessageParser
    parses: Callable[[], int]  # how many files were actually parsed (not served from the cache) so far


def caching_parser(tmp_path: Path) -> ParserHarness:
    parsed = [0]

    def split(text: str) -> tuple[JsonObject, str]:
        parsed[0] += 1
        return split_frontmatter(text)

    return ParserHarness(CachingMessageParser(split=split), lambda: parsed[0])


def counting_parser(tmp_path: Path) -> ParserHarness:
    parser = CountingMessageParser()
    return ParserHarness(parser, lambda: parser.parses)


IMPLEMENTATIONS: Mapping[type, Sequence[Callable[[Path], object]]] = {
    MessageParser: [caching_parser, counting_parser],
    MailboxReader: [fs_mailbox, memory_mailbox, caching_mailbox],
    MailboxWriter: [fs_mailbox, memory_mailbox],
    BatchStore: [fs_mailbox, memory_mailbox],
    TaskQuery: [fs_mailbox, memory_mailbox],
    MailFingerprint: [fs_mailbox, memory_mailbox],
    MessageIndex: [fs_mailbox, memory_mailbox],
}
