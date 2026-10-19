"""``FingerprintTaskViews``: the task views of an agent, recomputed only when its set of message files changes (moved from ``Scheduler._task_view``)."""

from __future__ import annotations

from collections.abc import Callable, Collection

from ..kernel import Message
from ..mail import MailFingerprint, TaskQuery
from ._ports import TaskViews


class FingerprintTaskViews(TaskViews):
    def __init__(self, tasks: TaskQuery, fingerprints: MailFingerprint) -> None:
        self._tasks = tasks
        self._fingerprints = fingerprints
        self._memo: dict[str, tuple[tuple[frozenset[str], frozenset[str]], dict[str, list[Message]]]] = {}

    def open_tasks(self, addr: str) -> list[Message]:
        raise NotImplementedError("red: C-stalls")

    def outstanding(self, addr: str) -> list[Message]:
        raise NotImplementedError("red: C-stalls")

    def retain(self, agents: Collection[str]) -> None:
        raise NotImplementedError("red: C-stalls")

    def rebound(self, tasks: TaskQuery, fingerprints: MailFingerprint) -> FingerprintTaskViews:
        """Views over other ports that remember what these remember."""
        raise NotImplementedError("red: C-stalls")

    def _view(self, addr: str, name: str, compute: Callable[[str], list[Message]]) -> list[Message]:
        raise NotImplementedError("red: C-stalls")
