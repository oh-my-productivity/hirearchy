"""Org growth phase 0a, end to end: the E2 chain replayed against the new mechanisms, without a real LLM and without a network.

The team is real: its deliveries are scheduler runs (``testkit.scheduler_loop.loop_over``) of the testkit fake agent with ``FAKE_MODE=service``
(the lead sends each request to the writer, then to the reviewer, and reports it with lessons). The calls under test (root's ``request``,
``feedback`` and ``define_service``; the lead's ``revise_playbook``, ``hire`` and ``write``) go through the in-process MCP servers. Every test builds
its own organization in its own ``tmp_path`` and replays only what it needs, so each block also runs alone (``-k test_6``).
"""

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field

import pytest
import testkit
from testkit.e2e_world import agent_health, build_server
from testkit.scheduler_loop import loop_over
from testkit.services_world import playbook_meta

from hirearchy.core import ROOT, Org

SERVICE = "meeting-memo"
CRITERIA = [
    "A markdown file with one section per meeting",
    "At most 400 words",
    "Every decision has an owner",
    "Every action item names who does it",
    "One row for every commitment, including informal ones",
    "A date is never invented",
]
PLAYBOOK_V1 = "## Steps\n1. writer: read the notes and write the memo.\n2. reviewer: check every criterion and report PASS or FAIL.\n"
FRIDAY = "Sam's 'before Friday' has a date: Oct 9."
LEE = "Lee's 'next week' has a date too."
A_MEMO = {"notes_file": "meeting-2024-10-02.txt"}


def call(server, tool, **args):
    result = asyncio.run(server.call_tool(tool, args))
    blocks = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(b, "text", "") for b in blocks)


def fails(server, tool, **args) -> str:
    with pytest.raises(Exception) as info:
        call(server, tool, **args)
    return str(info.value)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))


# ------------------------------------------------------------------------------------------------------------ the world
@dataclass
class World:
    org: Org
    root: object  # root's MCP server
    lead: object  # the lead's MCP server
    ids: dict[str, str] = field(default_factory=dict)  # A1, A2, N1, A3, B1, ...
    prompts: list[tuple[str, str]] = field(default_factory=list)  # (agent, the prompt the scheduler built for the run)


def world(tmp_path) -> World:
    org = Org.init(tmp_path / "org", "Meeting memos")
    org.hire(ROOT, "lead", "Lead", "Lead the memo team: send each request to the writer, then to the reviewer.", can_hire=True, max_children=3)
    w = World(org, build_server(org, ROOT), build_server(org, "lead"))
    call(w.lead, "hire", name="writer", role="Writer", charter="Write the memo from the notes.", max_children=9)  # 9 is asked: see test_1
    call(w.lead, "hire", name="reviewer", role="Reviewer", charter="Check the memo against every criterion.")
    org.define_service(
        ROOT, "lead", SERVICE, description="A memo of what a meeting decided and who does what.",
        inputs=[{"name": "notes_file", "description": "the notes of the meeting", "required": True}],
        acceptance=CRITERIA, deliverable={"description": "one markdown file", "format": "markdown", "max_words": 400}, budget=12, playbook=PLAYBOOK_V1)
    w.lead = build_server(org, "lead")  # the tools of an agent that owns a service (revise_playbook) exist from the server it opens after the definition
    return w


def run_team(w: World, limit: float = 90.0) -> None:
    def runner(org, addr, prompt):
        w.prompts.append((addr, prompt))
        env = {**os.environ, "ORG_ROOT": str(org.root), "ORG_AGENT": addr, "FAKE_MODE": "service", "FAKE_REPORTS": "lead/writer,lead/reviewer"}
        return [sys.executable, str(testkit.FAKE_AGENT)], org.dir(addr), env

    loop = loop_over(w.org, runner, echo=lambda _: None)
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


def deliver(w: World, task_id: str) -> None:
    run_team(w)
    assert any(m.type == "result" and m.status == "done" and m.reply_to == task_id for m in w.org.received(ROOT)), task_id


def last_task(w: World) -> str:
    return max(m.id for m in w.org.sent(ROOT) if m.type == "task")


