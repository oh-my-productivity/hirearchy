"""``branch_totals``: the totals of every branch of the organization, a pure function of the health of its agents."""

from __future__ import annotations

from datetime import datetime, timezone

from orgmcp.health import FLAGS, AgentHealth
from orgmcp.health._branches import branch_totals

from ._support import RED

pytestmark = RED

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def agent(addr: str, runs: int = 0, open_tasks: int = 0, done: int = 0, failed: int = 0, blocked: int = 0, rework: int = 0,
          **flags: str) -> AgentHealth:
    return AgentHealth(
        addr=addr, depth=addr.count("/") + 1, state="idle", budget_left=0, budget_received=0, runs_used=runs, tasks_received=0,
        open_tasks=open_tasks, oldest_open_age=None, done=done, failed=failed, blocked=blocked, runs_per_task=None, rework=rework,
        empty_runs=0, last_activity=None, since_activity=None, flags=dict(flags),
    )


ALL = [
    agent("ceo", 3, 1, 2, 0, 0, 1),
    agent("ceo/eng", 5, 0, 1, 1, 0, 0, idle="quiet", stuck="old"),
    agent("ceo/eng/dev", 2, 2, 0, 0, 3, 0, paused="by hand"),
    agent("ceo2", 7, 0, 4, 0, 0, 0),
]


def totals(top: str = "root") -> dict[str, tuple[int, ...] | str | None]:
    addrs = [h.addr for h in ALL]
    by_addr = {h.addr: h for h in ALL}
    got = branch_totals(top, addrs, by_addr)
    return {b: (v.agents, v.runs_used, v.open_tasks, v.done, v.failed, v.blocked, v.rework) for b, v in got.items()} | {
        f"{b}:worst": v.worst_flag for b, v in got.items()
    }


def test_there_is_a_branch_for_the_top_and_for_each_agent_in_order() -> None:
    assert list(branch_totals("root", [h.addr for h in ALL], {h.addr: h for h in ALL})) == ["root", "ceo", "ceo/eng", "ceo/eng/dev", "ceo2"]


def test_the_top_is_not_repeated_when_it_is_one_of_the_agents() -> None:
    members = ALL[:3]
    got = branch_totals("ceo", [h.addr for h in members], {h.addr: h for h in members})
    assert list(got) == ["ceo", "ceo/eng", "ceo/eng/dev"]


def test_root_holds_every_agent() -> None:
    assert totals()["root"] == (4, 17, 3, 7, 1, 3, 1)


def test_a_branch_holds_its_agent_and_the_agents_below_it() -> None:
    got = totals()
    assert got["ceo"] == (3, 10, 3, 3, 1, 3, 1) and got["ceo/eng"] == (2, 7, 2, 1, 1, 3, 0) and got["ceo/eng/dev"] == (1, 2, 2, 0, 0, 3, 0)


def test_an_address_that_only_starts_like_another_is_not_below_it() -> None:
    assert totals()["ceo2"] == (1, 7, 0, 4, 0, 0, 0)


def test_the_worst_flag_of_a_branch_is_the_first_of_the_ranking_among_its_members() -> None:
    got = totals()
    assert got["root:worst"] == "stuck" and got["ceo:worst"] == "stuck" and got["ceo/eng:worst"] == "stuck"
    assert got["ceo/eng/dev:worst"] == "paused" and got["ceo2:worst"] is None
    assert FLAGS.index("stuck") < FLAGS.index("paused") < FLAGS.index("idle")
