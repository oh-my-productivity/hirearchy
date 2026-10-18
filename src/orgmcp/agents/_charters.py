"""RED skeleton (step A-agents)."""

from __future__ import annotations

from ..kernel import JsonObject, OrgLayout
from .api import CharterReader


class FsCharterReader(CharterReader):
    def __init__(self, paths: OrgLayout) -> None:
        raise NotImplementedError("red: A-agents")

    def charter(self, addr: str) -> tuple[JsonObject, str]:
        raise NotImplementedError("red: A-agents")

    def memory(self, addr: str) -> str:
        raise NotImplementedError("red: A-agents")