def last_verdict(w: World) -> str:
    return max(m.id for m in w.org.sent(ROOT) if m.feedback)


def request(w: World, **extra) -> str:
    call(w.root, "request", service=SERVICE, inputs=A_MEMO, **extra)
    return last_task(w)


def feedback(w: World, task_id: str, verdict: str, note: str = "", **extra) -> str:
    call(w.root, "feedback", task_id=task_id, verdict=verdict, note=note, **extra)
    return last_verdict(w)


def revise(w: World, content: str, reason: str, evidence: list[str]) -> str:
    return call(w.lead, "revise_playbook", service=SERVICE, content=content, reason=reason, evidence=evidence)


def chain(w: World, through: int) -> dict[str, str]:
    """Replay blocks 2 to ``through`` (the actions only, without their asserts); returns the ids ``A1``, ``A2``, ``N1``, ``A3``, ``B1``."""
    ids = w.ids
    if through >= 2:
        ids["A1"] = request(w)
        deliver(w, ids["A1"])
        ids["A2"] = request(w, revises=ids["A1"], note="use none for informal dates")  # no source: the assistant's own reading
        deliver(w, ids["A2"])
    if through >= 4:
        ids["N1"] = feedback(w, ids["A2"], "reject", FRIDAY, source="human")
        feedback(w, ids["A2"], "reject", "It is about C6; no new rule.", source="human", criterion=["C6"], confirms=ids["N1"])
        ids["A3"] = request(w, revises=ids["A2"], note="Dates only when the notes give one.", source="human")
        deliver(w, ids["A3"])
    if through >= 6:
        feedback(w, ids["A3"], "accept", "This version is right.", source="human")
        ids["B1"] = request(w)
        deliver(w, ids["B1"])
        n = feedback(w, ids["B1"], "reject", LEE, source="human")
        feedback(w, ids["B1"], "reject", "It is about C6 too.", source="human", criterion=["C6"], confirms=n)
        revise(w, PLAYBOOK_V1 + "3. A date is written only when the notes state it.\n", "C6 failed in A1 and B1", ["C6"])
    return ids


def charter_of(w: World, addr: str) -> dict:
    return w.org.charter(addr)[0]


# ------------------------------------------------------------------------------------------------------------ the blocks
def test_1_hires_are_bounded(tmp_path):
    w = world(tmp_path)
    meta = charter_of(w, "lead/writer")  # 9 was asked through the lead's server
    assert meta["can_hire"] is False and meta["max_children"] == 0
    assert charter_of(w, "lead/reviewer")["max_children"] == 0
    assert charter_of(w, "lead")["max_children"] == 3  # root's own hire keeps what it asked


def test_2_the_assistants_rework_is_relayed(tmp_path):
    w = world(tmp_path)
    ids = chain(w, 2)
    a1 = next(m for m in w.org.received("lead") if m.id == ids["A1"])
    a2 = next(m for m in w.org.received("lead") if m.id == ids["A2"])
    assert a1.source is None  # a fresh request is the user's ask: not stamped
    assert a2.source == "relayed" and a2.revises == ids["A1"]
    assert "source: relayed" in a2.to_text()  # the owner sees which


def test_3_the_e2_rule_is_refused_at_zero_run_cost(tmp_path):
    w = world(tmp_path)
    ids = chain(w, 2)
    runs = lambda: len(list((w.org.dir("lead") / "runs").glob("*")))  # noqa: E731
    before = runs()
    rule = PLAYBOOK_V1 + "3. Informal dates are none.\n"
    reason = "Lesson: informal time references must be none"
    refused = fails(w.lead, "revise_playbook", service=SERVICE, content=rule, reason=reason, evidence=[ids["A1"]])
    assert "refused: none of this evidence is the client's own" in refused
    assert f"case {ids['A1']} has no rejection by the client; 1 of its reworks were relayed (the assistant's own reading)" in refused
    assert f'"We would change how we deliver {SERVICE}: {reason}. Is that what you want from now on?' in refused
    assert "C6 is in the contract since v1, not added by an amendment" in fails(w.lead, "revise_playbook", service=SERVICE, content=rule, reason=reason, evidence=["C6"])
    assert "no evidence given" in fails(w.lead, "revise_playbook", service=SERVICE, content=rule, reason=reason, evidence=[])
    assert playbook_meta(w.org, "lead", SERVICE)[0]["version"] == 1
    assert runs() == before  # a refusal is a tool call: no run was spent


