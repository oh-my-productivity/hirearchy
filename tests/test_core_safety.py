"""Extra regression tests for the core safety/lifecycle fixes (see QA_REPORT.md and test_qa_findings.py)."""

import pytest

from orgmcp.core import ROOT

ENG = "ceo/eng"


# ------------------------------------------------------------------- QA-12: delivery order and recovery
def _fail_writes_into(monkeypatch, marker):
    from orgmcp import core

    real = core.atomic_write

    def flaky(path, text):
        if marker in str(path):
            raise OSError("disk full")
        return real(path, text)

    monkeypatch.setattr(core, "atomic_write", flaky)
    return lambda: monkeypatch.setattr(core, "atomic_write", real)


def test_sender_copy_is_written_before_the_recipient_copy(org, monkeypatch):
    order = []
    from orgmcp import core

    real = core.atomic_write
    monkeypatch.setattr(core, "atomic_write", lambda path, text: (order.append(path.parent.name), real(path, text))[1])
    org.send(ROOT, "ceo", "hi")
    assert order == ["sent", "inbox"]


def test_recipient_write_failure_is_repaired_by_recover_without_minting_or_losing_budget(org, monkeypatch):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    restore = _fail_writes_into(monkeypatch, "/ceo/eng/inbox/")
    with pytest.raises(OSError):
        org.send("ceo", ENG, "grant", budget=4)
    restore()
    # charged but undelivered: nothing minted, nothing visible to the recipient yet
    assert org.budget("ceo") == 6 and org.budget(ENG) == 0 and org.unread(ENG) == 0
    assert org.recover() == []  # no interrupted runs; the delivery is finished silently
    assert org.budget("ceo") == 6 and org.budget(ENG) == 4 and org.unread(ENG) == 1
    assert org.recover() == [] and org.unread(ENG) == 1  # idempotent
    assert len(list((org.dir(ENG) / "inbox").glob("*.md"))) == 1


def test_recover_redelivers_to_root_too(org, monkeypatch):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")
    restore = _fail_writes_into(monkeypatch, str(org.root / "inbox"))
    with pytest.raises(OSError):
        org.report("ceo", task.id, "done", "ok")
    restore()
    assert org.unread(ROOT) == 0
    org.recover()
    assert org.unread(ROOT) == 1


def test_recover_does_not_duplicate_handled_messages_or_resurrect_retired_agents(org):
    sent = org.send(ROOT, "ceo", "one")
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)  # now in read/
    note = org.send("ceo", ENG, "to a soon retired agent")
    org.retire("ceo", "eng", "bye")
    assert org.recover() == []
    assert org.unread("ceo") == 0 and not org.exists(ENG) and not (org.dir(ENG)).exists()
    assert [m.id for m in org.messages("ceo", "read")] == [sent.id]
    assert note.id  # the sent copy remains as the audit trail


def test_recover_still_returns_inflight_batches(org):
    org.send(ROOT, "ceo", "x")
    org.begin_run("ceo")
    assert org.recover() == ["ceo"] and org.unread("ceo") == 1


def test_retire_tool_reports_the_refund(org):
    import asyncio

    from orgmcp.server import build_server

    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    org.delegate("ceo", ENG, "t", "g", "a", budget=4)
    result = asyncio.run(build_server(org, "ceo").call_tool("retire", {"name": ENG, "reason": "done"}))
    blocks = result[0] if isinstance(result, tuple) else result
    text = "\n".join(getattr(b, "text", "") for b in blocks)
    assert "retired ceo/eng" in text and "4 unspent run(s)" in text and "returned to ceo" in text
