"""Contract of ``OrphanJudge``: the verdict table, against real processes and against the fake process table.

Only processes the world started are inspected; the judge never signals anything.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from orgmcp.processes import OrphanJudge
from orgmcp.processes.testing import IMPLEMENTATIONS, ProcessWorld

from ._support import make_world

pytestmark = pytest.mark.xfail(strict=True, reason="red: A-processes")


@pytest.fixture(params=IMPLEMENTATIONS[OrphanJudge], ids=lambda factory: factory.__name__)
def world(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[ProcessWorld]:
    yield from make_world(request, tmp_path)


def record(world: ProcessWorld, pid: int, **override: object) -> dict[str, object]:
    """What the scheduler recorded for a run: the process group and the start time of its leader."""
    return {"pgid": pid, "lstart": world.inspector.start_time(pid), **override}


# --------------------------------------------------------------------------------------------------------------------- ours


def test_a_live_session_leader_started_at_the_recorded_time_is_ours(world: ProcessWorld) -> None:
    leader = world.start_leader()
    assert isinstance(world.judge, OrphanJudge)
    assert world.judge.judge(record(world, leader.pid)) == "ours"


def test_a_leader_with_a_grandchild_is_ours(world: ProcessWorld) -> None:
    leader, _ = world.start_group()
    assert world.judge.judge(record(world, leader.pid)) == "ours"


def test_extra_keys_of_the_record_do_not_matter(world: ProcessWorld) -> None:
    leader = world.start_leader()
    rec = record(world, leader.pid, started=1.0, scheduler=999999, log="alice/runs/x.log")
    assert world.judge.judge(rec) == "ours"


# --------------------------------------------------------------------------------------------------------------------- gone


def test_a_process_that_does_not_exist_is_gone(world: ProcessWorld) -> None:
    assert world.judge.judge({"pgid": world.gone_pid(), "lstart": "Mon Jan 1 00:00:00 2001"}) == "gone"


def test_a_zombie_is_gone(world: ProcessWorld) -> None:
    zombie = world.start_zombie()
    assert world.judge.judge(record(world, zombie)) == "gone"


def test_gone_wins_over_a_missing_start_time(world: ProcessWorld) -> None:
    assert world.judge.judge({"pgid": world.gone_pid()}) == "gone"
    assert world.judge.judge({"pgid": world.gone_pid(), "lstart": None}) == "gone"


# ------------------------------------------------------------------------------------------------------------------ foreign


def test_a_pid_that_now_belongs_to_a_process_started_at_another_time_is_foreign(world: ProcessWorld) -> None:
    stranger = world.start_leader()  # a session leader, but not started when the recorded run was
    assert world.judge.judge(record(world, stranger.pid, lstart="Mon Jan 1 00:00:00 2001")) == "foreign"


def test_a_recorded_pid_that_is_not_a_session_leader_is_foreign(world: ProcessWorld) -> None:
    bystander = world.start_bystander()  # in the process group of the test run itself
    assert world.judge.judge(record(world, bystander)) == "foreign"


@pytest.mark.parametrize("pgid", [0, 1, -5, None, "x", True, False, 2.5, [1]], ids=repr)
def test_a_pgid_that_cannot_be_a_run_is_foreign(world: ProcessWorld, pgid: object) -> None:
    assert world.judge.judge({"pgid": pgid, "lstart": "x"}) == "foreign"


def test_a_record_without_a_pgid_is_foreign(world: ProcessWorld) -> None:
    assert world.judge.judge({}) == "foreign"
    assert world.judge.judge({"lstart": "x"}) == "foreign"


def test_the_pid_and_the_process_group_of_the_judging_process_are_foreign(world: ProcessWorld) -> None:
    pid, pgid = world.inspector.own_ids()
    assert world.judge.judge({"pgid": pid, "lstart": world.inspector.start_time(pid)}) == "foreign"
    assert world.judge.judge({"pgid": pgid, "lstart": world.inspector.start_time(pgid)}) == "foreign"


# -------------------------------------------------------------------------------------------------------------------- doubt


@pytest.mark.parametrize("lstart", [None, "", 5, ["x"]], ids=repr)
def test_a_live_process_without_a_usable_recorded_start_time_is_in_doubt(world: ProcessWorld, lstart: object) -> None:
    leader = world.start_leader()
    assert world.judge.judge({"pgid": leader.pid, "lstart": lstart}) == "doubt"


def test_a_live_process_and_a_record_with_no_start_time_at_all_is_in_doubt(world: ProcessWorld) -> None:
    leader = world.start_leader()
    assert world.judge.judge({"pgid": leader.pid}) == "doubt"


def test_when_ps_cannot_run_a_sane_pgid_is_in_doubt(world: ProcessWorld) -> None:
    leader = world.start_leader()
    assert world.blind_judge.judge(record(world, leader.pid)) == "doubt"
    assert world.blind_judge.judge({"pgid": world.gone_pid(), "lstart": "x"}) == "doubt"


def test_when_ps_cannot_run_a_pgid_that_cannot_be_a_run_is_still_foreign(world: ProcessWorld) -> None:
    pid, pgid = world.inspector.own_ids()
    for nonsense in (0, 1, -5, None, "x", True, pid, pgid):
        assert world.blind_judge.judge({"pgid": nonsense, "lstart": "x"}) == "foreign", nonsense
