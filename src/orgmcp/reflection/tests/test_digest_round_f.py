# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import time

import pytest
from testkit.legacy.orgmcp.core import ROOT

# ------------------------------------------------------------------------------------------ 3. feedback
SERVICE = dict(
    description="A brief.", acceptance=["At most 600 words"], budget=10,
    deliverable={"description": "one markdown file", "format": "markdown", "max_words": 600},
    inputs=[{"name": "topic", "description": "subject", "required": True}],
)


@pytest.fixture
def svc(org):
    org.define_service(ROOT, "ceo", "brief", **SERVICE)
    return org


def work(org, addr, runs=1):
    batch = org.begin_run(addr)
    for _ in range(runs):
        org.start_run_log(addr)
        time.sleep(0.002)
    return batch


def deliver(org, task, status="done", lessons="ok"):
    work(org, "ceo")
    msg = org.report("ceo", task.id, status, "Delivered.", lessons=lessons)
    org.end_run("ceo", ok=True)
    return msg


def test_the_digest_quotes_the_clients_words_without_the_header(svc):
    task = svc.request(ROOT, "brief", {"topic": "ai"})
    deliver(svc, task)
    svc.feedback(ROOT, task.id, "reject", "Missed two items.")
    digest = svc.runtime.reflection_digest.reflection_digest("ceo", "brief")
    assert 'client feedback: reject "Missed two items."' in digest and "reflection only" not in digest


# ------------------------------------------------------------------------------------------ 5. digest order
def test_the_digest_shows_the_latest_lessons_first_and_earlier_ones_after(svc):
    first = svc.request(ROOT, "brief", {"topic": "ai"})
    deliver(svc, first, lessons="Ran cleanly; no changes needed.")
    rework = svc.request(ROOT, "brief", {"topic": "ai"}, revises=first.id, budget=4)
    deliver(svc, rework, lessons="Two items were missed: add a pre-read step.")
    digest = svc.runtime.reflection_digest.reflection_digest("ceo", "brief")
    line = next(x for x in digest.splitlines() if x.startswith("- case "))
    assert line.index('lessons: "Two items were missed') < line.index('earlier: "Ran cleanly; no changes needed.')
