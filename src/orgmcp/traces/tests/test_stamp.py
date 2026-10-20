# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import json
import shutil

import pytest
from testkit.legacy.orgmcp.app import wiring
from testkit.legacy.orgmcp.core import ROOT, split_frontmatter


# ---------------------------------------------------------------------------------------------------- helpers
@pytest.fixture
def org(org):
    """The shared org, with the events of its construction (hires) forgotten: tests see only their own."""
    shutil.rmtree(org.root / ".runtime" / "events", ignore_errors=True)
    wiring.process_resources().reset()
    return org


def event_files(org):
    return sorted((org.root / ".runtime" / "events").glob("*/*.jsonl"))


def read_events(org, kind=None):
    """Every event of the org, merged by time (the way a reader would)."""
    out = []
    for f in event_files(org):
        for line in f.read_text(encoding="utf-8").splitlines():
            out.append(json.loads(line))  # every line is a valid JSON object
    out.sort(key=lambda e: (e["ts"], e["seq"]))
    return [e for e in out if kind is None or e["kind"] == kind]


# ---------------------------------------------------------------------------------------------- trace stamping
def frontmatter(org, addr, box, msg):
    return split_frontmatter((org.dir(addr) / box / f"{msg.id}.md").read_text())[0]


def deliveries(org):
    return {e["id"]: e for e in read_events(org, "msg.deliver")}


