"""Contract of ``HealthAnalyzer``: the metrics of an agent and the totals of a branch, over mailboxes, run logs and flag files on disk and in memory.

The ``w`` fixture (``conftest.py``) is an organization of ``ceo`` and ``ceo/eng`` over each of ``testing.IMPLEMENTATIONS[HealthAnalyzer]``. The flags and their thresholds are in ``test_flags_*.py`` and ``test_client_rework.py``; they run over the same two worlds."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import cast

import pytest

from orgmcp.health import HEALTH_DEFAULTS, FLAGS, AgentHealth, HealthAnalyzer, OrgHealth
from orgmcp.health.testing import IMPLEMENTATIONS, HealthWorld, org_md
from orgmcp.kernel import OrgError

from ._support import answer, at, give, implementations, runs


# ------------------------------------------------------------------------------------------------------------------------ the guards


def test_root_has_no_health_data(w: HealthWorld) -> None:
    with pytest.raises(OrgError, match="root is the human; only agents have health data"):
        w.analyzer.agent_health("root", at(100))


def test_an_agent_that_does_not_exist_is_refused(w: HealthWorld) -> None:
    with pytest.raises(OrgError, match="no such agent: ghost"):
        w.analyzer.agent_health("ghost", at(100))
    with pytest.raises(OrgError, match="no such agent: ghost"):
        w.analyzer.org_health("ghost", at(100))


def test_the_address_is_normalized(w: HealthWorld) -> None:
    assert w.analyzer.agent_health(" /ceo/eng/ ", at(100)).addr == "ceo/eng"
    assert w.analyzer.org_health(" /ceo/ ", at(100)).root == "ceo"


# --------------------------------------------------------------------------------------------------------------------------- the metrics


def test_an_agent_that_has_done_nothing(w: HealthWorld) -> None:
    assert w.analyzer.agent_health("ceo/eng", at(100)) == AgentHealth(
        addr="ceo/eng", depth=2, state="idle", budget_left=10, budget_received=0, runs_used=0, tasks_received=0, open_tasks=0,
        oldest_open_age=None, done=0, failed=0, blocked=0, runs_per_task=None, rework=0, empty_runs=0, last_activity=None,
        since_activity=None, flags={}, failed_runs=0, runtime_runs=0, client_rework=0,
    )


def test_tasks_are_counted_once_by_their_latest_result(w: HealthWorld) -> None:
    done, failed, later_done, open_one = (give(w, when=10 + i) for i in range(4))
    answer(w, done, "done", 20)
    answer(w, failed, "failed", 21)
    answer(w, later_done, "blocked", 22)
    answer(w, later_done, "done", 23)  # a blocked result superseded by a done one is a done
    h = w.analyzer.agent_health("ceo/eng", at(100))
    assert (h.tasks_received, h.open_tasks, h.done, h.failed, h.blocked) == (4, 1, 2, 1, 0)
    assert open_one and h.budget_received == 20


def test_a_blocked_task_is_answered_not_open(w: HealthWorld) -> None:
    answer(w, give(w), "blocked", 20)
    h = w.analyzer.agent_health("ceo/eng", at(100))
    assert (h.open_tasks, h.blocked, h.done) == (0, 1, 0)


def test_the_age_of_the_oldest_open_task(w: HealthWorld) -> None:
    give(w, when=10)
    give(w, when=100)
    assert w.analyzer.agent_health("ceo/eng", at(1000)).oldest_open_age == 990.0
    assert w.analyzer.agent_health("ceo/eng", at(5)).oldest_open_age == 0.0  # never negative


def test_the_budget_is_what_the_budget_port_says(w: HealthWorld) -> None:
    give(w, budget=5)
    w.set_budget("ceo/eng", 3)
    h = w.analyzer.agent_health("ceo/eng", at(100))
    assert (h.budget_left, h.budget_received) == (3, 5)


def test_runs_used_counts_every_log_and_runs_per_task_divides_by_the_results(w: HealthWorld) -> None:
    answer(w, give(w), "done", 20)
    answer(w, give(w, when=11), "failed", 21)
    runs(w, "ceo/eng", 3)
    h = w.analyzer.agent_health("ceo/eng", at(1000))
    assert h.runs_used == 3 and h.runs_per_task == 1.5


def test_the_last_activity_is_the_later_of_the_end_of_a_run_and_a_message_sent(w: HealthWorld) -> None:
    w.run("ceo/eng", 100, 150, "")
    h = w.analyzer.agent_health("ceo/eng", at(1000))
    assert h.last_activity == at(150) and h.since_activity == 850.0
    answer(w, give(w), "done", 400)
    h = w.analyzer.agent_health("ceo/eng", at(1000))
    assert h.last_activity == at(400) and h.since_activity == 600.0


def test_the_state_is_the_word_of_the_state_port(w: HealthWorld) -> None:
    assert w.analyzer.agent_health("ceo/eng", at(100)).state == "idle"
    w.send("root", "ceo/eng", "task", 10, budget=1)
    assert w.analyzer.agent_health("ceo/eng", at(100)).state == "pending"
    w.start_run("ceo/eng")
    assert w.analyzer.agent_health("ceo/eng", at(100)).state == "running"
    w.pause("ceo", "by hand")
    assert w.analyzer.agent_health("ceo", at(100)).state == "paused(by hand)"


def test_the_depth_is_the_number_of_parts_of_the_address(w: HealthWorld) -> None:
    assert [w.analyzer.agent_health(a, at(100)).depth for a in ("ceo", "ceo/eng")] == [1, 2]


# ----------------------------------------------------------------------------------------------------------------------------- the time


def test_now_defaults_to_the_clock_and_a_naive_now_is_utc(w: HealthWorld) -> None:
    w.run("ceo/eng", 100, 150, "")
    w.clock.t = at(5000)
    report = w.analyzer.org_health("root")
    assert 0 <= (report.now - at(5000)).total_seconds() < 1
    naive = w.analyzer.agent_health("ceo/eng", datetime(2026, 1, 1, 12, 16, 40))  # 1000 s after the origin
    assert naive.since_activity == 850.0 and naive == w.analyzer.agent_health("ceo/eng", at(1000))
    assert w.analyzer.org_health("root", datetime(2026, 1, 1, 12, 16, 40)).now == at(1000)


# ------------------------------------------------------------------------------------------------------------------------- the thresholds


def test_the_limits_given_replace_the_thresholds(w: HealthWorld) -> None:
    give(w, when=10)
    assert "stuck" not in w.analyzer.agent_health("ceo/eng", at(100)).flags
    assert "stuck" in w.analyzer.agent_health("ceo/eng", at(100), {**HEALTH_DEFAULTS, "stuck_after_seconds": 50}).flags
    assert "stuck" not in w.analyzer.agent_health("ceo/eng", at(100), {}).flags  # no limits at all: the thresholds again


def test_the_thresholds_are_read_from_org_md_at_every_call(w: HealthWorld) -> None:
    give(w, when=10)
    assert w.analyzer.agent_health("ceo/eng", at(100)).flags == {}
    w.configure(org_md(stuck_after_seconds=60))
    assert "stuck" in w.analyzer.agent_health("ceo/eng", at(100)).flags
    w.configure(org_md(stuck_after_seconds="soon"))  # a word is not a number: the default applies
    assert w.analyzer.agent_health("ceo/eng", at(100)).flags == {}


# --------------------------------------------------------------------------------------------------------------------- the whole organization


def test_the_whole_organization_lists_the_agents_parents_before_children(w: HealthWorld) -> None:
    w.agent("ops", 0)
    report = w.analyzer.org_health("root", at(100))
    assert isinstance(report, OrgHealth) and report.root == "root" and report.now == at(100)
    assert [h.addr for h in report.agents] == ["ceo", "ceo/eng", "ops"]
    assert list(report.branches) == ["root", "ceo", "ceo/eng", "ops"]


def test_a_branch_holds_its_agent_and_everything_below_it(w: HealthWorld) -> None:
    w.agent("ceo/eng/dev", 0)
    w.agent("ceo2", 0)  # a name that merely starts like another address is not in its branch
    answer(w, give(w, "ceo/eng"), "done", 20)
    answer(w, give(w, "ceo/eng/dev", when=11), "failed", 21, sender="ceo/eng/dev")
    runs(w, "ceo/eng", 2)
    runs(w, "ceo/eng/dev", 1)
    runs(w, "ceo2", 5)
    report = w.analyzer.org_health("root", at(100))
    ceo, eng, everyone = report.branches["ceo"], report.branches["ceo/eng"], report.branches["root"]
    assert (ceo.agents, ceo.runs_used, ceo.done, ceo.failed) == (3, 3, 1, 1)
    assert (eng.agents, eng.runs_used) == (2, 3)
    assert (everyone.agents, everyone.runs_used) == (4, 8)
    assert report.branches["ceo/eng/dev"].agents == 1


def test_a_branch_shows_its_worst_flag(w: HealthWorld) -> None:
    give(w, when=10)  # ceo/eng: an open task nobody works on
    w.pause("ceo", "by hand")
    report = w.analyzer.org_health("root", at(5000))
    assert report.branches["ceo"].worst_flag == "stuck" and report.branches["ceo/eng"].worst_flag == "stuck"
    assert report.branches["root"].worst_flag == "stuck" and FLAGS.index("stuck") < FLAGS.index("paused")
    quiet = w.analyzer.org_health("root", at(100))
    assert quiet.branches["ceo/eng"].worst_flag is None and quiet.branches["ceo"].worst_flag == "paused"


def test_the_report_of_a_branch_is_the_report_of_its_subtree(w: HealthWorld) -> None:
    w.agent("ops", 0)
    report = w.analyzer.org_health("ceo", at(100))
    assert report.root == "ceo" and [h.addr for h in report.agents] == ["ceo", "ceo/eng"]
    assert list(report.branches) == ["ceo", "ceo/eng"]
    leaf = w.analyzer.org_health("ceo/eng", at(100))
    assert [h.addr for h in leaf.agents] == ["ceo/eng"] and leaf.branches["ceo/eng"].agents == 1


@pytest.fixture(params=implementations(IMPLEMENTATIONS[HealthAnalyzer]))
def bare(request: pytest.FixtureRequest, tmp_path: Path) -> HealthWorld:
    return cast(Callable[[Path], HealthWorld], request.param)(tmp_path)


def test_an_organization_without_agents_has_an_empty_report(bare: HealthWorld) -> None:
    report = bare.analyzer.org_health("root", at(100))
    assert report.agents == [] and report.flagged == [] and list(report.branches) == ["root"]
    assert report.branches["root"].agents == 0 and report.branches["root"].worst_flag is None
