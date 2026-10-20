# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import shutil
import time

import pytest
from testkit.legacy.orgmcp import core
from testkit.legacy.orgmcp.core import ROOT, OrgError
from testkit.legacy.orgmcp.scheduler import Scheduler, kiro_runner

ENG = "ceo/eng"
TRUE = shutil.which("true") or "/usr/bin/true"


def test_qa4_oversized_message_does_not_wedge_the_agent(org, tmp_path, monkeypatch):
    monkeypatch.setattr("orgmcp.scheduler.ensure_kiro_profile", lambda tools, org=None: "orgmcp")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    org.send(ROOT, "ceo", "x" * 3_000_000)  # a single long result/note is enough
    sched = Scheduler(org, kiro_runner(TRUE), echo=lambda _: None)  # `true` stands in for kiro-cli
    sched.acquire()
    try:
        for _ in range(4):
            sched.tick()
            while sched.runs:
                time.sleep(0.01)
                sched._reap()
    finally:
        sched.release()
    assert org.ledger("failures") == {} and not org.paused("ceo")


def test_qa12_failed_send_does_not_mint_budget(org, monkeypatch):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    real = core.atomic_write

    def flaky(path, text):
        if "/sent/" in str(path):
            raise OSError("disk full")
        return real(path, text)

    monkeypatch.setattr(core, "atomic_write", flaky)
    with pytest.raises(OSError):
        org.send("ceo", ENG, "grant", budget=4)
    monkeypatch.setattr(core, "atomic_write", real)
    assert org.budget("ceo") + org.budget(ENG) <= 10


def test_qa15_report_refuses_artifacts_outside_the_org(org, tmp_path):
    outside = tmp_path / "secret.txt"
    outside.write_text("not part of the org")
    org.send(ROOT, "ceo", "budget", budget=5)
    task = org.delegate("ceo", ENG, "t", "g", "a", budget=1)
    with pytest.raises(OrgError):
        org.report(ENG, task.id, "done", "ok", [str(outside)])
