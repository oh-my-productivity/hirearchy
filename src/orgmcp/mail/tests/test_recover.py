# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.orgmcp.app import wiring
from testkit.reach.orgmcp.core import ROOT

from orgmcp.kernel import AtomicWriter
from orgmcp.kernel.testing import FailingAtomicWriter, fs_atomic_writer

ENG = "ceo/eng"


# ------------------------------------------------------------------- QA-12: delivery order and recovery
def _writer_into(org, fails=lambda path: False):
    """The organization goes on over a runtime whose atomic writer fails for the paths ``fails`` selects (and records every attempt)."""
    writer = FailingAtomicWriter(fs_atomic_writer(org.root).writer, fails=fails, error=OSError("disk full"))
    org.runtime = wiring.open_runtime(org.root, {AtomicWriter: writer})
    return writer


def _fail_writes_into(org, marker):
    armed = {"on": True}
    _writer_into(org, fails=lambda path: armed["on"] and marker in str(path))
    return lambda: armed.update(on=False)


def test_recover_redelivers_to_root_too(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")
    restore = _fail_writes_into(org, str(org.root / "inbox"))
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
