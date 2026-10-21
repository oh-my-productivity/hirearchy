"""``FingerprintTaskViews``: the task views of an agent, recomputed only when its set of message files changes (moved from ``Scheduler._task_view``)."""

from __future__ import annotations

from collections.abc import Callable, Collection

from ..kernel import Message
from ..mail import MailFingerprint, TaskQuery
from ._ports import TaskViews


class FingerprintTaskViews(TaskViews):
    """Messages are immutable and named by id, so the file names of an agent's mailboxes (a message moving from inbox to inflight to read stays the
    same message) determine both views. An idle pass therefore lists a few directories instead of parsing every message ever received or sent."""

    def __init__(self, tasks: TaskQuery, fingerprints: MailFingerprint) -> None:
        self._tasks = tasks
        self._fingerprints = fingerprints
        self._memo: dict[str, tuple[tuple[frozenset[str], frozenset[str]], dict[str, list[Message]]]] = {}  # agent -> (fingerprint, views)

    def open_tasks(self, addr: str) -> list[Message]:
        return self._view(addr, "open_tasks", self._tasks.open_tasks)

    def outstanding(self, addr: str) -> list[Message]:
        return self._view(addr, "outstanding", self._tasks.outstanding)

    def retain(self, agents: Collection[str]) -> None:
        for gone in set(self._memo) - set(agents):
            del self._memo[gone]

    def rebound(self, tasks: TaskQuery, fingerprints: MailFingerprint) -> FingerprintTaskViews:
        """Views over other ports that remember what these remember."""
        other = FingerprintTaskViews(tasks, fingerprints)
        other._memo = self._memo
        return other

    def _view(self, addr: str, name: str, compute: Callable[[str], list[Message]]) -> list[Message]:
        fingerprint = self._fingerprints.fingerprint(addr)
        cached = self._memo.get(addr)
        if cached is None or cached[0] != fingerprint:
            cached = self._memo[addr] = (fingerprint, {})
        if name not in cached[1]:
            cached[1][name] = compute(addr)
        return cached[1][name]
