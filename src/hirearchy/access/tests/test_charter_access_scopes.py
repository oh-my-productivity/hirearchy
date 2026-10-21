"""``CharterAccessScopes`` asks only for what it needs: root and unknown agents are answered without reading a charter."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.access import AccessScopes
from hirearchy.access._scopes import CharterAccessScopes
from hirearchy.agents import CharterReader
from hirearchy.agents.testing import MemoryAgents
from hirearchy.kernel import JsonObject


class RecordingCharters(CharterReader):
    """Reads through to the in-memory agents and remembers which charters it was asked for."""

    def __init__(self, agents: MemoryAgents) -> None:
        self._agents = agents
        self.asked: list[str] = []

    def charter(self, addr: str) -> tuple[JsonObject, str]:
        self.asked.append(addr)
        return self._agents.charter(addr)

    def memory(self, addr: str) -> str:
        return self._agents.memory(addr)


@pytest.fixture
def agents() -> MemoryAgents:
    made = MemoryAgents()
    made.put("ceo/AGENT.md", "---\nrole: R\nworkspace: /w/ceo\ninputs: [/in/a]\n---\nbody\n")
    made.put("ceo/eng/AGENT.md", "---\nrole: R\nworkspace: /w/eng\n---\nbody\n")
    return made


@pytest.fixture
def charters(agents: MemoryAgents) -> RecordingCharters:
    return RecordingCharters(agents)


@pytest.fixture
def scopes(agents: MemoryAgents, charters: RecordingCharters) -> CharterAccessScopes:
    return CharterAccessScopes(agents, charters)


def test_it_is_an_access_scopes(scopes: CharterAccessScopes) -> None:
    assert isinstance(scopes, AccessScopes)


def test_root_and_unknown_agents_are_answered_without_reading_a_charter(scopes: CharterAccessScopes, charters: RecordingCharters) -> None:
    assert scopes.workspace_of("root") is None and scopes.inputs_of("root") == []
    assert scopes.workspace_of("nobody") is None and scopes.inputs_of("nobody") == []
    assert charters.asked == []


def test_one_charter_is_read_per_question_with_the_normalized_address(scopes: CharterAccessScopes, charters: RecordingCharters) -> None:
    assert scopes.workspace_of(" /ceo/ ") == Path("/w/ceo").resolve()
    assert scopes.inputs_of("ceo/") == [Path("/in/a").resolve()]
    assert charters.asked == ["ceo", "ceo"]


def test_the_roots_of_a_subtree_come_from_the_agent_directory(scopes: CharterAccessScopes, charters: RecordingCharters) -> None:
    assert scopes.readable_roots("ceo") == [Path("/in/a").resolve(), Path("/w/ceo").resolve(), Path("/w/eng").resolve()]
    assert "ceo/eng" in charters.asked


def test_an_unconfined_charter_needs_no_agent(scopes: CharterAccessScopes, charters: RecordingCharters) -> None:
    assert scopes.unconfined_read({}) is True and scopes.unconfined_read({"inputs": []}) is False
    assert charters.asked == []
