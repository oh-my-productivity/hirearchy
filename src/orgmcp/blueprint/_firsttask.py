"""``FirstTaskGiver``: the first request or task of a blueprint."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from ..dispatch import TaskAssigner
from ..kernel import ROOT, Message
from ..services import ServiceCommands
from ._protocols import FirstTasking
from ._view import criteria_of, deliverable_of, items, s, task_of
from .api import Agent


class FirstTaskGiver(FirstTasking):
    def __init__(self, tasks: TaskAssigner, commands: ServiceCommands) -> None:
        self._tasks = tasks
        self._commands = commands

    def give(self, bp: Mapping[str, object], top: Agent, total: int) -> Message | None:
        task = task_of(bp) if isinstance(bp.get("task"), dict) else None
        if task is not None and "service" in task:
            return self._commands.request(ROOT, s(task["service"]), cast(Mapping[str, object], task.get("inputs") or {}), title=s(task.get("title")), note=s(task.get("note")))
        if task is not None:
            crit = criteria_of(bp)
            acceptance = "\n".join(f"{i}. {c}" for i, c in enumerate(crit, 1))
            goal = s(task.get("goal"))
            d = deliverable_of(bp)
            if d.get("description"):
                spec = ", ".join(x for x in (s(d.get("format")), f"at most {d['max_words']} words" if d.get("max_words") else "") if x)
                goal += f"\n\nDeliverable: {s(d['description'])}" + (f" ({spec})" if spec else "") + ". Report its path as an artifact."
            return self._tasks.delegate(ROOT, top.addr, s(task["title"]), goal, acceptance, items(task.get("inputs")), total)
        return None
