"""RED: the pure functions of the vocabulary (skeletons)."""

from __future__ import annotations

from datetime import datetime

from ..kernel import JsonObject


def percentile(values: list[float], p: float) -> float | None:
    raise NotImplementedError("red: C-obs-1")


def parse_when(text: str | datetime | None, now: datetime | None = None) -> datetime | None:
    raise NotImplementedError("red: C-obs-1")


def fmt_rel(ms: float) -> str:
    raise NotImplementedError("red: C-obs-1")


def normalize_refusal(text: str) -> str:
    raise NotImplementedError("red: C-obs-1")


def is_error(ev: JsonObject) -> bool:
    raise NotImplementedError("red: C-obs-1")


def format_event(ev: JsonObject, width: int = 300) -> str:
    raise NotImplementedError("red: C-obs-1")
