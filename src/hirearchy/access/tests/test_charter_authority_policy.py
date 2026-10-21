"""``CharterAuthorityPolicy`` judges a grant by the grantor's own charter and by the scopes it is given."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from hirearchy.access import AccessScopes, AuthorityPolicy
from hirearchy.access._authority import CharterAuthorityPolicy
from hirearchy.agents.testing import MemoryAgents
from hirearchy.kernel import OrgError, OrgPaths


ROOT = Path("/memory/org")


class FixedScopes(AccessScopes):
    """What the scopes say, whatever the charters say."""

    def __init__(self, workspace: Path | None, inputs: list[Path]) -> None:
        self.workspace = workspace
        self.inputs = inputs

    def workspace_of(self, addr: str) -> Path | None:
        return self.workspace

    def inputs_of(self, addr: str) -> list[Path]:
        return self.inputs

    def readable_roots(self, addr: str) -> list[Path]:
        raise AssertionError("the policy never asks for the readable roots")

    def unconfined_read(self, meta: Mapping[str, object]) -> bool:
        raise AssertionError("the policy never asks whether a charter is legacy")


def policy(scopes: AccessScopes, charter: str = "---\nrole: R\ntools: [read]\n---\nbody\n") -> CharterAuthorityPolicy:
    agents = MemoryAgents()
    agents.put("ceo/AGENT.md", charter)
    return CharterAuthorityPolicy(OrgPaths(ROOT), agents, scopes)


def test_it_is_an_authority_policy() -> None:
    assert isinstance(policy(FixedScopes(None, [])), AuthorityPolicy)


def test_the_bases_of_the_inputs_are_the_workspace_then_the_inputs_the_scopes_name() -> None:
    scopes = FixedScopes(Path("/a/ws"), [Path("/a/in")])
    policy(scopes).check_authority("ceo", [], None, ["/a/ws/x", "/a/in/y"])
    with pytest.raises(OrgError, match=r"^a report's inputs must be inside your inputs or workspace \(/a/ws, /a/in\): /a/other$"):
        policy(scopes).check_authority("ceo", [], None, ["/a/other"])


def test_without_bases_nothing_can_be_assigned() -> None:
    with pytest.raises(OrgError, match="^you have no workspace or inputs, so you cannot assign inputs$"):
        policy(FixedScopes(None, [])).check_authority("ceo", [], None, ["/a/x"])


def test_the_scopes_are_not_asked_when_there_are_no_inputs_to_check() -> None:
    class Refusing(FixedScopes):
        def workspace_of(self, addr: str) -> Path | None:
            raise AssertionError("not needed")

    policy(Refusing(None, [])).check_authority("ceo", ["read"], None, [])
    policy(Refusing(None, [])).check_authority("ceo", ["read"], None, None)


def test_the_workspace_of_the_grantor_is_the_one_of_the_charter_not_the_scopes() -> None:
    charter = "---\nrole: R\nworkspace: /c/ws\n---\nbody\n"
    policy(FixedScopes(Path("/other"), []), charter).check_authority("ceo", [], "/c/ws/sub")
    with pytest.raises(OrgError, match=r"^a report's workspace must be inside yours \(/c/ws\)$"):
        policy(FixedScopes(Path("/other"), []), charter).check_authority("ceo", [], "/other/sub")


def test_the_organization_directory_is_the_one_of_the_layout() -> None:
    with pytest.raises(OrgError, match=r"^an input must not overlap the organization directory \(/memory/org\): /memory/org/x$"):
        policy(FixedScopes(None, [])).check_inputs(["/memory/org/x"])
    assert policy(FixedScopes(None, [])).check_inputs(["/memory/other"]) == ["/memory/other"]
