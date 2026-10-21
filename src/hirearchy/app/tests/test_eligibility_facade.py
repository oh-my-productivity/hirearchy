"""The eligibility slice of the ``Org`` facade: ``paused``, ``pause``, ``resume``, ``record_failure``, ``clear_failures`` and ``state`` behave as they
always did (green before and after), and now go through the ports of the runtime (``pause_store``, ``failure_counter`` and ``agent_states``)."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from hirearchy.app import Org
from hirearchy.eligibility import AgentStates, FailureCounter, PauseStore


def use(org: Org, **ports: Any) -> None:
    org.runtime = dataclasses.replace(org.runtime, **ports)


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.", can_hire=True, max_children=2)
    made.hire("ceo", "eng", "Engineer", "Build.")
    return made


def kinds(org: Org) -> list[str]:
    files = sorted((org.root / ".runtime" / "events").glob("*/*.jsonl"))
    return [json.loads(line)["kind"] for f in files for line in f.read_text(encoding="utf-8").splitlines()]


# ----------------------------------------------------------------------------------- as it always was (green before and after)


def test_a_pause_is_the_flag_file_and_an_event(org: Org) -> None:
    assert org.paused("ceo") is None
    org.pause("ceo", "paused by the user: lunch", by="human")
    assert (org.root / "ceo" / ".paused").read_text(encoding="utf-8") == "paused by the user: lunch"
    assert org.paused("ceo") == "paused by the user: lunch" and org.paused("ceo/eng") is None
    org.resume("ceo", "back", by="human")
    assert org.paused("ceo") is None and not (org.root / "ceo" / ".paused").exists()
    assert [k for k in kinds(org) if k.startswith("agent.p") or k.startswith("agent.r")] == ["agent.pause", "agent.resume"]


def test_resuming_an_agent_that_is_not_paused_emits_nothing(org: Org) -> None:
    org.resume("ceo")
    assert "agent.resume" not in kinds(org)


def test_failures_are_counted_in_the_ledger_and_cleared(org: Org) -> None:
    assert [org.record_failure("ceo"), org.record_failure("ceo"), org.record_failure("ceo/eng")] == [1, 2, 1]
    assert org.ledger("failures") == {"ceo": 2, "ceo/eng": 1}
    org.clear_failures("ceo")
    assert (org.root / ".runtime" / "failures.json").read_text(encoding="utf-8") == json.dumps({"ceo/eng": 1}, indent=2) + "\n"


def test_the_state_word(org: Org) -> None:
    assert org.state("ceo") == "idle"
    org.send("root", "ceo", "work", budget=3)
    assert org.state("ceo") == "pending"
    org.pause("ceo", "failures")
    assert org.state("ceo") == "paused(failures)"
    org.resume("ceo")
    org.begin_run("ceo")
    org.pause("ceo", "budget")
    assert org.state("ceo") == "running"


# -------------------------------------------------------------------------------------------- through the ports


class Pauses(PauseStore):
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def paused(self, addr: str) -> str | None:
        self.calls.append(("paused", addr))
        return "from the port"

    def pause(self, addr: str, reason: str, by: str | None = None) -> None:
        self.calls.append(("pause", addr, reason, by))

    def resume(self, addr: str, reason: str = "", by: str | None = None) -> None:
        self.calls.append(("resume", addr, reason, by))


class Failures(FailureCounter):
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def record(self, addr: str) -> int:
        self.calls.append(("record", addr))
        return 41

    def clear(self, addr: str) -> None:
        self.calls.append(("clear", addr))

    def repair(self) -> bool:
        raise AssertionError("not the facade's business")


class States(AgentStates):
    def state(self, addr: str) -> str:
        return f"state of {addr}"


def test_the_pause_comes_from_the_pause_store_of_the_runtime(org: Org) -> None:
    pauses = Pauses()
    use(org, pause_store=pauses)
    assert org.paused("ceo") == "from the port"
    org.pause("ceo", "why", by="me")
    org.pause("ceo", "why too")
    org.resume("ceo", "now", by="me")
    org.resume("ceo")
    assert pauses.calls == [
        ("paused", "ceo"), ("pause", "ceo", "why", "me"), ("pause", "ceo", "why too", None),
        ("resume", "ceo", "now", "me"), ("resume", "ceo", "", None),
    ]
    assert not (org.root / "ceo" / ".paused").exists()


def test_the_failures_come_from_the_failure_counter_of_the_runtime(org: Org) -> None:
    failures = Failures()
    use(org, failure_counter=failures)
    assert org.record_failure("ceo") == 41
    org.clear_failures("ceo")
    assert failures.calls == [("record", "ceo"), ("clear", "ceo")] and org.ledger("failures") == {}


def test_the_state_comes_from_the_agent_states_of_the_runtime(org: Org) -> None:
    use(org, agent_states=States())
    assert org.state("ceo/eng") == "state of ceo/eng"
