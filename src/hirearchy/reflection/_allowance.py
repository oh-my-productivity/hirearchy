"""``CaseAllowanceOf``: what is left of the runs the user approved for a case, derived from the case and the contract of its service."""

from __future__ import annotations

from ..services import CaseAllowance, ServiceCatalog
from .api import CaseHistory, user_approved, user_committed


class CaseAllowanceOf(CaseAllowance):
    """The approved runs of the case that holds the revised task (``user_approved``: the contract's budget, raised to the highest ceiling root set),
    less what the user's requests used or the team still holds for them (``user_committed``; the user's runs that a relayed result carried back are
    no longer held, D-E6-2). After a user rework of 1 run sent with nothing left, ``left`` is one lower: that run is committed and not approved
    (``Case.unapproved_reworks``, D-E7-2 A2). None when the task is in no case of the service, the service has no contract, or the case's client is
    an agent (it has no user)."""

    def __init__(self, history: CaseHistory, catalog: ServiceCatalog) -> None:
        self._history = history
        self._catalog = catalog

    def left(self, owner: str, service: str, revises: str) -> int | None:
        contract = self._catalog.read_contract(owner, service)
        case = next((c for c in self._history.cases(owner, service) if revises in {t.id for t in c.tasks}), None)
        if contract is None or case is None or case.client_kind != "human":
            return None
        return user_approved(case, contract.budget) - user_committed(case)
