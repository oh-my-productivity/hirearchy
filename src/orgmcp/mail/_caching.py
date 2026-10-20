"""The dashboard's decorator of the mailbox reader: boxes kept per directory change (what ``LenientOrg._box`` and its neighbours did)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..kernel import Clock, Message, OrgLayout, norm
from ._reads import DerivedMailboxReads
from .api import MailboxReader, MessageParser

CACHE_TRUST = 2.0  # a directory modified less than this many seconds before it was listed is listed again next time


@runtime_checkable
class DirectoryProbe(Protocol):
    def mtime(self, addr: str, name: str) -> int:
        """``mtime_ns`` of ``<addr>/<name>`` (the agent's directory itself for ``name`` ``""``); -1 when it is not there."""
        ...


class FsDirectoryProbe(DirectoryProbe):
    def __init__(self, layout: OrgLayout) -> None:
        self._layout = layout

    def mtime(self, addr: str, name: str) -> int:
        path = self._layout.agent_dir(addr)
        try:
            return os.stat(path / name if name else path).st_mtime_ns
        except OSError:
            return -1


class DirMtimeCachingMailbox(DerivedMailboxReads):
    """Keeps the parsed messages of every box until its directory changes (``probe`` tells when), and skips the files that do not parse.

    A box is listed again when the mtime of its directory differs from the one it was listed at, or when that listing was made so soon
    after the last change that a second change within the same coarse timestamp could have gone unseen (``CACHE_TRUST``). Messages are
    immutable, so a file seen before is the same message: its object is kept, and an unchanged box gives the very same list, so that
    everything derived from it stays valid. A file that cannot be read is left out and reported in ``bad`` (path relative to the
    organization -> why); one that moved away between the listing and the read is neither.
    """

    def __init__(self, inner: MailboxReader, layout: OrgLayout, parser: MessageParser, probe: DirectoryProbe, clock: Clock) -> None:
        self._inner = inner
        self._layout = layout
        self._parser = parser
        self._probe = probe
        self._clock = clock
        self._box_cache: dict[tuple[str, str], tuple[int, bool, list[Message]]] = {}
        self._bad_boxes: dict[tuple[str, str], dict[str, str]] = {}
        self._merged: dict[tuple[str, tuple[str, ...]], tuple[list[list[Message]], list[Message]]] = {}

    @property
    def bad(self) -> dict[str, str]:
        """Files that could not be read: path (relative to the org) -> why."""
        out: dict[str, str] = {}
        for d in self._bad_boxes.values():
            out.update(d)
        return out

    # ------------------------------------------------------------------ MailboxReader

    def messages(self, addr: str, *boxes: str) -> list[Message]:
        key = (norm(addr), boxes)
        lists = [self._box(addr, box) for box in boxes]
        hit = self._merged.get(key)
        if hit is not None and len(hit[0]) == len(lists) and all(a is b for a, b in zip(hit[0], lists)):
            return hit[1]
        merged = sorted((m for lst in lists for m in lst), key=lambda m: m.id)
        self._merged[key] = (lists, merged)
        return merged

    def find_anywhere(self, addr: str, msg_id: str) -> Message | None:
        return self._inner.find_anywhere(addr, msg_id)

    def unread(self, addr: str) -> int:
        """Inbox messages that wake the agent (an unreadable file still counts as mail, like in ``FsMailbox.unread``)."""
        msgs = self._box(addr, "inbox")
        return sum(1 for m in msgs if m.wake) + self._bad_in(addr, "inbox")

    def has_inflight(self, addr: str) -> bool:
        return bool(self._box(addr, "inflight")) or self._bad_in(addr, "inflight") > 0

    # ------------------------------------------------------------------ the cache

    def _trusted(self, listed_at: int, mtime: int) -> bool:
        """A listing is reused only if the directory had been quiet for a while when it was made (coarse-mtime safe)."""
        return (listed_at - mtime) > CACHE_TRUST * 1e9

    def _box(self, addr: str, box: str) -> list[Message]:
        key = (norm(addr), box)
        mtime = self._probe.mtime(key[0], box)
        if mtime < 0:
            self._box_cache.pop(key, None)
            self._bad_boxes.pop(key, None)
            return []
        hit = self._box_cache.get(key)
        if hit is not None and hit[0] == mtime and hit[1]:
            return hit[2]
        d = self._layout.box(addr, box)
        listed_at = int(self._clock.time() * 1e9)
        previous = {m.path.name: m for m in hit[2] if m.path is not None} if hit is not None else {}
        out: list[Message] = []
        bad: dict[str, str] = {}
        try:
            names = sorted(e.name for e in os.scandir(d) if e.name.endswith(".md") and not e.name.startswith("."))
        except OSError:
            names = []
        for n in names:
            old = previous.get(n)
            if old is not None:  # messages are immutable: a file seen before is the same message
                out.append(old)
                continue
            p = d / n
            try:
                out.append(self._parser.parse(p))
            except FileNotFoundError:
                continue  # moved between the listing and the read: the next tick sees it where it went
            except Exception as exc:  # noqa: BLE001 - yaml errors, bad numbers, bad encoding, ...
                bad[self._rel(p)] = f"{type(exc).__name__}: {str(exc).splitlines()[0][:80] if str(exc) else ''}".rstrip(": ")
        if hit is not None and len(out) == len(hit[2]) and all(a is b for a, b in zip(out, hit[2])):
            out = hit[2]  # unchanged: the same list object, so everything derived from it stays valid
        self._box_cache[key] = (mtime, self._trusted(listed_at, mtime), out)
        if bad:
            self._bad_boxes[key] = bad
        else:
            self._bad_boxes.pop(key, None)
        return out

    def _bad_in(self, addr: str, box: str) -> int:
        return len(self._bad_boxes.get((norm(addr), box), ()))

    def _rel(self, p: Path) -> str:
        try:
            return self._layout.rel(p)
        except ValueError:
            return str(p)
