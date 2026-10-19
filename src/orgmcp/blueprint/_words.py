"""``ServiceWords``: the sentences about services that the block for the user and the details have in common."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..services import ContractNormalizer
from ._protocols import PlanWords
from .api import Agent


class ServiceWords(PlanWords):
    def __init__(self, normalizer: ContractNormalizer) -> None:
        self._normalizer = normalizer

    def input_words(self, sv: Mapping[str, object]) -> str:
        raise NotImplementedError

    def delivery(self, sv: Mapping[str, object], agents: Sequence[Agent], bp: Mapping[str, object]) -> str:
        raise NotImplementedError

    def request_words(self, bp: Mapping[str, object]) -> str:
        raise NotImplementedError

    def reflection_line(self, owner: str) -> str:
        raise NotImplementedError
