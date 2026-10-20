# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.legacy.orgmcp.app import wiring
from testkit.legacy.orgmcp.core import ROOT

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


def test_sender_copy_is_written_before_the_recipient_copy(org):
    writer = _writer_into(org)
    org.send(ROOT, "ceo", "hi")
    order = [path.parent.name for path in writer.attempts]
    assert order == ["sent", "inbox"]


def test_recipient_write_failure_is_repaired_by_recover_without_minting_or_losing_budget(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    restore = _fail_writes_into(org, "/ceo/eng/inbox/")
    with pytest.raises(OSError):
        org.send("ceo", ENG, "grant", budget=4)
    restore()
    # charged but undelivered: nothing minted, nothing visible to the recipient yet
    assert org.budget("ceo") == 6 and org.budget(ENG) == 0 and org.unread(ENG) == 0
    assert org.recover() == []  # no interrupted runs; the delivery is finished silently
    assert org.budget("ceo") == 6 and org.budget(ENG) == 4 and org.unread(ENG) == 1
    assert org.recover() == [] and org.unread(ENG) == 1  # idempotent
    assert len(list((org.dir(ENG) / "inbox").glob("*.md"))) == 1
