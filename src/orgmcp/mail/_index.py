"""The front matter of every message file (skeleton: red step of A-mail)."""

from __future__ import annotations

from collections.abc import MutableMapping
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..agents import AgentDirectory
from ..kernel import JsonObject, OrgLayout
from .api import MessageFile, MessageIndex

MetaRead = tuple[JsonObject | None, str | None, float]  # (front matter, why it is unusable, mtime in epoch seconds)


@runtime_checkable
class MetaReader(Protocol):
    def read(self, path: Path) -> MetaRead:
        """The front matter of a message file, why it cannot be used (None when it can), and the file's mtime."""
        ...


def describe(text: str) -> tuple[JsonObject | None, str | None]:
    """The front matter of the text of a message file and what is wrong with it (None when nothing is)."""
    raise NotImplementedError


class StampCachedMetaReader(MetaReader):
    cache: MutableMapping[tuple[str, int, int], tuple[JsonObject | None, str | None]]

    def __init__(self, max_entries: int = 50_000) -> None:
        raise NotImplementedError

    @property
    def max_entries(self) -> int:
        raise NotImplementedError

    def _read_text(self, path: Path) -> str:
        raise NotImplementedError

    def read(self, path: Path) -> MetaRead:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError


class FsMessageIndex(MessageIndex):
    def __init__(self, layout: OrgLayout, agents: AgentDirectory, meta: MetaReader) -> None:
        raise NotImplementedError

    def scan(self) -> list[MessageFile]:
        raise NotImplementedError
