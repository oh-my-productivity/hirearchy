"""What an amendment of a contract changes, and how it is told to the owner."""

from __future__ import annotations

from collections.abc import Sequence

from ..kernel import JsonObject, OrgError
from ._lines import criteria_lines
from ._protocols import ContractAmendment
from .api import Contract


def _described(deliverable: JsonObject) -> str:
    raise NotImplementedError


def _inputs_listing(items: Sequence[JsonObject]) -> list[str]:
    raise NotImplementedError


class ContractAmender(ContractAmendment):
    """Criteria are added and removed by their exact text; the owner is told line by line what changed."""

    def numbered(self, items: Sequence[str], indent: str = "") -> str:
        raise NotImplementedError

    def amended_criteria(self, name: str, current: Sequence[str], add: object, remove: object) -> list[str]:
        raise NotImplementedError

    def changes(self, old: Contract, new: Contract) -> list[str]:
        raise NotImplementedError

    def diff(self, old: Contract, new: Contract, changes: Sequence[str], where: str) -> str:
        raise NotImplementedError
