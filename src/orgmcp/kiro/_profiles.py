"""``FsProfileStore``: the profiles as ``<agents directory>/<name>.json``."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..kernel import AtomicWriter, Provider
from ._profile_document import parse_profile, render_profile
from .api import ProfileStore


class FsProfileStore(ProfileStore):
    def __init__(self, directory: Provider[Path], writer: AtomicWriter) -> None:
        self._directory = directory  # asked on every use: ``~/.kiro/agents`` follows HOME, which may change between two calls
        self._writer = writer

    def _path(self, name: str) -> Path:
        return self._directory() / f"{name}.json"

    def read(self, name: str) -> dict[str, object] | None:
        try:
            text = self._path(name).read_text(encoding="utf-8")
        except (OSError, ValueError):  # missing, a directory, not UTF-8: as good as missing
            return None
        return parse_profile(text)

    def write(self, name: str, data: Mapping[str, object]) -> None:
        self._writer.write(self._path(name), render_profile(data))  # temp file + rename: never a half-written profile
