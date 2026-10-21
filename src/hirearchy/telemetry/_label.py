"""The name of this process."""

from __future__ import annotations

from ..eventlog import PROCS
from .api import ProcessLabel


class MutableProcessLabel(ProcessLabel):
    """``cli`` until named; a name that is not one of ``PROCS`` means ``cli``."""

    def __init__(self) -> None:
        self._name = "cli"

    def get(self) -> str:
        return self._name

    def set(self, name: str) -> None:
        self._name = name if name in PROCS else "cli"
