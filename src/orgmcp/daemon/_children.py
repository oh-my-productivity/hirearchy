"""The schedulers this process started, until they end."""

from __future__ import annotations

from ..processes import ProcessHandle
from ._ports import Children


class ChildRegistry(Children):
    """Schedulers this process started: reaped when they end, so that they never linger as zombies (what ``scheduler._children`` was)."""

    def __init__(self) -> None:
        self._children: dict[int, ProcessHandle] = {}

    def adopt(self, handle: ProcessHandle) -> None:
        self._children[handle.pid] = handle

    def reap(self) -> None:
        for pid, handle in list(self._children.items()):
            if handle.poll() is not None:
                del self._children[pid]
