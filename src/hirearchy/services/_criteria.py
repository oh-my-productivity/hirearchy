"""The stored versions of a contract and the basis each records, as ``number_criteria`` takes them."""

from __future__ import annotations

from ._parse import contract_of
from .api import ServiceStore


def stored_versions(store: ServiceStore, owner: str, name: str) -> list[tuple[int, str, list[str]]]:
    """``(version, defined_by, acceptance)`` of every contract version that is kept (the archive, then the current one), oldest first."""
    found = []
    for _, meta, body in store.versions(owner, name, "SERVICE"):
        contract = contract_of(owner, name, meta, body, None)
        found.append((contract.version, contract.defined_by or "", contract.acceptance))
    return found


def stored_basis(store: ServiceStore, owner: str, name: str) -> dict[int, tuple[str, bool]]:
    """``version -> (answers, user)`` of every contract version that is kept: the rejection the version answers (``""`` when none) and whether it
    is a change the user asked for on their own. A version written before 0a.2 has neither."""
    found = {}
    for _, meta, body in store.versions(owner, name, "SERVICE"):
        contract = contract_of(owner, name, meta, body, None)
        found[contract.version] = (contract.answers, contract.initiated == "user")
    return found
