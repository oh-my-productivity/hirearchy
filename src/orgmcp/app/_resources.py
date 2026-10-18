"""Process-scope resources: what the module globals were, created once per process (ARCHITECTURE.md 2.4). RED skeleton (M2)."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypeVar

from ..kernel import JsonObject, Message, split_frontmatter

M = TypeVar("M", bound=Message)

Split = Callable[[str], tuple[JsonObject, str]]
Stamp = tuple[int, int]  # (mtime_ns, size)


class MessageParser(Protocol):
    """Interim home of the port that ``mail.api`` takes over in step A-mail (its first method, as in section 3.10)."""

    def parse(self, path: Path) -> Message:
        """Parse a message file; cached by (path, mtime_ns, size)."""
        ...


class CachingMessageParser(MessageParser):
    """Parses message files and keeps the parse: a bounded LRU keyed by path, stamped by ``(mtime_ns, size)``.

    Messages are mutable, so the cache holds the parts (frontmatter, body) and every call builds a fresh ``Message``.
    """

    cache: OrderedDict[str, tuple[Stamp, JsonObject, str]]

    def __init__(self, max_entries: int = 50_000, split: Split = split_frontmatter) -> None:
        raise NotImplementedError("red: M2")

    def parse(self, path: Path) -> Message:
        raise NotImplementedError("red: M2")

    def parse_as(self, cls: type[M], path: Path) -> M:
        """``parse`` into a subclass of ``Message`` (what the legacy classmethod ``Message.load`` needs)."""
        raise NotImplementedError("red: M2")

    def clear(self) -> None:
        """Forget every parse (the dict object stays: ``core._PARSED`` is an alias of it)."""
        raise NotImplementedError("red: M2")

    @property
    def max_entries(self) -> int:
        """How many parses are kept; the least recently used go first."""
        raise NotImplementedError("red: M2")

    def _split_text(self, text: str) -> tuple[JsonObject, str]:
        raise NotImplementedError("red: M2")


class ProcessResources:
    """The objects that exist once per process and are shared by every organization runtime in it."""

    message_parser: CachingMessageParser

    def __init__(self, message_parser: CachingMessageParser) -> None:
        raise NotImplementedError("red: M2")

    def reset(self) -> None:
        """Empty every resource (tests start from a clean process); the objects themselves stay."""
        raise NotImplementedError("red: M2")
