"""``PsOrphanJudge``: the order of its checks (what is asked of the process table, and when), over the fake table."""

from __future__ import annotations

import pytest

from orgmcp.processes import OrphanJudge, ProcessInfo, ProcessTableError
from orgmcp.processes._judge import PsOrphanJudge
from orgmcp.processes.testing import FakeProcessTable

STARTED = "Sun Oct 18 10:00:00 2026"
PID = 5000


class Spy(FakeProcessTable):
    """The fake table that remembers what the judge asked of it."""

    def __init__(self) -> None:
        super().__init__(own_pid=4000, own_pgid=3990)
        self.asked: list[tuple[str, int]] = []
        self.leader_answer: bool | None | str = "table"

    def info(self, pid: int) -> ProcessInfo | None:
        self.asked.append(("info", pid))
        return super().info(pid)

    def is_session_leader(self, pgid: int) -> bool | None:
        self.asked.append(("leader", pgid))
        return super().is_session_leader(pgid) if self.leader_answer == "table" else self.leader_answer  # type: ignore[return-value]


@pytest.fixture
def table() -> Spy:
    return Spy()


@pytest.fixture
def judge(table: Spy) -> PsOrphanJudge:
    return PsOrphanJudge(table)


def test_it_is_an_orphan_judge(judge: PsOrphanJudge) -> None:
    assert isinstance(judge, OrphanJudge)


@pytest.mark.parametrize("pgid", [0, 1, -3, 4000, 3990, None, "5000", True])
def test_the_pgid_is_checked_before_ps_is_asked_anything(judge: PsOrphanJudge, table: Spy, pgid: object) -> None:
    table.add(PID, pgid=PID, sid=PID, started=STARTED)
    assert judge.judge({"pgid": pgid, "lstart": STARTED}) == "foreign"
    assert table.asked == []


def test_ps_is_asked_once_about_the_pgid_and_a_leader_check_follows_only_for_a_verified_start_time(judge: PsOrphanJudge, table: Spy) -> None:
    table.add(PID, pgid=PID, sid=PID, started=STARTED)
    assert judge.judge({"pgid": PID, "lstart": STARTED}) == "ours"
    assert table.asked == [("info", PID), ("leader", PID)]


@pytest.mark.parametrize("lstart", [None, "", "Mon Jan 1 00:00:00 2001"], ids=repr)
def test_neither_a_missing_nor_a_wrong_start_time_asks_whether_the_process_leads_a_session(
    judge: PsOrphanJudge, table: Spy, lstart: object
) -> None:
    table.add(PID, pgid=PID, sid=PID, started=STARTED)
    assert judge.judge({"pgid": PID, "lstart": lstart}) in ("doubt", "foreign")
    assert table.asked == [("info", PID)]


def test_a_gone_process_is_not_asked_about_its_session(judge: PsOrphanJudge, table: Spy) -> None:
    assert judge.judge({"pgid": PID, "lstart": STARTED}) == "gone"
    assert table.asked == [("info", PID)]


def test_a_zombie_is_gone_even_when_its_recorded_start_time_differs(judge: PsOrphanJudge, table: Spy) -> None:
    table.add(PID, pgid=PID, sid=PID, state="Z", started=STARTED)
    assert judge.judge({"pgid": PID, "lstart": "Mon Jan 1 00:00:00 2001"}) == "gone"


def test_a_start_time_that_differs_is_foreign_whatever_the_session(judge: PsOrphanJudge, table: Spy) -> None:
    table.add(PID, pgid=PID, sid=PID, started=STARTED)
    assert judge.judge({"pgid": PID, "lstart": "Mon Jan 1 00:00:00 2001"}) == "foreign"


def test_a_leader_check_that_cannot_be_decided_is_in_doubt(judge: PsOrphanJudge, table: Spy) -> None:
    table.add(PID, pgid=PID, sid=PID, started=STARTED)
    table.leader_answer = None
    assert judge.judge({"pgid": PID, "lstart": STARTED}) == "doubt"


def test_a_process_that_does_not_lead_a_session_is_foreign(judge: PsOrphanJudge, table: Spy) -> None:
    table.add(PID, pgid=3990, sid=3990, started=STARTED)  # in the group of the judging process
    assert judge.judge({"pgid": PID, "lstart": STARTED}) == "foreign"


def test_a_process_table_that_cannot_be_read_is_in_doubt(judge: PsOrphanJudge, table: Spy) -> None:
    table.add(PID, pgid=PID, sid=PID, started=STARTED)
    table.ps_works = False
    assert judge.judge({"pgid": PID, "lstart": STARTED}) == "doubt"
    with pytest.raises(ProcessTableError):
        table.info(PID)


def test_the_judge_never_changes_the_table(judge: PsOrphanJudge, table: Spy) -> None:
    table.add(PID, pgid=PID, sid=PID, started=STARTED)
    judge.judge({"pgid": PID, "lstart": STARTED})
    assert table.is_alive(PID) and table.signals == []
