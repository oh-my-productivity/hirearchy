"""The ``.gitignore`` of the organization (RED skeleton: nothing is implemented yet)."""

from __future__ import annotations

from collections.abc import Sequence

from ..kernel import AtomicWriter, OrgLayout
from .api import IgnoreList


class FsIgnoreList(IgnoreList):
    def __init__(self, paths: OrgLayout, writer: AtomicWriter) -> None:
        self._paths = paths
        self._writer = writer

    def write_initial(self, lines: Sequence[str]) -> None:
        raise NotImplementedError

    def ensure(self, lines: Sequence[str]) -> None:
        raise NotImplementedError

    def ensure_runtime_files(self) -> None:
        raise NotImplementedError
