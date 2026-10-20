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


def test_sender_copy_is_written_before_the_recipient_copy(org, monkeypatch):
    order = []
    from testkit.legacy.orgmcp import core

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