def test_rule_new_a_root_task_is_its_own_trace(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    assert task.trace == task.id
    assert frontmatter(org, "ceo", "inbox", task)["trace"] == task.id
    assert frontmatter(org, ROOT, "sent", task)["trace"] == task.id
    ev = deliveries(org)[task.id]
    assert ev["trace"] == task.id and ev["trace_rule"] == "new" and ev["type"] == "task" and ev["from"] == "root"
    assert ev["to"] == "ceo" and ev["budget"] == 5 and ev["chars"] > 0 and ev["wake"] is True and "body" not in ev


def test_rule_link_a_result_follows_its_task(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")
    result = org.report("ceo", task.id, "done", "ok")
    assert result.trace == task.id
    ev = deliveries(org)[result.id]
    assert ev["trace"] == task.id and ev["trace_rule"] == "link" and ev["reply_to"] == task.id and ev["status"] == "done"


def test_rule_link_via_reply_to_on_a_plain_note(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    note = org.send("ceo", ROOT, "a question", reply_to=task.id)
    assert note.trace == task.id and deliveries(org)[note.id]["trace_rule"] == "link"


def test_rule_link_via_revises_keeps_the_trace_of_the_revised_task(org):
    first = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")
    org.report("ceo", first.id, "done", "ok")
    redo = org.delegate(ROOT, "ceo", "T again", "g", "a", budget=9, revises=first.id)
    assert redo.trace == first.id and redo.id != first.id
    assert deliveries(org)[redo.id]["trace_rule"] == "link" and deliveries(org)[redo.id]["revises"] == first.id
    # and a manager's own rework of its delegation stays in the same trace
    org.begin_run("ceo")
    sub = org.delegate("ceo", "ceo/eng", "Sub", "g", "a", budget=2)
    redo_sub = org.delegate("ceo", "ceo/eng", "Sub again", "g", "a", budget=2, revises=sub.id)
    assert sub.trace == first.id and redo_sub.trace == first.id


def test_rule_open_task_a_manager_stamps_what_it_sends_with_its_open_tasks_trace(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=8)
    sub = org.delegate("ceo", "ceo/eng", "Sub", "g", "a", budget=3)  # no batch needed: the open task decides
    assert sub.trace == task.id and deliveries(org)[sub.id]["trace_rule"] == "open-task"
    note = org.send("ceo", "ceo/eng", "psst")
    grant = org.send("ceo", "ceo/eng", "more runs", budget=1)
    assert note.trace == grant.trace == task.id


def test_rule_batch_picks_the_one_trace_of_the_current_batch(org):
    a = org.delegate(ROOT, "ceo", "A", "g", "a", budget=8)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    b = org.delegate(ROOT, "ceo", "B", "g", "a", budget=8)
    org.begin_run("ceo")  # inflight: only B; open tasks: A and B (two traces)
    note = org.send("ceo", "ceo/eng", "about B")
    assert note.trace == b.id != a.id
    assert deliveries(org)[note.id]["trace_rule"] == "batch"


def test_rule_ambiguous_leaves_the_trace_empty_and_lists_candidates(org):
    a = org.delegate(ROOT, "ceo", "A", "g", "a", budget=8)
    b = org.delegate(ROOT, "ceo", "B", "g", "a", budget=8)
    org.begin_run("ceo")  # inflight holds both
    note = org.send("ceo", "ceo/eng", "about both")
    assert note.trace is None and "trace" not in frontmatter(org, "ceo", "sent", note)
    ev = deliveries(org)[note.id]
    assert ev["trace"] is None and ev["trace_rule"] == "ambiguous"
    assert ev["trace_candidates"] == sorted([a.id, b.id])


def test_root_notes_without_a_link_are_ambiguous_and_sender_without_context_too(org):
    note = org.send(ROOT, "ceo", "hello")
    assert note.trace is None and deliveries(org)[note.id]["trace_rule"] == "ambiguous"


def test_the_trace_follows_the_whole_chain_down_and_up(org):
    root_task = org.delegate(ROOT, "ceo", "Ship", "g", "a", budget=8)
    org.begin_run("ceo")
    sub = org.delegate("ceo", "ceo/eng", "Build", "g", "a", budget=3)
    org.begin_run("ceo/eng")
    up = org.report("ceo/eng", sub.id, "done", "built")
    org.end_run("ceo/eng", ok=True)
    org.end_run("ceo", ok=True)
    org.begin_run("ceo")
    top = org.report("ceo", root_task.id, "done", "shipped")
    assert {m.trace for m in (root_task, sub, up, top)} == {root_task.id}


def test_runtime_notices_carry_the_trace_of_the_task_when_given(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    notice = org.notify("ceo", "reminder", "do it", trace=task.id)
    assert notice.trace == task.id and deliveries(org)[notice.id]["trace_rule"] == "given"
    plain = org.notify("ceo", "plain", "no task")
    assert plain.trace is None and deliveries(org)[plain.id]["from"] == "runtime"


def test_old_messages_without_a_trace_still_load_and_work(org):
    old = org.dir("ceo") / "inbox" / "20200101T000000000000-root-aaaa.md"
    old.write_text("---\nid: 20200101T000000000000-root-aaaa\nfrom: root\nto: ceo\ntype: task\ntitle: Old\n"
                   "created: '2020-01-01T00:00:00+00:00'\nhops: 0\nbudget: 4\n---\nbody\n")
    m = org.runtime.message_parser.parse(old)
    assert m.trace is None and m.title == "Old"
    # an agent with only unstamped context sends without a trace and nothing breaks
    note = org.send("ceo", ROOT, "status?")
    assert note.trace is None
    result = org.report("ceo", m.id, "done", "ok")  # reply to an unstamped task: no link, falls through, no crash
    assert result.trace is None and deliveries(org)[result.id]["trace_rule"] == "ambiguous"


def test_the_trace_is_in_the_file_but_not_in_what_agents_are_shown(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    shown = task.render()
    assert task.id in shown and "trace" not in shown.lower().replace(task.id, "")
    text = (org.dir("ceo") / "inbox" / f"{task.id}.md").read_text()
    assert f"trace: {task.id}" in text
    assert "trace" not in org.run_prompt("ceo", [task]).replace(task.id, "").lower().split("# new messages")[1]


def test_trace_of_ignores_ids_that_are_paths(org):
    assert org.trace_of("ceo", "../../ORG") is None and org.trace_of("ceo", "") is None and org.trace_of("ceo", None) is None
