"""The world of the service tests: a weekly-brief service offered by ``ceo``, and the helpers that drive it (define, work, deliver, request, call a tool, run the CLI).

Shared by the tests of services, reflection and the service tools; ``svc`` is a fixture (import it into a test module to use it).
"""

import asyncio
import time

import pytest

from hirearchy.app.wire_cli import run_cli as main
from hirearchy.core import ROOT, split_frontmatter


ENG = "ceo/eng"


BRIEF = dict(
    description="A one-page brief on the past week's news about a topic.",
    inputs=[
        {"name": "topic", "description": "what the brief is about", "required": True},
        {"name": "week", "description": "ISO week; default the current one", "required": False},
    ],
    acceptance=["At most 600 words", "Every factual claim has a source URL"],
    deliverable={"description": "one markdown file", "format": "markdown", "max_words": 600},
    budget=10,
)


def define(org, owner="ceo", name="weekly-brief", actor=ROOT, **over):
    return org.define_service(actor, owner, name, **{**BRIEF, **over})


def work(org, addr, runs=1):
    """The agent reads its batch and uses ``runs`` runs (log files), as a scheduler pass would."""
    batch = org.begin_run(addr)
    for _ in range(runs):
        org.start_run_log(addr)
        time.sleep(0.002)
    return batch


def deliver(org, owner, task, status="done", lessons="Worked; no change needed.", runs=1, summary="Delivered."):
    work(org, owner, runs)
    msg = org.report(owner, task.id, status, summary, lessons=lessons)
    org.end_run(owner, ok=True)
    return msg


def request(org, topic="ai", **kw):
    return org.request(ROOT, "weekly-brief", {"topic": topic}, **kw)


def confirmed_amendment(org, criterion, topic="confirm", owner="ceo", name="weekly-brief"):
    """The user rejects a fresh delivery, the contract gains ``criterion`` and the user's yes to it is recorded (a ``confirms`` link naming its
    new id): what admits a revision citing it by rule (c). Returns the new id."""
    task = org.request(ROOT, name, {"topic": topic})
    deliver(org, owner, task)
    no = org.feedback(ROOT, task.id, "reject", f"Missing: {criterion}", source="human")
    org.define_service(ROOT, owner, name, add_acceptance=[criterion])
    new = next(c.id for c in reversed(org.runtime.service_catalog.criteria(owner, name)) if c.text == criterion and c.current)
    org.feedback(ROOT, task.id, "reject", "Yes, add it.", source="human", criterion=[new], confirms=no.id)
    return new


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def fails(server, tool, **args) -> str:
    with pytest.raises(Exception) as info:
        call(server, tool, **args)
    return str(info.value)


def contract_meta(org, owner="ceo", name="weekly-brief"):
    return split_frontmatter((org.dir(owner) / "services" / name / "SERVICE.md").read_text())


def playbook_meta(org, owner="ceo", name="weekly-brief"):
    return split_frontmatter((org.dir(owner) / "services" / name / "PLAYBOOK.md").read_text())


@pytest.fixture
def svc(org):
    """ceo offers weekly-brief (contract v1, no playbook)."""
    define(org)
    return org


def cli(org, *args):
    main(["--root", str(org.root), *args])
