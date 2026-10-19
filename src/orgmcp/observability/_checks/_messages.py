"""(a) The message files parse, ids are unique, sender and recipient copies match."""

from __future__ import annotations

from collections.abc import Sequence

from ...agents import AgentDirectory
from ...kernel import JsonObject, OrgLayout
from ...mail import MessageFile
from .._ports import IntegrityCheck


class MessagesIntact(IntegrityCheck):
    def __init__(self, layout: OrgLayout, agents: AgentDirectory) -> None:
        self._layout, self._agents = layout, agents

    def run(self, files: Sequence[MessageFile], now: float) -> JsonObject:
        raise NotImplementedError("red: C-obs-2")
