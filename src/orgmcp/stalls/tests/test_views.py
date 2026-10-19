"""``FingerprintTaskViews``: the task views of an agent are recomputed only when its set of message files changes (the former ``Scheduler._task_view``)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from orgmcp.kernel import Message
from orgmcp.mail.testing import CountingMessageParser, MailHarness, fs_mailbox, memory_mailbox
from orgmcp.stalls._ports import TaskViews
from orgmcp.stalls._views import FingerprintTaskViews
from orgmcp.stalls.testing import CountingTasks

from ._support import RED

Make = Callable[[Path], MailHarness]


class Views:
    """The views over one mailbox harness, and the means to put mail in it."""

    def __init__(self, mail: MailHarness) -> None:
        self.mail = mail
        self.tasks = CountingTasks(mail.tasks)
        self.views = FingerprintTaskViews(self.tasks, mail.fingerprint)
        self.numbers = 0

    def send(self, sender: str, to: str, type: str = "task", reply_to: str | None = None) -> Message:
        self.numbers += 1
        for addr in (sender, to):
            if addr != "root":
                self.mail.agent(addr)
        msg = Message(sender=sender, to=to, type=type, title="t", body="b", id=f"20260101T0000000000{self.numbers:02d}-{sender}-aaaa",
                      created="2026-01-01T00:00:00+00:00", reply_to=reply_to, status="done" if type == "result" else None)
        self.mail.writer.store(msg)
        return msg


@pytest.fixture(params=[fs_mailbox, memory_mailbox], ids=lambda factory: factory.__name__)
def v(request: pytest.FixtureRequest, tmp_path: Path) -> Views:
    make: Make = request.param
    return Views(make(tmp_path))


def test_it_is_a_task_views_port(v: Views) -> None:
    assert isinstance(v.views, TaskViews)


@RED
def test_the_views_are_the_tasks_of_the_task_query(v: Views) -> None:
    task = v.send("root", "ceo")
    v.send("ceo", "ceo/eng")
    assert [t.id for t in v.views.open_tasks("ceo")] == [task.id]
    assert [t.to for t in v.views.outstanding("ceo")] == ["ceo/eng"]


@RED
def test_an_unchanged_mailbox_is_not_asked_again(v: Views) -> None:
    v.send("root", "ceo")
    v.views.open_tasks("ceo")
    v.views.outstanding("ceo")
    assert v.tasks.computed == [("open_tasks", "ceo"), ("outstanding", "ceo")]
    for _ in range(3):
        v.views.open_tasks("ceo")
        v.views.outstanding("ceo")
    assert len(v.tasks.computed) == 2


@RED
def test_a_view_nobody_asked_for_is_not_computed(v: Views) -> None:
    v.send("root", "ceo")
    v.views.open_tasks("ceo")
    assert v.tasks.computed == [("open_tasks", "ceo")]


@RED
def test_a_message_that_only_moves_between_the_received_boxes_changes_nothing(v: Views) -> None:
    v.send("root", "ceo")
    v.views.open_tasks("ceo")
    v.mail.batches.begin("ceo")  # inbox -> inflight
    v.views.open_tasks("ceo")
    v.mail.batches.end("ceo", True)  # inflight -> read
    v.views.open_tasks("ceo")
    assert len(v.tasks.computed) == 1


@RED
def test_a_new_received_message_recomputes_both_views(v: Views) -> None:
    v.send("root", "ceo")
    v.views.open_tasks("ceo")
    v.views.outstanding("ceo")
    task = v.send("root", "ceo")
    assert task.id in [t.id for t in v.views.open_tasks("ceo")]
    v.views.outstanding("ceo")
    assert v.tasks.computed[2:] == [("open_tasks", "ceo"), ("outstanding", "ceo")]


@RED
def test_a_new_sent_message_recomputes_and_shows_the_task_closed(v: Views) -> None:
    task = v.send("root", "ceo")
    assert [t.id for t in v.views.open_tasks("ceo")] == [task.id]
    v.send("ceo", "root", type="result", reply_to=task.id)
    assert v.views.open_tasks("ceo") == []
    assert len(v.tasks.computed) == 2


@RED
def test_agents_are_remembered_apart(v: Views) -> None:
    v.send("root", "ceo")
    v.send("root", "dev")
    v.views.open_tasks("ceo")
    v.views.open_tasks("dev")
    v.send("root", "dev")
    v.views.open_tasks("ceo")
    v.views.open_tasks("dev")
    assert v.tasks.computed == [("open_tasks", "ceo"), ("open_tasks", "dev"), ("open_tasks", "dev")]


@RED
def test_retain_forgets_the_agents_that_are_gone(v: Views) -> None:
    v.send("root", "ceo")
    v.send("root", "dev")
    v.views.open_tasks("ceo")
    v.views.open_tasks("dev")
    v.views.retain(["ceo"])
    v.views.open_tasks("ceo")
    v.views.open_tasks("dev")
    assert v.tasks.computed == [("open_tasks", "ceo"), ("open_tasks", "dev"), ("open_tasks", "dev")]


@RED
def test_retain_of_an_agent_that_was_never_asked_about_is_harmless(v: Views) -> None:
    v.views.retain(["nobody"])
    v.views.retain([])


@RED
def test_the_files_of_an_unchanged_mailbox_are_not_even_opened_again(tmp_path: Path) -> None:
    v = Views(fs_mailbox(tmp_path))
    parser = v.mail.parser
    assert isinstance(parser, CountingMessageParser)
    v.send("root", "ceo")
    v.views.open_tasks("ceo")
    v.views.outstanding("ceo")
    asked = len(parser.loaded)
    for _ in range(3):
        v.views.open_tasks("ceo")
        v.views.outstanding("ceo")
    assert len(parser.loaded) == asked


@RED
def test_rebound_views_keep_what_is_remembered_and_ask_the_new_ports(tmp_path: Path) -> None:
    v = Views(fs_mailbox(tmp_path))
    v.send("root", "ceo")
    v.views.open_tasks("ceo")
    again = CountingTasks(v.mail.tasks)
    rebound = v.views.rebound(again, v.mail.fingerprint)
    rebound.open_tasks("ceo")
    assert again.computed == [] and len(v.tasks.computed) == 1  # the memo came along
    v.send("root", "ceo")
    rebound.open_tasks("ceo")
    assert again.computed == [("open_tasks", "ceo")]  # a change is computed by the new ports
