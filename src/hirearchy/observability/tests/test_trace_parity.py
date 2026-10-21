"""The trace the runtime stamps at send time (``traces``) and the trace ``MessageTraceDeriver`` derives for a message that has none say the same.

The messages are sent through the real stamper over the mailboxes on disk and in memory; then the deriver is asked about the same messages as if
nobody had recorded a trace. Where the two answer differently on purpose the test says so: the deriver works from the files afterwards, the
stamper from the sender's boxes at the moment of sending."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import pytest

from hirearchy.kernel import STAMP_FORMAT, Message, stamp_of
from hirearchy.kernel.testing import T0
from hirearchy.observability._derive import MessageTraceDeriver
from hirearchy.observability._messages import Msg
from hirearchy.runs.testing import MemoryRuns
from hirearchy.traces.testing import TraceHarness, fs_traces, memory_traces

from ._support import implementations


RULES = {"given": "recorded", "new": "derived:new", "link": "derived:link", "open-task": "derived:open-task", "batch": "derived:batch",
         "ambiguous": "unknown"}


@dataclass
class Sent:
    message: Message
    rule: str


class Flow:
    """Messages sent one after the other, ``n`` seconds after 10:00, through the stamper; and the run logs the agents left."""

    def __init__(self, harness: TraceHarness) -> None:
        self.h, self.runs, self.count = harness, MemoryRuns(), 0
        self.sent: list[Sent] = []
        for addr in ("ceo", "ceo/eng"):
            harness.mail.agent(addr)

    def send(self, n: int, sender: str, to: str, kind: str, box: str = "inbox", **fields: object) -> Sent:
        self.count += 1
        at = T0 + timedelta(seconds=n)
        msg = Message(sender=sender, to=to, type=kind, body="b", title="t", id=f"{at:{STAMP_FORMAT}}-{sender.replace('/', '.')}-{self.count:04x}",
                      created=at.isoformat(), **fields)  # type: ignore[arg-type]
        rule, _ = self.h.stamper.stamp(msg)
        if box == "inbox":
            self.h.mail.writer.store(msg)
        else:
            if sender != "runtime":
                self.h.mail.put(f"{sender}/sent/{msg.id}.md", msg.to_text())
            self.h.mail.put(f"{to}/{box}/{msg.id}.md", msg.to_text())
        out = Sent(msg, rule)
        self.sent.append(out)
        return out

    def run(self, addr: str, n: int) -> None:
        self.runs.put_log(addr, f"{T0 + timedelta(seconds=n):{STAMP_FORMAT}}.log", "")

    def derived(self) -> dict[str, tuple[str | None, str]]:
        """What the deriver says about every message sent, with the traces taken out of the files."""
        msgs = {
            s.message.id: Msg(
                id=s.message.id, sender=s.message.sender, to=s.message.to, type=s.message.type, title="", status=s.message.status, budget=0,
                reply_to=s.message.reply_to, revises=s.message.revises, service=None, feedback=None, wake=True,
                trace=s.message.trace if s.rule == "given" else None,
                t=stamp_of(s.message.id) or T0,
            )
            for s in self.sent
        }
        deriver = MessageTraceDeriver(msgs, None, self.runs)
        return {mid: deriver.of(mid) for mid in msgs}


@pytest.fixture(params=implementations([fs_traces, memory_traces]))
def flow(request: pytest.FixtureRequest, tmp_path: Path) -> Flow:
    made: Callable[[Path], TraceHarness] = request.param
    return Flow(made(tmp_path))


def test_a_request_from_its_start_to_its_final_result_is_derived_as_it_was_stamped(flow: Flow) -> None:
    task = flow.send(0, "root", "ceo", "task")
    sub = flow.send(1, "ceo", "ceo/eng", "task")  # ceo holds one open task: open-task
    answer = flow.send(2, "ceo/eng", "ceo", "result", status="done", reply_to=sub.message.id)  # link
    rework = flow.send(3, "root", "ceo", "task", revises=task.message.id)  # link
    final = flow.send(4, "ceo", "root", "result", status="done", reply_to=task.message.id)  # link
    assert [s.rule for s in flow.sent] == ["new", "open-task", "link", "link", "link"]
    derived = flow.derived()
    for s in flow.sent:
        assert derived[s.message.id] == (task.message.trace, RULES[s.rule]), s.message.id
    assert {s.message.trace for s in (task, sub, answer, rework, final)} == {task.message.id}


def test_the_batch_of_a_run_is_derived_as_it_was_stamped(flow: Flow) -> None:
    task = flow.send(0, "root", "ceo", "task")
    flow.send(3, "ceo", "root", "result", status="done", reply_to=task.message.id)
    flow.run("ceo", 10)
    # a runtime notice about another request wakes ceo: its batch has that one request, and ceo has no task open
    notice = flow.send(20, "runtime", "ceo", "note", box="inflight", trace="T-other")
    flow.run("ceo", 30)
    note = flow.send(40, "ceo", "root", "note")
    assert (notice.rule, note.rule, note.message.trace) == ("given", "batch", "T-other")
    assert flow.derived()[note.message.id] == ("T-other", "derived:batch")


def test_nothing_to_go_by_is_ambiguous_and_unknown(flow: Flow) -> None:
    note = flow.send(5, "ceo", "root", "note")
    assert note.rule == "ambiguous" and note.message.trace is None
    assert flow.derived()[note.message.id] == (None, "unknown")


def test_two_open_requests_are_ambiguous_for_the_stamper_and_the_batch_of_the_previous_run_may_answer_for_the_deriver(flow: Flow) -> None:
    """Different on purpose: the stamper looks at the inflight box of the moment, the deriver at what arrived before the run."""
    flow.run("ceo", 10)
    first = flow.send(20, "root", "ceo", "task")
    flow.run("ceo", 30)
    flow.send(32, "root", "ceo", "task")
    note = flow.send(40, "ceo", "root", "note")
    assert (note.rule, note.message.trace) == ("ambiguous", None)
    assert flow.derived()[note.message.id] == (first.message.id, "derived:batch")


def test_a_runtime_message_that_refers_to_a_task_is_linked_by_the_deriver_only(flow: Flow) -> None:
    """Different on purpose: the runtime never links when it stamps; the deriver reads ``reply_to`` whoever wrote it."""
    task = flow.send(0, "root", "ceo", "task")
    notice = flow.send(5, "runtime", "ceo", "note", reply_to=task.message.id)
    assert (notice.rule, notice.message.trace) == ("ambiguous", None)
    assert flow.derived()[notice.message.id] == (task.message.id, "derived:link")
