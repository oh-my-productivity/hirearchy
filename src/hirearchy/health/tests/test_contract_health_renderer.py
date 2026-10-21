"""Contract of ``HealthRenderer``: the human report. The text is what ``health``, the ``status health`` tool and the review notes show, so it is
pinned character for character. ``TextHealthRenderer`` is a pure function of the report: one implementation, no fake (``testing.PURE``)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from hirearchy.health import AgentHealth, BranchHealth, HealthRenderer, OrgHealth
from hirearchy.health._render import TextHealthRenderer

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def renderer() -> HealthRenderer:
    made = TextHealthRenderer()
    assert isinstance(made, HealthRenderer)
    return made


def agent(addr: str, **fields: object) -> AgentHealth:
    base: dict[str, object] = dict(
        addr=addr, depth=addr.count("/") + 1, state="idle", budget_left=3, budget_received=5, runs_used=2, tasks_received=1, open_tasks=0,
        oldest_open_age=None, done=1, failed=0, blocked=0, runs_per_task=2.0, rework=0, empty_runs=0, last_activity=NOW, since_activity=90.0,
    )
    return AgentHealth(**{**base, **fields})  # type: ignore[arg-type]


def branch(addr: str, agents: int = 1, **fields: object) -> BranchHealth:
    base: dict[str, object] = dict(addr=addr, agents=agents, runs_used=0, open_tasks=0, done=0, failed=0, blocked=0, rework=0, worst_flag=None)
    return BranchHealth(**{**base, **fields})  # type: ignore[arg-type]


def report(agents: list[AgentHealth], branches: list[BranchHealth]) -> OrgHealth:
    return OrgHealth("root", NOW, agents, {b.addr: b for b in branches})


def test_nothing_to_report(renderer: HealthRenderer) -> None:
    assert renderer.render_text(report([], [])) == "0 agents, 0 flagged"


def test_one_agent_is_not_plural(renderer: HealthRenderer) -> None:
    text = renderer.render_text(report([agent("ceo")], [branch("ceo")]))
    assert text.splitlines()[0] == "1 agent, 0 flagged"


def test_an_agent_line(renderer: HealthRenderer) -> None:
    text = renderer.render_text(report([agent("ceo")], [branch("ceo")]))
    assert text == (
        "1 agent, 0 flagged\n"
        "ceo idle, budget 3/5, runs 2, open 0, done 1 failed 0 blocked 0 rework 0, runs/task 2.0, empty 0, last activity 1m ago"
    )


def test_every_optional_part(renderer: HealthRenderer) -> None:
    ceo = agent(
        "ceo", state="paused(budget)", budget_left=None, open_tasks=2, oldest_open_age=7300.0, client_rework=2, runs_per_task=None, empty_runs=3,
        failed_runs=1, since_activity=None, last_activity=None, flags={"stuck": "open task is 2h old", "paused": "paused: budget"},
    )
    text = renderer.render_text(report([ceo], [branch("ceo")]))
    assert text.splitlines()[1] == (
        "ceo paused(budget), budget unlimited/5, runs 2, open 2 (oldest 2h), done 1 failed 0 blocked 0 rework 0 (+2 by the client), "
        "runs/task -, empty 3 (+1 failed), last activity never | !stuck: open task is 2h old; !paused: paused: budget"
    )


def test_the_branch_totals_follow_an_agent_that_has_others_below_it(renderer: HealthRenderer) -> None:
    agents = [agent("ceo"), agent("ceo/eng", flags={"idle": "quiet"}), agent("ceo/qa")]
    branches = [
        branch("ceo", 3, runs_used=6, open_tasks=1, done=3, failed=1, blocked=2, rework=1, worst_flag="idle"),
        branch("ceo/eng"), branch("ceo/qa"),
    ]
    lines = renderer.render_text(report(agents, branches)).splitlines()
    assert lines[0] == "3 agents, 1 flagged"
    assert lines[1].endswith(" | branch: runs 6, open 1, done 3, failed 1, blocked 2, rework 1, worst idle")
    assert " | branch:" not in lines[2] and " | branch:" not in lines[3]


def test_a_branch_without_flags_says_none(renderer: HealthRenderer) -> None:
    text = renderer.render_text(report([agent("ceo"), agent("ceo/eng")], [branch("ceo", 2), branch("ceo/eng")]))
    assert text.splitlines()[1].endswith(" | branch: runs 0, open 0, done 0, failed 0, blocked 0, rework 0, worst none")


def test_children_are_indented_by_two_spaces_per_level_below_the_shallowest_agent(renderer: HealthRenderer) -> None:
    agents = [agent("ceo"), agent("ceo/eng"), agent("ceo/eng/dev")]
    lines = renderer.render_text(report(agents, [branch("ceo", 3), branch("ceo/eng", 2), branch("ceo/eng/dev")])).splitlines()
    assert [len(line) - len(line.lstrip()) for line in lines[1:]] == [0, 2, 4]
    assert lines[3].lstrip().startswith("dev idle")  # the last part of the address only


def test_the_indent_is_relative_to_the_shallowest_agent_of_the_report(renderer: HealthRenderer) -> None:
    agents = [agent("ceo/eng"), agent("ceo/eng/dev")]
    lines = renderer.render_text(report(agents, [branch("ceo/eng", 2), branch("ceo/eng/dev")])).splitlines()
    assert [len(line) - len(line.lstrip()) for line in lines[1:]] == [0, 2]


def test_the_segment_shows_only_when_judged(renderer: HealthRenderer) -> None:
    quiet = renderer.render_text(report([agent("ceo")], [branch("ceo")]))
    assert "escapes" not in quiet and "re-checks" not in quiet
    still = renderer.render_text(report([agent("ceo", rechecks=2, rework_runs=3)], [branch("ceo")]))
    assert still == quiet  # nothing is judged: the segment stays out, whatever the other numbers say
    judged = renderer.render_text(report([agent("ceo", escapes=1, judged=4, rechecks=2, rework_runs=3)], [branch("ceo")]))
    assert judged == (
        "1 agent, 0 flagged\n"
        "ceo idle, budget 3/5, runs 2, open 0, done 1 failed 0 blocked 0 rework 0, escapes 1 of 4 judged, re-checks after a FAIL 2 "
        "(author rework runs 3), runs/task 2.0, empty 0, last activity 1m ago"
    )


def test_the_segment_follows_the_rework_part_with_the_client_count(renderer: HealthRenderer) -> None:
    text = renderer.render_text(report([agent("ceo", client_rework=2, escapes=0, judged=1)], [branch("ceo")]))
    assert "rework 0 (+2 by the client), escapes 0 of 1 judged, re-checks after a FAIL 0 (author rework runs 0), runs/task" in text