def test_4_a_human_reject_names_its_criterion_and_reaches_the_owners_prompt(tmp_path):
    w = world(tmp_path)
    ids = chain(w, 2)
    n1 = ids["N1"] = feedback(w, ids["A2"], "reject", FRIDAY, source="human")
    verdict = next(m for m in w.org.received("lead") if m.id == n1)
    assert verdict.source == "human" and verdict.feedback == "reject"
    feedback(w, ids["A2"], "reject", "It is about C6; no new rule.", source="human", criterion=["C6"], confirms=n1)
    link = max((m for m in w.org.received("lead") if m.reply_to == n1), key=lambda m: m.id)
    assert not link.feedback and link.criterion == "C6" and link.to == "lead" and link.source == "human"
    case = next(c for c in w.org.runtime.case_history.cases("lead", SERVICE) if c.id == ids["A1"])
    assert len(case.verdicts) == 1  # the link is no new verdict
    ids["A3"] = request(w, revises=ids["A2"], note="Dates only when the notes give one.", source="human")
    assert next(m for m in w.org.received("lead") if m.id == ids["A3"]).source == "human"
    deliver(w, ids["A3"])
    lead_prompt = next(p for addr, p in w.prompts if addr == "lead" and ids["A3"] in p)
    assert "# Regression list: meeting-memo (the client's rejections, verbatim)" in lead_prompt
    assert f'- R1, case {ids["A1"]}, verdict {n1}, about C6: "{FRIDAY}"' in lead_prompt
    assert "# Reflect before you start: meeting-memo" in lead_prompt
    assert "The client rejected a delivery: check the delivery against its words" in lead_prompt
    assert all("Regression list" not in p for addr, p in w.prompts if addr in ("lead/writer", "lead/reviewer"))


def test_5_one_case_is_a_question_not_a_rule(tmp_path):
    w = world(tmp_path)
    ids = chain(w, 4)
    refused = fails(w.lead, "revise_playbook", service=SERVICE, content=PLAYBOOK_V1 + "3. No dates.\n", reason="R1 says so", evidence=["R1"])
    assert f"the client rejected this in one case only ({ids['A1']})" in refused
    assert f'In case {ids["A1"]} you said: "{FRIDAY}"' in refused
    assert "a clarification of C6" in refused  # C6 is current
    assert playbook_meta(w.org, "lead", SERVICE)[0]["version"] == 1


def test_6_a_second_independent_human_reject_admits_a_revision(tmp_path):
    w = world(tmp_path)
    ids = chain(w, 5)
    feedback(w, ids["A3"], "accept", "This version is right.", source="human")
    ids["B1"] = request(w)
    deliver(w, ids["B1"])
    n = feedback(w, ids["B1"], "reject", LEE, source="human")
    feedback(w, ids["B1"], "reject", "It is about C6 too.", source="human", criterion=["C6"], confirms=n)
    v2 = PLAYBOOK_V1 + "3. A date is written only when the notes state it.\n"
    assert "now v2" in revise(w, v2, "C6 failed in A1 and B1", ["C6"])
    meta, body = playbook_meta(w.org, "lead", SERVICE)
    assert meta["version"] == 2 and meta["admitted"] == "b" and meta["evidence"] == ["C6"] and body.strip() == v2.strip()
    assert any(f"admitted: C6 failed in 2 cases the client rejected: {ids['A1']}, {ids['B1']}" in m.body for m in w.org.received(ROOT))  # root's quiet note


