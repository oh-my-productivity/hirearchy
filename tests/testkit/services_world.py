"""The world of the service tests: a weekly-brief service offered by ``ceo``, and the helpers that drive it (define, work, deliver, request, call a tool, run the CLI).

Shared by the tests of services, reflection and the service tools; ``svc`` is a fixture (import it into a test module to use it).
"""

import asyncio
import time

import pytest

from hirearchy.app.wire_cli import run_cli as main
from hirearchy.core import ROOT, split_frontmatter
from hirearchy.services.testing import unheld_requests


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


def request_unheld(org, topic="ai", name="weekly-brief", **kw):
    """Root's new request of ``name`` that clause 2 (REQUEST-UNANSWERED) does not hold: judged against a record with no rejection, over the organization's
    own ports. For the tests of another rule that need a rejection with no answer and a new request in the same story; the tests of clause 2 use
    ``request``."""
    rt = org.runtime
    requester = unheld_requests(
        rt.agents, rt.service_catalog, rt.mailbox, rt.message_sender, rt.judged_versions, rt.case_allowance, rt.service_store,
    )
    given = {"title": "", "note": "", "extra_acceptance": None, "budget": None, "revises": None, "source": None, "base": None, **kw}
    return requester.request(ROOT, name, {"topic": topic}, **given)


def confirmed_amendment(org, criterion, topic="confirm", owner="ceo", name="weekly-brief"):
    """The user rejects a fresh delivery and answers yes to the question about ``criterion``: ``define_service(..., answers=<the rejection>,
    about=<a current id>, words="Yes, add it.")`` adds it and the product writes the link that confirms it (Rule A); what admits a revision citing
    it by rule (c). Returns the new id."""
    task = org.request(ROOT, name, {"topic": topic})
    deliver(org, owner, task)
    no = org.feedback(ROOT, task.id, "reject", f"Missing: {criterion}", source="human")
    about = next(c.id for c in org.runtime.service_catalog.criteria(owner, name) if c.current)
    org.define_service(ROOT, owner, name, add_acceptance=[criterion], answers=no.id, about=about, words="Yes, add it.")
    return next(c.id for c in reversed(org.runtime.service_catalog.criteria(owner, name)) if c.text == criterion and c.current)


def write_version(org, version, acceptance, owner="ceo", name="weekly-brief", **basis):
    """Write contract version ``version`` of the service straight into the store (the current one is archived) with ``basis`` keys in its
    frontmatter (``answers``, ``about``, ``words``, ``initiated``), as a version of 0a.2 carries them. A version's basis is its own: the keys of
    the version before are not copied."""
    meta, body = org.runtime.service_store.read_contract(owner, name)
    meta = {k: v for k, v in meta.items() if k not in ("answers", "about", "words", "initiated")}
    defined = org.runtime.clock.now().isoformat(timespec="microseconds")
    org.runtime.service_store.write_contract(
        owner, name, {**meta, "version": version, "acceptance": list(acceptance), "defined_by": ROOT, "defined": defined, **basis}, body, version - 1,
    )


def amend_legacy(org, add_acceptance=(), remove_acceptance=(), owner="ceo", name="weekly-brief"):
    """Root's amendment written the way a version of the contract was before 0a.2: criteria added or removed, no answer and no words in the
    frontmatter (a legacy version: the 0a.1 rule applies to its criteria, so a human `confirms` link makes an added one eligible). Today's
    `define_service` records the user's words, so a test of the legacy rule writes the version itself."""
    current = org.runtime.service_store.read_contract(owner, name)[0]
    acceptance = [t for t in current["acceptance"] if t not in remove_acceptance] + list(add_acceptance)
    write_version(org, current["version"] + 1, acceptance, owner=owner, name=name)


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
