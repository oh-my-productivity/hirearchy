"""The public surface of ``mail``: the per-agent mailboxes (``inbox``, ``inflight``, ``read``, ``sent``) and the messages in them.

``MailboxReader`` reads them, ``MailboxWriter`` is the only one that puts a message into them, ``BatchStore`` moves the batch of a
run between the boxes, ``TaskQuery`` derives which tasks are open from the messages, ``MailFingerprint`` and ``MessageIndex`` are
the cheap views (file names; front matter of every file) that the idle scheduler and ``observe`` need, and ``MessageParser`` turns
a message file into a ``Message`` (and remembers the parse).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import JsonObject, Message

__all__ = [
    "BatchStore",
    "MailFingerprint",
    "MailboxReader",
    "MailboxWriter",
    "MessageFile",
    "MessageIndex",
    "MetaRead",
    "MessageParser",
    "TaskQuery",
    "moved_past",
    "still_open",
]


MetaRead = tuple[JsonObject | None, str | None, float]  # (front matter, why it is unusable (None when it is usable), mtime in epoch seconds)


@dataclass(frozen=True)
class MessageFile:
    """One message file as ``MessageIndex.scan`` sees it: where it is and what its front matter says (or why it does not parse)."""

    path: Path
    owner: str  # the agent whose directory holds it (``root`` for the human)
    box: str  # ``inbox``, ``inflight``, ``read`` or ``sent``
    meta: JsonObject | None  # the front matter; None when the file could not be read or parsed
    error: str | None  # why ``meta`` is unusable, None for a well-formed message
    id: str  # the ``id`` of the front matter, else the file name without ``.md``
    mtime: float  # modification time in epoch seconds (0.0 when the file could not be read)


def moved_past(task: Message, blocked: Message, received: Sequence[Message]) -> bool:
    """Has the assigner of ``task`` moved past it? ``blocked``: its latest result (``blocked``); ``received``: what its assignee received (pure).

    Yes when a later task from the same sender revises ``task``, or revises what ``task`` revised (a second rework of the same delivery), or when
    the sender gave a verdict (a note with ``feedback``) on any task of its chain after ``blocked``. The chain is the tasks received from the
    sender that are connected to ``task`` through ``revises``, in both directions."""
    mine = [t for t in received if t.type == "task" and t.sender == task.sender]
    chain = {task.id}
    grown = True
    while grown:
        more = {t.id for t in mine if t.revises in chain} | {t.revises for t in mine if t.id in chain and t.revises}
        grown = not more <= chain
        chain |= more
    later = any(
        t.id > task.id and (t.revises == task.id or (task.revises is not None and t.revises == task.revises)) for t in mine
    )
    verdict = any(
        m.type == "note" and m.feedback and m.sender == task.sender and m.reply_to in chain and m.id > blocked.id for m in received
    )
    return later or verdict


def still_open(task: Message, latest: Message | None, received: Sequence[Message]) -> bool:
    """Does the assignee of ``task`` still owe a report on it (pure)? ``latest``: its latest result, None when it has none; ``received``: what the
    assignee received. Yes without a result, and with a ``blocked`` one its assigner has not moved past (``moved_past``: a later task of the same
    sender revises it or what it revised, or the sender gave a verdict on its chain after the block; the user's accept of what it delivered is one
    such verdict, D-E7-2 F-E7-7). No after a ``done`` or ``failed`` result."""
    if latest is None:
        return True
    return latest.status == "blocked" and not moved_past(task, latest, received)


@runtime_checkable
class MessageParser(Protocol):
    def parse(self, path: Path) -> Message:
        """Parse a message file; cached by ``(path, mtime_ns, size)`` (50 000 entries, least recently used go first).
        Every call returns a new ``Message``; CRLF and CR line endings read as LF."""
        ...


@runtime_checkable
class MailboxReader(Protocol):
    def messages(self, addr: str, *boxes: str) -> list[Message]:
        """The messages in the given boxes of ``addr`` (a box that is not there is empty), sorted by id."""
        ...

    def received(self, addr: str) -> list[Message]:
        """``inbox`` + ``inflight`` + ``read``, sorted by id."""
        ...

    def sent(self, addr: str) -> list[Message]:
        """``sent``, sorted by id."""
        ...

    def find_received(self, addr: str, msg_id: str) -> Message | None:
        """The received message with this id, or None."""
        ...

    def find_anywhere(self, addr: str, msg_id: str) -> Message | None:
        """The message with this id in any of the four boxes of ``addr``, found by file name (no scan);
        None when it is not there, the id is not a plain file name, or the file does not parse."""
        ...

    def unread(self, addr: str) -> int:
        """The messages in the inbox that wake the agent: ``wake: false`` ones are held and not counted, an unreadable file counts."""
        ...

    def has_inflight(self, addr: str) -> bool:
        """A batch is in flight: the agent has a run going."""
        ...


@runtime_checkable
class MailboxWriter(Protocol):
    def store(self, msg: Message) -> None:
        """Write the message: the sender's ``sent/`` copy FIRST (not for the runtime), then the recipient's ``inbox/`` copy; each atomic.
        The sender's copy is what charges a budget grant, so a failure between the two can only leave a message charged but
        undelivered (``BatchStore.recover`` delivers it), never delivered but uncharged."""
        ...


@runtime_checkable
class BatchStore(Protocol):
    def begin(self, addr: str) -> list[Message]:
        """Move the inbox into ``inflight/``, held non-waking messages included, and return the whole inflight batch."""
        ...

    def end(self, addr: str, ok: bool) -> None:
        """Success: the inflight batch is processed (``read/``). Failure: put it back in the inbox for a retry (at-least-once).
        A no-op for an agent that no longer exists."""
        ...

    def recover(self) -> list[str]:
        """After a crash: return every inflight batch to its inbox, then ``redeliver_orphans``; the agents whose batch was returned."""
        ...

    def redeliver_orphans(self) -> list[str]:
        """Deliver every sent message whose recipient has no copy (in the inbox, inflight or read of any agent); messages to
        agents that no longer exist and files that do not parse are left alone. The ids that were delivered."""
        ...


@runtime_checkable
class TaskQuery(Protocol):
    def open_tasks(self, addr: str) -> list[Message]:
        """The tasks ``addr`` received that it has not answered with a result."""
        ...

    def outstanding(self, addr: str) -> list[Message]:
        """The tasks ``addr`` sent that have not been answered with a result."""
        ...

    def blocked_tasks(self, addr: str) -> list[Message]:
        """The tasks ``addr`` received whose latest result is ``blocked``: answered, but they may be reported again."""
        ...


@runtime_checkable
class MailFingerprint(Protocol):
    def fingerprint(self, addr: str) -> tuple[frozenset[str], frozenset[str]]:
        """``(received file names, sent file names)``: messages are immutable and named by id, so this set of names determines
        everything derived from the mailbox; listing the directories is a cheap cache key."""
        ...


@runtime_checkable
class MessageIndex(Protocol):
    def scan(self) -> list[MessageFile]:
        """Every message file of root and of the live agents, in box order, front matter parsed once (cached by path + mtime + size)."""
        ...

    def meta_of(self, path: Path) -> MetaRead:
        """The front matter of ONE message file, as ``scan`` reads it (same cache, same findings): ``(front matter, why it is unusable, mtime)``;
        ``(None, "unreadable (<error type>)", 0.0)`` for a file that cannot be read."""
        ...
