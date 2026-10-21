"""Contract of ``SummaryText``: what ``apply`` tells of what it did. ``Summary`` is data with this one view, so it has one implementation and no fake."""

from __future__ import annotations

from hirearchy.blueprint import Issue, Summary, SummaryText


def test_a_summary_is_a_summary_text() -> None:
    assert isinstance(Summary(["lead"], "t", "lead", 3), SummaryText)


def test_a_plain_task() -> None:
    s = Summary(["lead", "lead/writer"], "task-1", "lead", 12)
    assert s.text() == "created 2 agents: lead, lead/writer\ntask task-1 -> lead (budget 12)"


def test_services_and_a_first_request() -> None:
    s = Summary(["lead"], "task-2", "lead", 22, services=["weekly-brief", "daily"], service_request="weekly-brief")
    assert s.text() == (
        "created 1 agents: lead\n"
        "defined 2 service(s) of lead: weekly-brief, daily (contract and playbook v1)\n"
        "first request: service weekly-brief, task task-2 -> lead (budget 22)"
    )


def test_services_and_no_task() -> None:
    s = Summary(["lead"], "", "lead", 0, services=["weekly-brief"])
    assert s.text() == (
        "created 1 agents: lead\n"
        "defined 1 service(s) of lead: weekly-brief (contract and playbook v1)\n"
        "no task was given: the services are ready and nothing runs yet. To use one: request(service, inputs) "
        "(or `hirearchy request SERVICE --input key=value`), then start()"
    )


def test_warnings_come_last_one_line_each() -> None:
    s = Summary(["lead"], "t", "lead", 3, warnings=[Issue("warning", "needs.scope", "say more", "needs-scope"), Issue("warning", "x", "y")])
    assert s.text().splitlines() == ["created 1 agents: lead", "task t -> lead (budget 3)", "warning: needs.scope: say more", "warning: x: y"]


def test_the_defaults_are_empty_and_not_shared() -> None:
    a, b = Summary([], "", "x", 0), Summary([], "", "x", 0)
    a.warnings.append(Issue("warning", "p", "m"))
    assert b.warnings == [] and b.services == [] and b.service_request == ""
