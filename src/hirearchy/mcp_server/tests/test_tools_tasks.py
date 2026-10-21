"""``TaskTools``: delegate (what was delegated and the budget left) and report (what was returned, and the hint on a service request)."""

from __future__ import annotations

from pathlib import Path

from hirearchy.kernel import OrgError
from hirearchy.mail.testing import memory_mailbox
from hirearchy.mcp_server._tools_tasks import TaskTools
from hirearchy.mcp_server.testing import HeldBudgets, ScriptedHints, ScriptedTasks

import asyncio

from ._support import call, described, fails, serve


def tools(tmp_path: Path, tasks: ScriptedTasks | None = None, hints: ScriptedHints | None = None) -> tuple[TaskTools, ScriptedTasks, ScriptedHints]:
    tasks, hints = tasks or ScriptedTasks(), hints or ScriptedHints()
    box = memory_mailbox(tmp_path)
    return TaskTools(lambda: tasks, lambda: tasks, lambda: HeldBudgets({"ceo": 4}), lambda: box.reader, lambda: hints), tasks, hints


def test_delegate_hands_the_task_over_and_says_the_budget_left(tmp_path: Path) -> None:
    group, tasks, _ = tools(tmp_path)
    out = call(serve(group, "ceo"), "delegate", to="ceo/eng", title="T", goal="G", acceptance="A", budget=2)
    assert out == "delegated task-1 to ceo/eng with budget 2. Your budget is now 4."
    assert tasks.log.of("delegate") == [(("ceo", "ceo/eng", "T", "G", "A", [], 2, None), {})]


def test_delegate_passes_inputs_and_the_task_it_revises(tmp_path: Path) -> None:
    group, tasks, _ = tools(tmp_path)
    call(serve(group, "ceo"), "delegate", to="ceo/eng", title="T", goal="G", acceptance="A", inputs=["/in"], revises="old")
    assert tasks.log.of("delegate")[0][0][6:] == (None, "old") and tasks.log.of("delegate")[0][0][5] == ["/in"]


def test_root_delegate_says_a_rework_after_the_users_rejection_is_human(tmp_path: Path) -> None:
    text = " ".join(described(serve(tools(tmp_path)[0], "root"))["delegate"].split())
    assert "a rework after their own rejection, carrying their corrections, is one" in text and 'source (with revises): "human" when the user asked for this rework' in text


def test_agents_delegate_has_no_source_parameter(tmp_path: Path) -> None:
    server = serve(tools(tmp_path)[0], "ceo")
    props = {t.name: set(t.inputSchema["properties"]) for t in asyncio.run(server.list_tools())}["delegate"]
    assert "source" not in props and "source" not in described(server)["delegate"]
    root_props = {t.name: set(t.inputSchema["properties"]) for t in asyncio.run(serve(tools(tmp_path)[0], "root").list_tools())}["delegate"]
    assert "source" in root_props


def test_root_delegate_passes_the_source_it_is_given(tmp_path: Path) -> None:
    group, tasks, _ = tools(tmp_path)
    call(serve(group, "root"), "delegate", to="ceo", title="T", goal="G", acceptance="A", revises="old", source="human")
    assert tasks.log.of("delegate") == [(("root", "ceo", "T", "G", "A", [], None, "old"), {"source": "human"})]


def test_a_refusal_of_the_port_is_the_refusal_of_the_tool(tmp_path: Path) -> None:
    group, _, _ = tools(tmp_path, ScriptedTasks(fails=OrgError("you can only delegate to your direct reports")))
    assert "you can only delegate to your direct reports" in fails(serve(group, "ceo"), "delegate", to="x", title="T", goal="G", acceptance="A")


def test_report_says_what_it_sent_where(tmp_path: Path) -> None:
    group, tasks, _ = tools(tmp_path)
    assert call(serve(group, "ceo/eng"), "report", task_id="t1", status="done", summary="S") == "reported done on t1 to boss"
    assert tasks.log.of("report") == [(("ceo/eng", "t1", "done", "S", [], None), {})]


def test_report_says_what_travelled_up_with_the_result(tmp_path: Path) -> None:
    group, _, _ = tools(tmp_path, ScriptedTasks(returned=3))
    out = call(serve(group, "ceo/eng"), "report", task_id="t1", status="done", summary="S")
    assert out == "reported done on t1 to boss; returned 3 unspent run(s) of budget to boss"


def test_report_adds_the_hint_for_a_service_request_it_answers(tmp_path: Path) -> None:
    hints = ScriptedHints("Rate it with feedback.")
    group, _, _ = tools(tmp_path, hints=hints)
    box = memory_mailbox(tmp_path)
    box.put("ceo/inbox/t1.md", "---\nsender: root\nto: ceo\ntype: task\nid: t1\ncreated: 2026-01-01T00:00:00+00:00\n---\nbody\n")
    group = TaskTools(lambda: ScriptedTasks(), lambda: ScriptedTasks(), lambda: HeldBudgets(), lambda: box.reader, lambda: hints)
    out = call(serve(group, "ceo"), "report", task_id="t1", status="done", summary="S", lessons="L")
    assert out == "reported done on t1 to boss. Rate it with feedback."
    assert hints.log.of("report_hint") == [(("ceo", "t1", "done"), {})]


def test_report_asks_no_hint_for_a_task_it_was_not_given(tmp_path: Path) -> None:
    group, _, hints = tools(tmp_path, hints=ScriptedHints("never"))
    assert "never" not in call(serve(group, "ceo"), "report", task_id="nope", status="done", summary="S")
    assert hints.log.calls == []
