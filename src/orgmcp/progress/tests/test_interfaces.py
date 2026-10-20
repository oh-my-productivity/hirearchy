"""D of SOLID: every class with behaviour subclasses the port it implements (ARCHITECTURE.md R6), and the data is plain data."""

from __future__ import annotations

import dataclasses

import pytest

from orgmcp.progress import ProgressReporter
from orgmcp.progress._activity import FsTeamActivity
from orgmcp.progress._lines import CaseTaskLines
from orgmcp.progress._liveness import RunnableTeams
from orgmcp.progress._listing import MailRootTasks
from orgmcp.progress._ports import (
    ProgressText,
    ProgressView,
    RootTasks,
    RunCounts,
    Snapshot,
    Snapshots,
    TaskLines,
    TaskMark,
    TaskState,
    TaskStates,
    TaskTeams,
    TeamActivity,
    TeamLiveness,
)
from orgmcp.progress._render import RootTaskReport
from orgmcp.progress._reporter import DerivedProgressReporter
from orgmcp.progress._counts import LogRunCounts
from orgmcp.progress._snapshot import TeamSnapshots
from orgmcp.progress._states import MailTaskStates
from orgmcp.progress._teams import AgentTaskTeams
from orgmcp.progress._wait import PollingProgress


def test_each_class_subclasses_the_port_it_implements() -> None:
    assert ProgressReporter in DerivedProgressReporter.__mro__
    assert ProgressView in PollingProgress.__mro__
    assert ProgressText in RootTaskReport.__mro__
    assert Snapshots in TeamSnapshots.__mro__
    assert TaskLines in CaseTaskLines.__mro__
    assert RootTasks in MailRootTasks.__mro__
    assert TaskTeams in AgentTaskTeams.__mro__
    assert TaskStates in MailTaskStates.__mro__
    assert RunCounts in LogRunCounts.__mro__
    assert TeamActivity in FsTeamActivity.__mro__
    assert TeamLiveness in RunnableTeams.__mro__


def test_the_values_are_plain_data() -> None:
    assert TaskState("working", "running: ceo") == ("working", "running: ceo") and TaskMark("working", "T", "working").kind == "working"
    snap = Snapshot({}, {}, frozenset())
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.alive = frozenset({"t"})  # type: ignore[misc]
