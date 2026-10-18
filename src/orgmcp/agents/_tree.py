"""RED skeleton (step A-agents)."""

from __future__ import annotations

from collections.abc import Callable

from ..kernel import JsonObject
from .api import AgentDirectory


def valid_address(addr: str) -> bool:
    raise NotImplementedError("red: A-agents")


def parse_charter(text: str) -> tuple[JsonObject, str]:
    raise NotImplementedError("red: A-agents")


def walk_agents(children: Callable[[str], list[str]]) -> list[str]:
    raise NotImplementedError("red: A-agents")


def walk_subtree(addr: str, children: Callable[[str], list[str]]) -> list[str]:
    raise NotImplementedError("red: A-agents")


class TreeDirectory(AgentDirectory):
    def require(self, addr: str) -> str:
        raise NotImplementedError("red: A-agents")

    def agents(self) -> list[str]:
        raise NotImplementedError("red: A-agents")

    def subtree(self, addr: str) -> list[str]:
        raise NotImplementedError("red: A-agents")
