# mypy: ignore-errors
"""Phase 2a, end to end: the acceptance guards of design 15.3 (GREEN when written, like Phase 1's FEAT-010; PC-11).

No scheduler, no LLM, no network: an organization is built through the product's own calls (hire, define a service, delegate, report, feedback with the user's verdict),
and root's MCP server is driven the way the assistant drives it. A guard that goes red is a bug of the product: it is fixed test-first, never edited to match.
"""

import json
import re
import time

import pytest
from testkit.e2e_world import build_server
from testkit.services_world import call

from hirearchy.core import ROOT, Org
from hirearchy.retro import brief_json


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))


def plan_id_in(text):
    return re.search(r"^plan_id: (\w+)$", text, re.M).group(1)


def item_blueprint(brief_text, n):
    """The blueprint of item ``n`` as the brief's Details give it (the JSON under ``On yes:``)."""
    item = re.split(r"\n(?=\d+\. )", brief_text.split("\nItems:\n")[1])[n - 1]
    body = item.split("On yes:")[1].split("\n   Revert:")[0].split("\n", 1)[1]
    return json.loads("\n".join(line[3:] for line in body.splitlines()))


def make_the_org(tmp_path):
    """An organization with a lead at capacity whose service has no reviewer, and an operator that is asked for one chore again and again."""
    org = Org.init(tmp_path / "org", "Run the memos and the chores.", {"poll_seconds": 0.05})
    workspace = tmp_path / "ws"
    workspace.mkdir()
    org.hire(ROOT, "ceo", "Lead", "Directs the memos.", tools=["read", "write"], workspace=str(workspace), can_hire=True, max_children=1)
    org.hire("ceo", "writer", "Writer", "Writes the memos.", tools=["read", "write"], workspace=str(workspace))
    org.hire(ROOT, "ops", "Operator", "Does the chores.", tools=["read", "write"], workspace=str(workspace))
    org.define_service(
        ROOT, "ceo", "memos", description="A memo.", inputs=[{"name": "topic", "description": "what it is about", "required": True}],
        acceptance=["A Summary line first", "Every claim names its source"], deliverable={"description": "one markdown file"}, budget=12,
    )
    return org


def deliver(org, owner, task):
    org.begin_run(owner)
    org.start_run_log(owner)
    org.report(owner, task.id, "done", "Delivered.", lessons="Worked.")
    org.end_run(owner, ok=True)


def the_user_judged_three_chores_and_rejected_three_memos_on_one_criterion(org):
    for day in (2, 9, 16):  # three one-off tasks of one shape, each accepted by the user
        task = org.delegate(ROOT, "ops", f"Action list for 2026-11-{day:02d}", "Turn the notes into a list.", "Every action has an owner", budget=3)
        org.report("ops", task.id, "done", "Done.")
        org.feedback(ROOT, task.id, "accept", source="human")
    for topic in ("one", "two", "three"):  # three cases of the service the user rejected on C2 (no check of the team signs them), each answered by the user's link
        task = org.request(ROOT, "memos", {"topic": topic})
        deliver(org, "ceo", task)
        no = org.feedback(ROOT, task.id, "reject", "Missing the sources.", source="human")
        org.feedback(ROOT, task.id, "reject", "Yes, it is about that.", source="human", criterion=["C2"], confirms=no.id)


def approve(server, blueprint):
    """The assistant's two calls for one item: propose (the plan the user sees), then apply with that plan's id after the user's approval."""
    proposal = call(server, "propose_org", blueprint=json.dumps(blueprint), extend="current")
    assert "PLAN FOR YOU (a change to your organization)" in proposal and "Cannot apply yet" not in proposal
    return call(server, "apply_org", blueprint=json.dumps(blueprint), extend="current", approved=True, plan_id=plan_id_in(proposal))


def test_the_exit_criterion_service_and_checker_through_the_brief_with_no_unprompted_charter_edit(tmp_path):
    """Design 15.3 item 1 (X3): the user's verdicts make retro() hold a `service` and a `checker-add` item; their calls are made one at a time (propose, apply with the
    plan_id); the checker has `kind: verifier` and `approved_in`; the next brief shows both `taken`, labels both `from your change {id}, item B1.k`, and counts no
    unprompted charter edit."""
    org = make_the_org(tmp_path)
    the_user_judged_three_chores_and_rejected_three_memos_on_one_criterion(org)
    server = build_server(org, ROOT)

    first = call(server, "retro")
    time.sleep(1.1)  # (an agent's `created` and a commit's time are whole seconds: what the plans change comes a second after the brief, as it does when the user takes time to approve)
    assert first.startswith("RETRO BRIEF B1 (since the organization started") and "RETRO BRIEF END" in first
    assert [i.kind for i in org.runtime.retro_records.last().items] == ["service", "checker-add"]
    assert "1. Make the repeated task" in first and "2. Add a checker to memos for C2" in first
    assert "Unprompted charter edits: 0" in first

    service = item_blueprint(first, 1)  # item 1: the service, with the two answers the user gives (what one request produces, and where it goes)
    entry = service["extend"]["add_services"][0]
    assert entry["owner"] == "ops" and entry["deliverable"]["description"].startswith("<ASK THE USER")
    entry["deliverable"] = {"description": "one markdown list", "format": "markdown", "path": str(tmp_path / "out")}
    (tmp_path / "out").mkdir()
    service_applied = approve(server, service)
    assert "defined 1 service(s): action-list-for of ops" in service_applied
    service_change = re.search(r"applied the change (\w+) to ", service_applied).group(1)

    checker = item_blueprint(first, 2)  # item 2: the checker, added to the lead that was at capacity (its limit goes up in the same plan)
    assert checker["extend"]["limits"] == [{"agent": "ceo", "max_children": 2}] and checker["extend"]["add_agents"][0]["parent"] == "ceo"
    checker_applied = approve(server, checker)
    assert "added 1 agent(s): ceo/c2-checker" in checker_applied and "changed limits: ceo" in checker_applied
    checker_change = re.search(r"applied the change (\w+) to ", checker_applied).group(1)

    meta, body = org.charter("ceo/c2-checker")
    assert (meta["kind"], meta["approved_in"], meta["hired_by"]) == ("verifier", f"change {checker_change}", "ceo")
    assert "Check C2 of memos on every request" in org.charter("ceo")[1]  # the line the plan showed, in the lead's added section
    assert org.runtime.service_store.versions("ops", "action-list-for", "SERVICE")[0][1]["approved_in"] == f"change {service_change}"

    task = org.request(ROOT, "memos", {"topic": "four"})  # the user's next verdict: the next brief is recorded
    deliver(org, "ceo", task)
    org.feedback(ROOT, task.id, "accept", source="human")
    second = call(server, "retro")
    assert second.startswith("RETRO BRIEF B2 (since the last brief")
    assert f"- agent ceo/c2-checker added (" in second and f"from your change {checker_change}, item B1.2" in second
    assert f"- service ops/action-list-for added (" in second and f"from your change {service_change}, item B1.1" in second
    assert "- B1.1 service: taken (ops/action-list-for defined)" in second and "- B1.2 checker-add: taken (a checker joined ceo's team)" in second
    assert "outside a plan" not in second and "outside the tools" not in second and "Unprompted charter edits: 0" in second
    counts = brief_json(org.runtime.retro_briefs.brief())["sections"]["d8"]["counts"]
    assert counts["unprompted_charter_edits"] == 0 and counts["changes"] >= 3
