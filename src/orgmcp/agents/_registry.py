"""RED skeleton (step A-agents)."""

from __future__ import annotations

from collections.abc import Mapping

from ..kernel import AtomicWriter, OrgLayout
from .api import AgentRegistry


class FsAgentRegistry(AgentRegistry):
    def __init__(self, paths: OrgLayout, writer: AtomicWriter) -> None:
        raise NotImplementedError("red: A-agents")

    def create(self, addr: str, meta: Mapping[str, object], charter_text: str) -> None:
        raise NotImplementedError("red: A-agents")

    def rewrite_charter(self, addr: str, text: str) -> None:
        raise NotImplementedError("red: A-agents")

    def archive(self, addr: str, stamp: str) -> str:
        raise NotImplementedError("red: A-agents")
