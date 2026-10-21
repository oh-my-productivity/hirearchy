"""``FAKE_MODE=service`` of the testkit fake agent: a service request delivered through an author and then a checker, under the real scheduler loop."""

import os
import sys
import time

from testkit import FAKE_AGENT
from testkit.scheduler_loop import loop_over

from hirearchy.core import ROOT, Org
from hirearchy.reflection import lessons_of


def run_until_idle(org, reports, limit=60.0):
    def runner(o, addr, prompt):
        env = {**os.environ, "ORG_ROOT": str(o.root), "ORG_AGENT": addr, "FAKE_MODE": "service", "FAKE_REPORTS": ",".join(reports)}
        return [sys.executable, str(FAKE_AGENT)], o.dir(addr), env

    loop = loop_over(org, runner, echo=lambda _: None)
    loop.acquire()
    try:
        deadline = time.time() + limit
        while time.time() < deadline:
            if not loop.tick():
                return
            time.sleep(0.02)
        raise AssertionError("organization never went idle")
    finally:
        loop.release()


def test_the_service_mode_delivers_through_author_then_checker(tmp_path):
    org = Org.init(tmp_path / "org", "m")
    org.hire(ROOT, "lead", "Lead", "Lead the team.", can_hire=True, max_children=3)
    org.hire("lead", "checker", "Checker", "Check.")  # hired first on purpose: the order is FAKE_REPORTS', not the sorted one
    org.hire("lead", "author", "Author", "Write.")
    org.define_service(ROOT, "lead", "memo", description="A memo.", inputs=[{"name": "topic", "description": "what", "required": True}],
                       acceptance=["At most 100 words"], deliverable={"description": "one file", "format": "markdown"}, budget=12)
    request = org.request(ROOT, "memo", {"topic": "x"})

    run_until_idle(org, ["lead/author", "lead/checker"])

    sent = [m for m in org.sent("lead") if m.type == "task"]  # in the order the lead delegated them
    assert [(m.to, m.title) for m in sent] == [("lead/author", request.title), ("lead/checker", f"check: {request.title}")]
    results = sorted((m for m in org.received("lead") if m.type == "result"), key=lambda m: m.id)
    assert [m.sender for m in results] == ["lead/author", "lead/checker"]
    final = next(m for m in org.received(ROOT) if m.type == "result" and m.reply_to == request.id)
    assert final.status == "done" and lessons_of(final) == "Delivered by the team; nothing to change."
    assert final.id > results[-1].id  # the checker's result is the last one before the lead's
    assert "lead/author/work/out.md" in final.body  # the author's artifact travels with the lead's result
    # a leaf reports with lessons when its task carries a service, and without when it does not
    assert lessons_of(results[0]) == "" and lessons_of(results[1]) == ""
