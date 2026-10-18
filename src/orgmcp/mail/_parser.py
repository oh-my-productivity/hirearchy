"""The parse cache of message files (skeleton: red step of A-mail)."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from ..kernel import JsonObject, Message, split_frontmatter
from .api import MessageParser

M = TypeVar("M", bound=Message)

Split = Callable[[str], tuple[JsonObject, str]]
Stamp = tuple[int, int]  # (mtime_ns, size)


class CachingMessageParser(MessageParser):
    cache: OrderedDict[str, tuple[Stamp, JsonObject, str]]

    def __init__(self, max_entries: int = 50_000, split: Split = split_frontmatter) -> None:
        raise NotImplementedError

    @property
    def max_entries(self) -> int:
        raise NotImplementedError

    def parse(self, path: Path) -> Message:
        raise NotImplementedError

    def parse_as(self, cls: type[M], path: Path) -> M:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    def _split_text(self, text: str) -> tuple[JsonObject, str]:
        raise NotImplementedError
