"""``RunnableTeams``: could an agent of a team run now."""

from __future__ import annotations

from hirearchy.kernel import ROOT, Message
from hirearchy.progress._liveness import RunnableTeams
from hirearchy.progress._ports import TeamLiveness
from hirearchy.progress.testing import ProgressWorld


def liveness(w: ProgressWorld) -> RunnableTeams:
    return RunnableTeams(w.mail, w.runnable)


def test_it_is_a_liveness(w: ProgressWorld) -> None:
    assert isinstance(liveness(w), TeamLiveness)


def test_an_agent_with_unread_work_and_budget_can_run(w: ProgressWorld, task: Message) -> None:
    assert liveness(w).can_run("ceo") and not liveness(w).can_run("ceo/eng")


def test_an_agent_that_is_running_can_run_whatever_the_rest_says(w: ProgressWorld, task: Message) -> None:
    w.begin_run("ceo")
    w.pause("ceo", "tired")
    assert liveness(w).can_run("ceo")


def test_a_paused_agent_with_unread_work_cannot(w: ProgressWorld, task: Message) -> None:
    w.pause("ceo", "tired")
    assert not liveness(w).can_run("ceo")


def test_a_team_is_alive_while_any_of_its_agents_can_run(w: ProgressWorld, task: Message) -> None:
    assert liveness(w).alive(["ceo/eng", "ceo"]) and not liveness(w).alive(["ceo/eng"]) and not liveness(w).alive([])
    assert ROOT not in {"ceo", "ceo/eng"}
