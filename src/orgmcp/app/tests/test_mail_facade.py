"""The mail methods of ``Org`` (``MailMixin``) call the ports of ``org.runtime`` and nothing else: a runtime built on the in-memory
mailbox answers them without any file on disk. The behaviour itself is in the contract suites of ``orgmcp.mail`` and in
``test_core``, ``test_wakes``, ``test_core_safety`` and ``test_qa_findings`` (which still go through the facade over the real files)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.app import Org, wiring
from orgmcp.kernel import Message
from orgmcp.mail import BatchStore, MailboxReader, MailboxWriter
from orgmcp.mail.testing import MemoryMailbox


@pytest.fixture
def org(tmp_path: Path) -> Org:
    return Org.init(tmp_path / "org", "mission")


def memory(org: Org) -> MemoryMailbox:
    """``org`` now reads and moves messages in memory (its files on disk are not looked at)."""
    box = MemoryMailbox()
    box.agents.put("ceo/AGENT.md", "---\nrole: R\n---\nx\n")
    box.agents.put("cto/AGENT.md", "---\nrole: R\n---\nx\n")
    org.runtime = wiring.open_runtime(org.root, {MailboxReader: box, MailboxWriter: box, BatchStore: box})
    return box


def task(n: int, to: str = "ceo", sender: str = "root") -> Message:
    return Message(sender=sender, to=to, type="task", body="b", id=f"20260101T0000000000{n:02d}-{sender}-aaaa", created="2026-01-01T00:00:00+00:00")


def result(n: int, task_id: str, status: str = "done") -> Message:
    return Message(sender="ceo", to="root", type="result", body="r", reply_to=task_id, status=status,
                   id=f"20260101T0000000000{n:02d}-ceo-aaaa", created="2026-01-01T00:00:00+00:00")


def test_the_listing_methods_ask_the_mailbox(org: Org) -> None:
    box = memory(org)
    box.store(task(1))
    box.store(task(2))
    assert [m.id for m in org.messages("ceo", "inbox")] == [task(1).id, task(2).id]
    assert [m.id for m in org.received("ceo")] == [task(1).id, task(2).id]
    assert [m.id for m in org.sent("root")] == [task(1).id, task(2).id]
    assert org.find_received("ceo", task(2).id) is not None and org.find_received("ceo", "nope") is None
    assert org.unread("ceo") == 2 and org.running("ceo") is False


def test_the_task_views_come_from_the_task_query(org: Org) -> None:
    box = memory(org)
    box.store(task(1))
    box.store(task(2))
    box.store(result(3, task(1).id, "blocked"))
    assert [m.id for m in org.open_tasks("ceo")] == [task(2).id]
    assert [m.id for m in org.outstanding("root")] == [task(2).id]  # a result of any status closes it for the sender
    assert [m.id for m in org._blocked_tasks("ceo")] == [task(1).id]


def test_the_run_lifecycle_is_the_batch_store(org: Org) -> None:
    box = memory(org)
    box.store(task(1))
    assert [m.id for m in org.begin_run("ceo")] == [task(1).id] and org.running("ceo") is True and org.unread("ceo") == 0
    org.end_run("ceo", ok=False)
    assert org.running("ceo") is False and org.unread("ceo") == 1
    org.begin_run("ceo")
    assert org.recover() == ["ceo"] and org.unread("ceo") == 1
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    assert [m.id for m in org.messages("ceo", "read")] == [task(1).id]


def test_redelivery_is_the_batch_stores(org: Org) -> None:
    box = memory(org)
    box.agents.put(f"cto/sent/{task(1, 'ceo', 'cto').id}.md", task(1, "ceo", "cto").to_text())
    assert org.redeliver_orphans() == [task(1, "ceo", "cto").id]
    assert [m.id for m in org.messages("ceo", "inbox")] == [task(1, "ceo", "cto").id]


def test_the_legacy_static_wakes_reads_a_file_through_the_process_parser(org: Org, tmp_path: Path) -> None:
    held, waking, broken = tmp_path / "a.md", tmp_path / "b.md", tmp_path / "c.md"
    held.write_text("---\nfrom: root\nto: ceo\ntype: note\nwake: false\n---\nx\n", encoding="utf-8")
    waking.write_text("---\nfrom: root\nto: ceo\ntype: note\n---\nx\n", encoding="utf-8")
    broken.write_text("---\nfrom: [oops\n---\nx\n", encoding="utf-8")
    assert [Org._wakes(held), Org._wakes(waking), Org._wakes(broken), Org._wakes(tmp_path / "absent.md")] == [False, True, True, True]
