"""``MailClientRework``: which of the reworks an agent received come from the client of a service case, not from its manager."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..agents import AgentDirectory
from ..kernel import Message
from ..mail import MailboxReader
from ._ports import ClientRework


class MailClientRework(ClientRework):
    def __init__(self, agents: AgentDirectory, mail: MailboxReader) -> None:
        pass  # red: C-health

    def driven(self, tasks: Sequence[Message], results: Mapping[str, Message]) -> set[str]:
        raise NotImplementedError("red: C-health")
