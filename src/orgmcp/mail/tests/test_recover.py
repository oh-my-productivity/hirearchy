# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import pytest
from testkit.legacy.orgmcp.core import ROOT

ENG = "ceo/eng"


# ------------------------------------------------------------------- QA-12: delivery order and recovery
def _fail_writes_into(monkeypatch, marker):
    from testkit.legacy.orgmcp import core

    real = core.atomic_write

    def flaky(path, text):
        if marker in str(path):
            raise OSError("disk full")
        return real(path, text)

    monkeypatch.setattr(core, "atomic_write", flaky)
    return lambda: monkeypatch.setattr(core, "atomic_write", real)


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
