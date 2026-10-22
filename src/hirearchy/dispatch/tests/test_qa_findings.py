# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import time

import pytest
from testkit.dispatch_loop import loop_over
from testkit.reach.hirearchy.app import wiring
from testkit.reach.hirearchy.core import ROOT, OrgError

from hirearchy.kernel import AtomicWriter
from hirearchy.kernel.testing import FailingAtomicWriter

ENG = "ceo/eng"

def test_qa4_oversized_message_does_not_wedge_the_agent(org, tmp_path):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    org.send(ROOT, "ceo", "x" * 3_000_000)  # a single long result/note is enough
    sched = loop_over(org, "kiro-cli")  # the stub kiro-cli of the fixture: under the launcher `true` would exit before any runStarted and count as a failure
    sched.acquire()
    try:
        for _ in range(4):
            sched.tick()
            while sched.state.runs:
                time.sleep(0.01)
                sched.reap()
    finally:
        sched.release()
    assert org.ledger("failures") == {} and not org.paused("ceo")


def test_qa12_failed_send_does_not_mint_budget(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    real = org.runtime

    flaky = FailingAtomicWriter(real.atomic_writer, lambda path: "/sent/" in str(path), OSError("disk full"))
    org.runtime = wiring.open_runtime(org.root, {AtomicWriter: flaky})
    with pytest.raises(OSError):
        org.send("ceo", ENG, "grant", budget=4)
    org.runtime = real
    assert org.budget("ceo") + org.budget(ENG) <= 10


def test_qa15_report_refuses_artifacts_outside_the_org(org, tmp_path):
    outside = tmp_path / "secret.txt"
    outside.write_text("not part of the org")
    org.send(ROOT, "ceo", "budget", budget=5)
    task = org.delegate("ceo", ENG, "t", "g", "a", budget=1)
    with pytest.raises(OrgError):
        org.report(ENG, task.id, "done", "ok", [str(outside)])
