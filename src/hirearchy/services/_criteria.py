"""The stored versions of a contract and the basis each records, as ``number_criteria`` takes them."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ._parse import contract_of
from .api import AmendmentBasis, Contract, Criterion, Rejection, ServiceStore, criteria_of, number_criteria


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


def answering_version(store: ServiceStore, owner: str, name: str, note: str) -> int:
    """The first stored ``SERVICE`` version (oldest first) whose frontmatter ``answers`` is the rejection ``note``; 0 when none. The one reader of
    "a contract version answers this rejection", for the definer (one answer per rejection) and for ``feedback`` (no second link)."""
    for _, meta, body in store.versions(owner, name, "SERVICE"):
        contract = contract_of(owner, name, meta, body, None)
        if note and contract.answers == note:
            return contract.version
    return 0


def unanswered(basis: AmendmentBasis, store: ServiceStore, owner: str, name: str) -> list[Rejection]:
    """The rejections of ``basis`` that have no recorded answer, oldest first (the order of ``basis``): neither a human link note
    (``Rejection.answered``) nor a stored contract version that answers them (:func:`answering_version`). The one rule of "answered" for the
    retirement, the definer, the request and the client's accept: a rejection whose answering version exists but whose link write failed is answered."""
    return [r for r in basis.rejections if not r.answered and answering_version(store, owner, name, r.note) == 0]


def amendment_ids(versions: Sequence[tuple[int, str, Sequence[str]]], version: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """``(added, removed)``: the ids of the criteria ``version`` has and the stored version before it lacks, in the order of ``version``, and of
    those the version before it has and ``version`` lacks (pure). Numbered by :func:`number_criteria` over all ``versions``; ``((), ())`` for
    the first version or one that is not among them."""
    ids = {c.text: c.id for c in number_criteria(versions)}
    texts = {v: list(acceptance) for v, _, acceptance in versions}
    earlier = [v for v in texts if v < version]
    if version not in texts or not earlier:
        return (), ()
    before, now = texts[max(earlier)], texts[version]
    return tuple(ids[t] for t in now if t not in before), tuple(ids[t] for t in before if t not in now)


def answer_ids(store: ServiceStore, owner: str, name: str, version: int) -> tuple[str, ...]:
    """The ids the link of an answering ``version`` names: the criteria it added, in order; when it added none, the ones it removed. The definer
    computes the product's link with the same rule (``amendment_ids``) and ``feedback`` compares a recovery link with it."""
    added, removed = amendment_ids(stored_versions(store, owner, name), version)
    return added or removed


def version_in_force(contracts: Sequence[Contract], when: datetime | None) -> Contract | None:
    """The version in force at ``when`` among ``contracts`` (oldest first, as :meth:`ServiceStore.versions` lists them): the latest whose ``defined``
    is at or before ``when``; the oldest when none is (a version written before ``defined`` existed, no time); None when there is no version (pure)."""
    if not contracts:
        return None
    dated = [c for c in contracts if when is not None and c.defined is not None and c.defined <= when]
    return max(dated, key=lambda c: c.version) if dated else contracts[0]


def in_force(store: ServiceStore, owner: str, name: str, when: datetime | None) -> tuple[int, list[Criterion]]:
    """The stored contract version in force at ``when`` and its criteria, with their ids: the latest whose ``defined`` is at or before ``when``;
    the oldest when none is (a version written before ``defined`` existed, a missing history file, no time) or ``(0, [])`` for a service the store
    does not have. The current version is always stored."""
    contracts = [contract_of(owner, name, meta, body, None) for _, meta, body in store.versions(owner, name, "SERVICE")]
    chosen = version_in_force(contracts, when)
    if chosen is None:
        return 0, []
    numbered = number_criteria(
        [(c.version, c.defined_by or "", c.acceptance) for c in contracts], {c.version: (c.answers, c.initiated == "user") for c in contracts},
    )
    return chosen.version, criteria_of(numbered, chosen.acceptance)
