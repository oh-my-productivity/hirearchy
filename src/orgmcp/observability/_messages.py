"""The messages of the history as the views see them: one record per id, the boxes that hold a copy. (RED: skeleton.)"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from ..mail import MessageFile


@dataclass
class Msg:
    id: str
    sender: str
    to: str
    type: str
    title: str
    status: str | None
    budget: int
    reply_to: str | None
    revises: str | None
    service: str | None
    feedback: str | None
    wake: bool
    trace: str | None  # as recorded in the frontmatter
    t: datetime
    boxes: list[tuple[str, str]] = field(default_factory=list)  # (owner, box) of every copy


def build_messages(files: Sequence[MessageFile]) -> dict[str, Msg]:
    raise NotImplementedError("red: C-obs-1")
