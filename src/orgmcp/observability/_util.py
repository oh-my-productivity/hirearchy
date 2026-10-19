"""Small helpers of the views. (RED: skeleton.)"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime

from ..kernel import JsonObject


def iso(t: datetime | None) -> str | None:
    raise NotImplementedError("red: C-obs-1")


def ms_between(a: datetime, b: datetime) -> float:
    raise NotImplementedError("red: C-obs-1")


def stats(values: Sequence[float]) -> JsonObject:
    raise NotImplementedError("red: C-obs-1")


def plain(value: object) -> object:
    raise NotImplementedError("red: C-obs-1")


def cap(lines: list[str], max_lines: int | None, hint: str) -> list[str]:
    raise NotImplementedError("red: C-obs-1")


def matcher(agent: str | None = None, kind: str | None = None, trace: str | None = None, errors: bool = False) -> Callable[[JsonObject], bool]:
    raise NotImplementedError("red: C-obs-1")
