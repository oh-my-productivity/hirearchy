"""``FsProfileStore``: the profiles as ``<agents directory>/<name>.json``."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..kernel import AtomicWriter, Provider
from .api import ProfileStore


class FsProfileStore(ProfileStore):
    def __init__(self, directory: Provider[Path], writer: AtomicWriter) -> None:
        self._directory = directory  # asked on every use: ``~/.kiro/agents`` follows HOME, which may change between two calls
        self._writer = writer

    def read(self, name: str) -> dict[str, object] | None:
        raise NotImplementedError

    def write(self, name: str, data: Mapping[str, object]) -> None:
        raise NotImplementedError
