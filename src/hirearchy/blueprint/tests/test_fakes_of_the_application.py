"""The recording and flaky ports that the application suites use: they obey the contracts of the ports they stand for."""

from __future__ import annotations

import pytest

from hirearchy.agents.testing import MemoryAgents
from hirearchy.blueprint.testing import (
    CallLog,
    FlakyHiring,
    FlakyServiceCommands,
    FlakyTaskAssigner,
    RecordingHiring,
    RecordingRetirement,
    RecordingServiceCommands,
    RecordingSnapshots,
    RecordingTaskAssigner,
)
from hirearchy.dispatch import TaskAssigner
from hirearchy.hierarchy import Hiring, Retirement
from hirearchy.kernel import OrgError
from hirearchy.services import ServiceCommands
from hirearchy.snapshots import OrgSnapshotter


def test_the_recording_ports_are_the_ports() -> None:
    log, agents = CallLog(), MemoryAgents()
    assert isinstance(RecordingHiring(agents, log), Hiring) and isinstance(RecordingRetirement(agents, log), Retirement)
    assert isinstance(RecordingTaskAssigner(log), TaskAssigner) and isinstance(RecordingServiceCommands(log), ServiceCommands)
    assert isinstance(RecordingSnapshots(log), OrgSnapshotter)
    assert isinstance(FlakyHiring(RecordingHiring(agents, log), 1), Hiring) and isinstance(FlakyTaskAssigner(RecordingTaskAssigner(log)), TaskAssigner)
    assert isinstance(FlakyServiceCommands(RecordingServiceCommands(log)), ServiceCommands)


def test_a_hire_makes_the_agent_and_a_name_that_is_taken_is_refused() -> None:
    log, agents = CallLog(), MemoryAgents()
    hiring = RecordingHiring(agents, log)
    assert hiring.hire("root", "lead", "Lead", "charter") == "lead" and hiring.hire("lead", "w", "W", "c") == "lead/w"
    assert agents.exists("lead/w") and agents.charter("lead")[1].strip() == "charter"
    with pytest.raises(OrgError, match="lead already exists"):
        hiring.hire("root", "lead", "Lead", "charter")
    assert log.names() == ["hire", "hire", "hire"]


def test_a_retirement_archives_the_tree_and_a_missing_agent_is_refused() -> None:
    log, agents = CallLog(), MemoryAgents()
    RecordingHiring(agents, log).hire("root", "lead", "Lead", "c")
    retirement = RecordingRetirement(agents, log)
    assert retirement.retire("root", "lead", "why") == "lead" and not agents.exists("lead")
    with pytest.raises(OrgError, match="no such agent: lead"):
        retirement.retire("root", "lead", "why")


def test_the_flaky_hiring_fails_the_chosen_hire_only_and_does_the_others() -> None:
    log, agents = CallLog(), MemoryAgents()
    hiring = FlakyHiring(RecordingHiring(agents, log), fail_on=2, error="boom")
    hiring.hire("root", "a", "A", "c")
    with pytest.raises(OrgError, match="boom"):
        hiring.hire("root", "b", "B", "c")
    hiring.hire("root", "c", "C", "c")
    assert agents.exists("a") and not agents.exists("b") and agents.exists("c")


def test_the_flaky_task_assigner_fails_the_first_delegation_by_default() -> None:
    log = CallLog()
    tasks = FlakyTaskAssigner(RecordingTaskAssigner(log))
    with pytest.raises(OrgError, match="delegate failed"):
        tasks.delegate("root", "lead", "t", "g", "a")
    assert tasks.delegate("root", "lead", "t", "g", "a").to == "lead"


def test_the_flaky_service_commands_fail_a_definition_or_a_request_and_do_the_rest() -> None:
    log = CallLog()
    commands = FlakyServiceCommands(RecordingServiceCommands(log), fail_define_on=1, fail_request_on=2)
    with pytest.raises(OrgError, match="disk full"):
        commands.define_service("root", "lead", "s")
    assert commands.define_service("root", "lead", "s") == "defined s"
    assert commands.request("root", "s", {}).service == "s"
    with pytest.raises(OrgError, match="disk full"):
        commands.request("root", "s", {})
    with pytest.raises(OrgError):
        commands.revise_playbook("root", "s", "c", "r")  # the others are the inner ones: the recording ones refuse what an application never does
