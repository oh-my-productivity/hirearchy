"""The traces slice of the ``Org`` facade: ``trace_of``, ``open_task_traces``, ``context_trace`` and ``stamp_trace`` behave as they always
did (green before and after), and now go through the trace ports of the runtime."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest

from hirearchy.app import Org
from hirearchy.kernel import Message
from hirearchy.traces import TraceLookup, TraceStamper

def use(org: Org, **ports: Any) -> None:
    org.runtime = dataclasses.replace(org.runtime, **ports)


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.", can_hire=True, max_children=2)
    made.hire("ceo", "eng", "Engineer", "Build.")
    return made


# ----------------------------------------------------------------------------------- as it always was (green before and after)


def test_trace_of_a_message_in_each_box_of_that_agent_only(org: Org) -> None:
    task = org.delegate("root", "ceo", "T", "g", "a", budget=5)
    assert org.trace_of("ceo", task.id) == task.id and org.trace_of("root", task.id) == task.id  # inbox of ceo, sent of root
    assert org.trace_of("ceo/eng", task.id) is None
    org.begin_run("ceo")
    assert org.trace_of(" /ceo/ ", task.id) == task.id  # now inflight
    org.end_run("ceo", ok=True)
    assert org.trace_of("ceo", task.id) == task.id  # now read


def test_trace_of_an_id_that_is_not_a_file_name_or_a_file_that_does_not_parse(org: Org) -> None:
    task = org.delegate("root", "ceo", "T", "g", "a", budget=5)
    assert org.trace_of("ceo", f"../inbox/{task.id}") is None and org.trace_of("ceo", "") is None and org.trace_of("ceo", None) is None
    broken = org.dir("ceo") / "inbox" / "20260101T000000000001-root-aaaa.md"
    broken.write_text("---\nfrom: [unclosed\n---\n", encoding="utf-8")
    assert org.trace_of("ceo", "20260101T000000000001-root-aaaa") is None


def test_open_task_traces_and_the_context_of_an_agent(org: Org) -> None:
    a = org.delegate("root", "ceo", "A", "g", "a", budget=8)
    assert org.open_task_traces("ceo") == [a.id] and org.context_trace("ceo") == (a.id, "open-task", [])
    b = org.delegate("root", "ceo", "B", "g", "a", budget=8)
    assert org.open_task_traces("ceo") == [a.id, b.id] and org.context_trace("ceo") == (None, "ambiguous", sorted([a.id, b.id]))
    org.begin_run("ceo")
    assert org.context_trace("ceo") == (None, "ambiguous", sorted([a.id, b.id]))
    assert org.open_task_traces("root") == [] and org.open_task_traces("runtime") == [] and org.open_task_traces("ghost") == []


def test_stamp_trace_returns_the_rule_and_sets_the_trace(org: Org) -> None:
    msg = Message(sender="root", to="ceo", type="task", body="b", title="t", id="20260101T000000000009-root-aaaa")
    assert org.stamp_trace(msg) == ("new", []) and msg.trace == msg.id
    note = Message(sender="ceo", to="root", type="note", body="b", id="20260101T000000000010-ceo-aaaa")
    assert org.stamp_trace(note) == ("ambiguous", []) and note.trace is None


# -------------------------------------------------------------------------------------------- through the ports (red until wired)


class FixedLookup(TraceLookup):
    def trace_of(self, addr: str, msg_id: str | None) -> str | None:
        return f"{addr}:{msg_id}"

    def open_task_traces(self, addr: str) -> list[str | None]:
        return [f"open:{addr}", None]

    def context_trace(self, addr: str) -> tuple[str | None, str, list[str]]:
        return f"ctx:{addr}", "batch", ["x"]


class FixedStamper(TraceStamper):
    def stamp(self, msg: Message) -> tuple[str, list[str]]:
        msg.trace = "STAMPED"
        return "given", ["c"]


def test_the_lookups_come_from_the_trace_lookup_of_the_runtime(org: Org) -> None:
    use(org, trace_lookup=FixedLookup())
    assert org.trace_of("ceo", "m") == "ceo:m"
    assert org.open_task_traces("ceo") == ["open:ceo", None]
    assert org.context_trace("ceo") == ("ctx:ceo", "batch", ["x"])


def test_stamp_trace_comes_from_the_trace_stamper_of_the_runtime(org: Org) -> None:
    use(org, trace_stamper=FixedStamper())
    msg = Message(sender="root", to="ceo", type="task", body="b", id="20260101T000000000009-root-aaaa")
    assert org.stamp_trace(msg) == ("given", ["c"]) and msg.trace == "STAMPED"
