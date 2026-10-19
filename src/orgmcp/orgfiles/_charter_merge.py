"""What a rewrite of a charter does to its frontmatter: the keys the new text leaves out are kept, and the writer is told."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..kernel import JsonObject


def _short(value: object, limit: int = 80) -> str:
    raise NotImplementedError


def charter_change_note(addr: str, old: JsonObject, written: JsonObject, merged: JsonObject) -> str:
    """What a charter rewrite did to the frontmatter: keys kept from the old one, keys changed (old -> new), added."""
    raise NotImplementedError


@runtime_checkable
class CharterMerge(Protocol):
    def merge(self, addr: str, old: JsonObject, written: JsonObject) -> tuple[JsonObject, str]:
        """``(frontmatter to write, note for the writer)``: every key of ``old`` that ``written`` does not set is kept."""
        ...


class CharterMerger(CharterMerge):
    def merge(self, addr: str, old: JsonObject, written: JsonObject) -> tuple[JsonObject, str]:
        raise NotImplementedError