def test_7_an_amendment_admits_a_revision_only_once_the_client_confirmed_it(tmp_path):
    w = world(tmp_path)
    ids = chain(w, 4)
    feedback(w, ids["A3"], "accept", "This version is right.", source="human")
    ids["B1"] = request(w)
    deliver(w, ids["B1"])
    n2 = feedback(w, ids["B1"], "reject", LEE, source="human")  # the user's rejection; no criterion on it
    added = "'before <weekday>' is that weekday's date"
    reply = call(w.root, "define_service", owner="lead", name=SERVICE, add_acceptance=[added])
    assert f"C7: {added}" in reply
    note = next(m.body for m in w.org.received("lead") if "Acceptance criteria now:" in m.body)
    assert all(f"C{k}: " in note for k in range(1, 8))
    v2 = PLAYBOOK_V1 + "3. 'before <weekday>' is that weekday's date.\n"
    refused = fails(w.lead, "revise_playbook", service=SERVICE, content=v2, reason="C7 was added by the client", evidence=["C7"])
    assert "C7 was added to the contract by an amendment (v2), but the client's yes to it is not recorded (not confirmed)" in refused
    assert playbook_meta(w.org, "lead", SERVICE)[0]["version"] == 1
    feedback(w, ids["B1"], "reject", "Yes, add it.", source="human", criterion=["C7"], confirms=n2)  # the user's yes, recorded as a link
    assert "now v2" in revise(w, v2, "C7 was added by the client", ["C7"])
    meta, _ = playbook_meta(w.org, "lead", SERVICE)
    assert meta["version"] == 2 and meta["admitted"] == "c" and meta["evidence"] == ["C7"]


def test_8_health_counts_the_escape_and_not_the_relayed_rework(tmp_path):
    w = world(tmp_path)
    chain(w, 7)
    reviewer = agent_health(w.org, "lead/reviewer")
    assert (reviewer.judged, reviewer.escapes, reviewer.rechecks) == (2, 1, 0)  # judged: A3 and B1; A2's rejection is not counted
    assert "low_quality" not in reviewer.flags  # 2 judged are fewer than min_judged_for_quality
    lead = agent_health(w.org, "lead")
    assert (lead.judged, lead.escapes) == (2, 1)


def test_9_a_non_root_lead_cannot_grant_hiring_rights(tmp_path):
    w = world(tmp_path)
    refused = fails(w.lead, "hire", name="sub", role="Sub-lead", charter="Lead a sub-team.", can_hire=True)
    assert "you cannot grant `can_hire: true`: only the user (root) or an approved plan gives an agent the right to hire" in refused
    assert "lead/sub" not in w.org.agents()
    w.org.hire("lead", "sub", "Sub-lead", "Lead a sub-team.", can_hire=True, max_children=1, approved=True)  # the user's own hire, as the CLI does
    meta = charter_of(w, "lead/sub")
    assert meta["can_hire"] is True and meta["max_children"] == 1


def test_10_a_charter_rewrite_cannot_grant_hiring_or_raise_a_limit(tmp_path):
    w = world(tmp_path)
    w.org.hire("lead", "sub", "Sub-lead", "Lead a sub-team.", can_hire=True, max_children=1, approved=True)
    grant = fails(w.lead, "write", path="lead/writer/AGENT.md", content="---\nrole: Writer\ncan_hire: true\n---\nWrite.")
    assert "you cannot grant `can_hire: true`" in grant
    assert charter_of(w, "lead/writer")["can_hire"] is False
    raised = fails(w.lead, "write", path="lead/sub/AGENT.md", content="---\nrole: Sub-lead\nmax_children: 5\n---\nLead.")
    assert "you cannot give a report max_children 5: your own limit is 3" in raised
    call(w.lead, "write", path="lead/sub/AGENT.md", content="---\nrole: Sub-lead\nmax_children: 3\n---\nLead.")
    assert charter_of(w, "lead/sub")["max_children"] == 3
    call(w.lead, "write", path="lead/sub/AGENT.md", content="---\nrole: Sub-lead\n---\nLead the sub-team, and tell me what it does.")  # body only
    meta, body = w.org.charter("lead/sub")
    assert meta["can_hire"] is True and meta["max_children"] == 3 and "tell me what it does" in body
