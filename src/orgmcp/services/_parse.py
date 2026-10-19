"""The contract and the playbook of a service as values, parsed from the frontmatter and the body of their files."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import SupportsInt, cast

from ..kernel import JsonObject, parse_time
from .api import Contract, Playbook


def as_int(value: object, default: int = 0) -> int:
    """``value`` as a whole number; ``default`` for what is none (absent, a bool, text that is no number)."""
    raise NotImplementedError


def as_time(value: object) -> datetime | None:
    """The time a frontmatter field holds; None when it is empty or unreadable."""
    raise NotImplementedError


def _items(value: object) -> list[object]:
    """What a list-valued field holds, as the files have always been read: an empty field has no items, anything else is iterated."""
    raise NotImplementedError


def contract_of(owner: str, name: str, meta: JsonObject, body: str, path: Path | None) -> Contract:
    """The contract a ``SERVICE.md`` describes."""
    raise NotImplementedError


def playbook_of(meta: JsonObject, body: str, path: Path | None) -> Playbook:
    """The playbook a ``PLAYBOOK.md`` describes."""
    raise NotImplementedError
