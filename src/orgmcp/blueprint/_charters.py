"""``CharterWriter``: the charter of an agent of a blueprint."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ._protocols import Charters
from ._shapes import Split
from .api import Agent


class CharterWriter(Charters):
    def charter(self, a: Agent, agents: Sequence[Agent], bp: Mapping[str, object], split: Mapping[str, Split]) -> str:
        raise NotImplementedError
