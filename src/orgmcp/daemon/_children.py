"""The schedulers this process started, until they end."""

from __future__ import annotations

from ..processes import ProcessHandle
from ._ports import Children


class ChildRegistry(Children):
    def __init__(self) -> None:
        self._children: dict[int, ProcessHandle] = {}

    def adopt(self, handle: ProcessHandle) -> None:
        raise NotImplementedError

    def reap(self) -> None:
        raise NotImplementedError
