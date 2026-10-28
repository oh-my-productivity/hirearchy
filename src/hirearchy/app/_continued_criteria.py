"""The criteria of the retired copy a definition would continue (design 5.2, L26): what an extension's service must repeat."""

from __future__ import annotations

from ..blueprint._protocols import ContinuedCriteria
from ..services._continue import copy_contracts
from ..services._protocols import ContinuedServices


class RecordedContinuedCriteria(ContinuedCriteria):
    """The newest retired copy of the owner's service ``name`` that a request of it has a result for, as ``define_service`` finds it."""

    def __init__(self, continued: ContinuedServices) -> None:
        self._continued = continued

    def criteria(self, owner: str, name: str) -> tuple[str, ...] | None:
        copy = self._continued.continued(owner, name)
        if copy is None:
            return None
        contracts = copy_contracts(owner, name, copy)
        return tuple(contracts[-1].acceptance) if contracts else None
