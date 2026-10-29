"""``FileBriefSources`` over a real organization: the facts of the brief are read from the files, and the brief built on them nominates what the user's own verdicts show."""

from __future__ import annotations

import json
from pathlib import Path

from testkit.reach.hirearchy.core import ROOT, Org

from hirearchy.kernel.testing import ListEventSink
from hirearchy.retro._brief import FileRetroBriefs
from hirearchy.retro._sources import FileBriefSources, criteria_lines, goal_line
from hirearchy.retro.testing import MemoryRetroRecords, ScriptedCharterHistory, ScriptedServiceRetirements


def sources_of(org: Org) -> FileBriefSources:
    rt = org.runtime
    return FileBriefSources(
        rt.case_records, rt.service_hints, rt.service_catalog, rt.service_store, rt.service_evidence, rt.agents, rt.charters, rt.retired_archive, rt.mailbox, rt.event_reader,
        rt.health_analyzer, rt.role_library, rt.run_log_reader, rt.settings, ScriptedCharterHistory(known=False), ScriptedServiceRetirements(), rt.clock,
    )


def world(tmp_path: Path) -> Org:
    org = Org.init(tmp_path / "org", "one-off work", {"poll_seconds": 0.05})
    (tmp_path / "ws").mkdir()
    org.hire(ROOT, "lead", "Lead", "Directs.", tools=["read", "write"], workspace=str(tmp_path / "ws"), can_hire=True, max_children=2)
    return org


def judged_one_off(org: Org, day: int) -> str:
    task = org.delegate(ROOT, "lead", f"Action list for 2026-11-{day:02d}", "Turn the notes into a list.", "Every action has an owner", budget=3)
    org.report("lead", task.id, "done", "Done.")
    org.feedback(ROOT, task.id, "accept", source="human")
    return str(task.id)


def test_the_body_of_a_task_gives_its_goal_and_its_criteria() -> None:
    body = "## Goal\n\nTurn the notes into a list.\nMore.\n\n## Acceptance criteria\n- One\n\n- Two\n## Deliverable\nx\n"
    assert goal_line(body) == "Turn the notes into a list." and criteria_lines(body) == ("- One", "- Two") and goal_line("none") == "" and criteria_lines("none") == ()


def test_an_organization_with_nothing_has_no_verdict_and_an_empty_fact_sheet(tmp_path: Path) -> None:
    sources = sources_of(world(tmp_path))
    facts = sources.read(None, None)
    assert sources.new_verdicts(None) == 0 and (facts.said, facts.passed, facts.one_offs, facts.failures) == ((), (), (), ()) and facts.verdicts == 0
    assert sources.started() is not None and facts.estimates == {"lead": 3} and facts.unreadable == ()  # the lead alone is a worker with a custom charter: 2 runs and 1 rework


def test_three_one_off_tasks_the_user_judged_nominate_a_service_and_the_ledger_records_it(tmp_path: Path) -> None:
    org = world(tmp_path)
    ids = [judged_one_off(org, day) for day in (2, 9, 16)]
    sources = sources_of(org)
    assert sources.new_verdicts(None) == 3 and sources.new_verdicts(org.runtime.clock.now()) == 0
    facts = sources.read(None, None)
    assert [c.id for c in facts.one_offs] == ids and all(c.judged and c.assignee == "lead" for c in facts.one_offs) and (facts.verdicts, facts.cases, facts.accepts) == (3, 3, 3)
    records, sink = MemoryRetroRecords(), ListEventSink()
    briefs = FileRetroBriefs(sources, records, org.runtime.settings, sink, org.runtime.clock)
    brief = briefs.brief()
    (item,) = brief.items
    assert (brief.id, brief.recorded, item.kind, item.key, item.weight) == ("B1", True, "service", f"service|lead|{ids[0]}", 3)
    assert json.loads(item.blueprint)["reason"] == "B1.1: 3 one-off tasks of one shape" and item.evidence == tuple(ids)
    assert [r.id for r in records.records()] == ["B1"] and sink.events == []
    again = briefs.brief()  # no verdict since: shown again, nothing recorded
    assert (again.id, again.recorded, again.items[0].state) == ("B1", False, "open") and len(records.records()) == 1
    assert item.blueprint is not None and "{n}" not in item.blueprint


def test_retro_writes_only_its_ledger_and_sends_nothing(tmp_path: Path) -> None:
    org = world(tmp_path)
    [judged_one_off(org, day) for day in (2, 9, 16)]
    before = sorted(p.relative_to(org.root).as_posix() for p in org.root.rglob("*") if p.is_file() and ".git/" not in p.as_posix() and ".runtime/events" not in p.as_posix())
    FileRetroBriefs(sources_of(org), MemoryRetroRecords(), org.runtime.settings, ListEventSink(), org.runtime.clock).brief()
    after = sorted(p.relative_to(org.root).as_posix() for p in org.root.rglob("*") if p.is_file() and ".git/" not in p.as_posix() and ".runtime/events" not in p.as_posix())
    assert after == before  # no message in any box, no file anywhere
