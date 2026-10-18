"""The parse cache of message files: what ``core._load_message`` / ``core._PARSED`` was (a process resource, ARCHITECTURE.md 2.4)."""

from __future__ import annotations

import os
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
    """Parses message files and keeps the parse: a bounded LRU keyed by path, stamped by ``(mtime_ns, size)``.

    Messages are mutable, so the cache holds the parts (frontmatter, body) and every call builds a fresh ``Message``.
    """

    def __init__(self, max_entries: int = 50_000, split: Split = split_frontmatter) -> None:
        self.cache: OrderedDict[str, tuple[Stamp, JsonObject, str]] = OrderedDict()  # LRU: the least recently used first
        self._max_entries = max_entries
        self._split = split

    @property
    def max_entries(self) -> int:
        """How many parses are kept; the least recently used go first."""
        return self._max_entries

    def parse(self, path: Path) -> Message:
        return self.parse_as(Message, path)

    def parse_as(self, cls: type[M], path: Path) -> M:
        """``parse`` into a subclass of ``Message`` (what the legacy classmethod ``Message.load`` needs)."""
        key = str(path)
        with open(path, "rb") as f:
            st = os.fstat(f.fileno())
            stamp = (st.st_mtime_ns, st.st_size)
            hit = self.cache.get(key)
            if hit is not None and hit[0] == stamp:
                try:
                    self.cache.move_to_end(key)
                except KeyError:  # evicted by another thread: harmless
                    pass
                meta, body = hit[1], hit[2]
            else:
                text = f.read().decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")  # like read_text
                meta, body = self._split_text(text)
                self.cache[key] = (stamp, meta, body)
                while len(self.cache) > self.max_entries:
                    try:
                        self.cache.popitem(last=False)
                    except KeyError:
                        break
        return cls.from_parts(meta, body, path)

    def clear(self) -> None:
        """Forget every parse (the dict object stays: ``core._PARSED`` is an alias of it)."""
        self.cache.clear()

    def _split_text(self, text: str) -> tuple[JsonObject, str]:
        return self._split(text)
