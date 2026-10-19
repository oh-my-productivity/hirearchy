"""``PlainAccessWords``: what an agent may touch, in the words of the block for the user."""

from __future__ import annotations

from ._protocols import AccessReport, AccessWording
from .api import Agent


class PlainAccessWords(AccessWording):
    def __init__(self, access: AccessReport) -> None:
        self._access = access

    def describe(self, a: Agent) -> str:
        raise NotImplementedError
