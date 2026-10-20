# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import time

import pytest
from testkit.legacy.orgmcp.core import ROOT

from orgmcp import services

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


def test_feedback_note_starts_with_the_fixed_header_and_then_the_clients_words(svc):
    task = svc.request(ROOT, "brief", {"topic": "ai"})
    deliver(svc, task)
    note = svc.feedback(ROOT, task.id, "accept", "deliver as is")
    first, _, rest = note.body.partition("\n\n")
    assert first == (
        "Client feedback for reflection only: it does not change this task's acceptance criteria or outcome; "
        "report `done` only if every criterion is met."
    )
    assert rest == "deliver as is"
    assert services.feedback_text(note) == "deliver as is"
    assert services.feedback_text(svc.feedback(ROOT, task.id, "accept")) == ""
