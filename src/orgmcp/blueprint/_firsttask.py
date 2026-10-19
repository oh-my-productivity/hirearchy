"""``FirstTaskGiver``: the first request or task of a blueprint."""

from __future__ import annotations

from collections.abc import Mapping

from ..dispatch import TaskAssigner
from ..kernel import Message
from ..services import ServiceCommands
from ._protocols import FirstTasking
from .api import Agent


class FirstTaskGiver(FirstTasking):
    def __init__(self, tasks: TaskAssigner, commands: ServiceCommands) -> None:
        self._tasks = tasks
        self._commands = commands

    def give(self, bp: Mapping[str, object], top: Agent, total: int) -> Message | None:
        raise NotImplementedError
