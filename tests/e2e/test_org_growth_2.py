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
from testkit.services_world import call, fails

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


def the_user_judged_three_chores_and_rejected_three_memos_on_one_criterion(org, chores_to="ops"):
    for day in (2, 9, 16):  # three one-off tasks of one shape, each accepted by the user
        task = org.delegate(ROOT, chores_to, f"Action list for 2026-11-{day:02d}", "Turn the notes into a list.", "Every action has an owner", budget=3)
        org.report(chores_to, task.id, "done", "Done.")
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


@pytest.mark.parametrize("first", ["service", "checker"])
def test_the_exit_study_on_one_lead_both_items_apply_as_the_brief_gives_them_in_either_order(tmp_path, first):
    """Review F4 of build 2a: in the study's script root's one-off tasks and the failing service belong to the same lead. The brief's `service` and `checker-add` calls, made as
    given (the user's two answers aside), both validate and apply whichever is taken first: the checker's call budgets every service of the lead for the team it leaves, and
    the service's budget already covers that team."""
    org = make_the_org(tmp_path)
    the_user_judged_three_chores_and_rejected_three_memos_on_one_criterion(org, chores_to="ceo")
    server = build_server(org, ROOT)
    brief = call(server, "retro")
    assert [i.kind for i in org.runtime.retro_records.last().items] == ["service", "checker-add"]
    service, checker = item_blueprint(brief, 1), item_blueprint(brief, 2)
    entry = service["extend"]["add_services"][0]
    assert entry["owner"] == "ceo"
    entry["deliverable"] = {"description": "one markdown list", "format": "markdown", "path": str(tmp_path / "out")}
    (tmp_path / "out").mkdir()
    for blueprint in ([service, checker] if first == "service" else [checker, service]):
        assert "applied the change" in approve(server, blueprint)
    assert sorted(org.runtime.service_catalog.service_names("ceo")) == ["action-list-for", "memos"]
    assert "ceo/c2-checker" in org.runtime.agents.agents()


def test_a_service_the_user_renamed_in_the_applied_extension_reads_taken_by_its_criteria(tmp_path):
    """Review F3 of build 2a (design 4.5, "effect of an item"): the user renames the pre-filled service; it was still made by the brief's item, so the next brief shows the
    item taken, not lapsed (P2-X1)."""
    org = make_the_org(tmp_path)
    the_user_judged_three_chores_and_rejected_three_memos_on_one_criterion(org)
    server = build_server(org, ROOT)
    first = call(server, "retro")
    time.sleep(1.1)
    service = item_blueprint(first, 1)
    entry = service["extend"]["add_services"][0]
    entry["name"] = "chore-list"
    entry["deliverable"] = {"description": "one markdown list", "format": "markdown", "path": str(tmp_path / "out")}
    (tmp_path / "out").mkdir()
    assert "defined 1 service(s): chore-list of ops" in approve(server, service)
    task = org.request(ROOT, "memos", {"topic": "four"})
    deliver(org, "ceo", task)
    org.feedback(ROOT, task.id, "accept", source="human")
    second = call(server, "retro")
    assert "- B1.1 service: taken (ops/chore-list defined)" in second and "B1.1 service: lapsed" not in second


def a_judged_memo(org, topic, verdict, link=None):
    """A new request of memos, delivered, and the user's verdict on it (a rejection is answered by the user's link to ``link``)."""
    task = org.request(ROOT, "memos", {"topic": topic})
    deliver(org, "ceo", task)
    if verdict == "accept":
        org.feedback(ROOT, task.id, "accept", source="human")
        return task
    no = org.feedback(ROOT, task.id, "reject", "Missing the sources again.", source="human")
    org.feedback(ROOT, task.id, "reject", "Yes, it is about that.", source="human", criterion=[link], confirms=no.id)
    return task


def the_checker_taken(tmp_path):
    org = make_the_org(tmp_path)
    the_user_judged_three_chores_and_rejected_three_memos_on_one_criterion(org)
    server = build_server(org, ROOT)
    first = call(server, "retro")
    time.sleep(1.1)
    approve(server, item_blueprint(first, 2))  # item 2: the checker (the service item is left)
    return org, server


def test_a_taken_checker_is_weighed_by_the_cases_that_follow_it_until_it_holds(tmp_path):
    """Review F1 of build 2a (design 4.4, rows 3-4): the next brief says whether a taken `checker-add` held: INCONCLUSIVE below the window, then `not recurred`."""
    org, server = the_checker_taken(tmp_path)
    a_judged_memo(org, "four", "accept")
    second = call(server, "retro")
    line = r"- agent ceo/c2-checker added \([\d-]+\), item B1\.2: "
    assert re.search(line + r"INCONCLUSIVE \(1 of 3 exercised cases\)", second), second
    a_judged_memo(org, "five", "accept")
    a_judged_memo(org, "six", "accept")
    third = call(server, "retro")
    assert re.search(line + r"not recurred in 3 cases where it was exercised", third), third


def test_a_taken_checker_whose_criterion_failed_again_reads_recurred_in_that_case(tmp_path):
    org, server = the_checker_taken(tmp_path)
    a_judged_memo(org, "four", "reject", link="C2")
    second = call(server, "retro")
    case = org.runtime.case_records.records("memos")[0].cases[-1].id
    assert re.search(r"- agent ceo/c2-checker added \([\d-]+\), item B1\.2: recurred in case " + re.escape(case), second), second
    assert "no target recorded" not in second.split("Did past changes hold")[1].split("Changes to your organization")[0]


# ------------------------------------------------------------------------------------------------------------ item 2: root's refusals and the extension paths

WHY = "the user said yes to this change"


def change(server, extend, **needs):
    """One extension, proposed and then applied after the user's approval (what the assistant does); returns the reply of apply_org."""
    blueprint = {"reason": WHY, "extend": extend}
    if needs:
        blueprint["needs"] = needs
    proposal = call(server, "propose_org", blueprint=json.dumps(blueprint), extend="current")
    assert "PLAN FOR YOU (a change to your organization)" in proposal and "Cannot apply yet" not in proposal, proposal
    return call(server, "apply_org", blueprint=json.dumps(blueprint), extend="current", approved=True, plan_id=plan_id_in(proposal))


def test_root_structural_calls_are_refused_and_each_extension_path_applies(tmp_path):
    """Design 15.3 item 2: over root's MCP a hire, a retire, a first definition of a service, a write of a charter and a write of ORG.md's max_depth are refused, each
    naming the extension; and each kind of extension (an agent, a service, a charter line and its removal, limits, a budget, a service retired, an agent retired)
    is proposed and applied the way the refusals say."""
    org = make_the_org(tmp_path)
    server = build_server(org, ROOT)
    before = {path.name: path.read_bytes() for path in (org.root / "ceo" / "AGENT.md", org.root / "ORG.md")}

    for tool, arguments, refused in (
        ("hire", dict(name="newbie", role="Helper", charter="Helps."), "refused: a new agent changes the organization, so the user approves it in a plan"),
        ("retire", dict(name="ceo/writer", reason="done"), "refused: retiring ceo/writer changes the organization, so the user approves it in a plan"),
        ("define_service", dict(owner="ceo", name="fresh", description="d", acceptance=["a"], budget=3), "refused: ceo offers no service `fresh`, and a new service changes the organization"),
        ("write", dict(path="ceo/AGENT.md", content="---\nrole: Chief\n---\nNew body.\n"), "refused: a charter changes through a plan the user approves"),
        ("write", dict(path="ORG.md", content=before["ORG.md"].decode().replace("max_depth: 4", "max_depth: 6")), "refused: max_depth bounds the organization's structure"),
    ):
        text = fails(server, tool, **arguments)
        assert refused in text and 'extend="current"' in text, (tool, text)
    assert {path.name: path.read_bytes() for path in (org.root / "ceo" / "AGENT.md", org.root / "ORG.md")} == before
    assert org.runtime.agents.agents() == ["ceo", "ceo/writer", "ops"] and org.runtime.service_catalog.service_names("ceo") == ["memos"]

    added = change(server, {"add_agents": [{"parent": "ceo", "name": "editor", "template": "writer", "tools": ["read", "write"]}], "limits": [{"agent": "ceo", "max_children": 2}]})
    assert "added 1 agent(s): ceo/editor" in added and org.charter("ceo/editor")[0]["approved_in"].startswith("change ") and org.charter("ceo")[0]["max_children"] == 2

    service = change(
        server,
        {"add_services": [{
            "owner": "ops", "name": "notes", "description": "Notes of a meeting.", "inputs": [{"name": "meeting", "description": "which meeting", "required": True}],
            "acceptance": [{"text": "Every decision is listed", "from": "list every decision", "asked": "What must the notes hold?"}],
            "deliverable": {"description": "one markdown file", "format": "markdown"}, "budget": 6,
        }]},
        elicitation="list every decision",
    )
    assert "defined 1 service(s): notes of ops" in service and org.runtime.service_catalog.service_names("ops") == ["notes"]

    line = "Check the sources of every memo."
    assert "charter lines: 1 added, 0 taken out" in change(server, {"add_charter_lines": [{"agent": "ceo", "line": line}]})
    assert line in org.charter("ceo")[1]
    assert "charter lines: 0 added, 1 taken out" in change(server, {"remove_charter_lines": [{"agent": "ceo", "line": line}]})
    assert line not in org.charter("ceo")[1]

    assert "changed limits: ceo" in change(server, {"limits": [{"agent": "ceo", "max_children": 3}]})
    assert org.charter("ceo")[0]["max_children"] == 3
    assert "budget of memos of ceo: 12 -> 15 runs per request" in change(server, {"budgets": [{"owner": "ceo", "service": "memos", "budget": 15}]})
    assert "max_depth" in change(server, {"limits": [{"org": "max_depth", "value": 5}]}) and "max_depth: 5" in (org.root / "ORG.md").read_text()

    assert "retired: service notes of ops" in change(server, {"retire_services": [{"owner": "ops", "service": "notes", "reason": "no longer asked for"}]})
    assert org.runtime.service_catalog.service_names("ops") == []
    assert "retired: ceo/editor" in change(server, {"retire": [{"agent": "ceo/editor", "reason": "not needed"}]})
    assert org.runtime.agents.agents() == ["ceo", "ceo/writer", "ops"]


def test_charter_plan_charter_added_and_verifier_kept_through_mcp(tmp_path):
    """Design 15.3 item 2 (the agent refusals of 6.6): the lead of a team cannot, over MCP, rewrite a report's plan keys (CHARTER-PLAN), drop or reword a line the user
    approved under "## Added by your changes" (CHARTER-ADDED) or retire the report that checks its team (VERIFIER-KEPT); a rewrite of the report's body passes."""
    org = make_the_org(tmp_path)
    root_server = build_server(org, ROOT)
    line = "Name the source of every claim."
    change(root_server, {
        "add_agents": [{"parent": "ceo", "name": "checker", "template": "reviewer", "tools": ["read"]}], "limits": [{"agent": "ceo", "max_children": 3}],
        "add_charter_lines": [{"agent": "ceo/writer", "line": line}],
    })
    assert org.charter("ceo/checker")[0]["kind"] == "verifier"
    lead = build_server(org, "ceo")  # (the lead holds the built-in `write`, so the organization's tool is called `org_write`)

    path = org.root / "ceo" / "checker" / "AGENT.md"
    text = path.read_text()
    refusal = fails(lead, "org_write", path="ceo/checker/AGENT.md", content=text.replace("kind: verifier", "kind: worker", 1))
    assert "refused: kind of ceo/checker is the plan's, which the user approved; a change goes through the user (propose_org(..., extend=\"current\")" in refusal
    assert path.read_text() == text

    writer = org.root / "ceo" / "writer" / "AGENT.md"
    held = writer.read_text()
    assert f"## Added by your changes" in held and line in held
    without = "\n".join(entry for entry in held.splitlines() if line not in entry) + "\n"
    added_refusal = fails(lead, "org_write", path="ceo/writer/AGENT.md", content=without)
    assert 'refused: the lines under "## Added by your changes" are the user\'s (approved in a plan); keep them exactly as they are' in added_refusal
    assert writer.read_text() == held
    assert call(lead, "org_write", path="ceo/writer/AGENT.md", content=held + "\n## Notes\nI draft in short paragraphs.\n").startswith("wrote ceo/writer/AGENT.md (organization file)")
    assert line in writer.read_text() and "I draft in short paragraphs." in writer.read_text()

    kept = fails(lead, "retire", name="checker", reason="restructure")
    assert kept.endswith("refused: ceo/checker checks your team's work (Independent Reviewer); removing a check is the user's decision (the retro brief shows them the team). Nothing was retired.")
    assert org.runtime.agents.exists("ceo/checker")
    assert call(lead, "retire", name="writer", reason="restructure").startswith("retired ceo/writer")  # a report that is no check is the lead's to retire


# ------------------------------------------------------------------------------------------------------------ item 3: F-P1-3, a criterion and the words it rests on

USER_WORDS = "Use the words from the notes."  # P1's I1, turn 2: the user's own words
ASKED = "Owners: initials or full names?"
WIDENED = "decisions and actions use the notes' own words"  # the criterion the assistant wrote from them: it adds words of its own


def notes_service(acceptance):
    return {"owner": "ops", "name": "notes", "description": "Notes of a meeting.", "inputs": [{"name": "meeting", "description": "which meeting", "required": True}],
            "acceptance": acceptance, "deliverable": {"description": "one markdown file", "format": "markdown"}, "budget": 6}


def proposal_of(server, extend, **needs):
    blueprint = {"reason": WHY, "extend": extend}
    if needs:
        blueprint["needs"] = needs
    return call(server, "propose_org", blueprint=json.dumps(blueprint), extend="current")


def test_the_widened_criterion_shows_its_added_words_and_is_asked_once_after_three_accepts(tmp_path, capsys):
    """Design 15.3 item 3 (F-P1-3): P1's I1 turn-2 words are the plan's `needs.elicitation`, and the widened criterion cites them: PLAN FOR YOU shows `words I added: decisions,
    and, actions, own`. A quote that is not in the words is refused; so are string criteria, and a plan without `needs.elicitation`, over MCP; at the terminal the same
    plan shows `my wording: your words for it were not recorded`. After 3 accepts the next brief carries the `clarify` item once."""
    org = make_the_org(tmp_path)
    server = build_server(org, ROOT)
    cited = [{"text": WIDENED, "from": USER_WORDS, "asked": ASKED}]

    plan = proposal_of(server, {"add_services": [notes_service(cited)]}, elicitation=f"{USER_WORDS} Initials are fine.")
    assert "Cannot apply yet" not in plan and "words I added: decisions, and, actions, own" in plan
    assert f'from your words "{USER_WORDS}" (my question: "{ASKED}")' in plan and "my wording" not in plan

    elsewhere = [{"text": WIDENED, "from": "Always use their full names.", "asked": ASKED}]  # a quote that is not in the user's words
    refused = proposal_of(server, {"add_services": [notes_service(elsewhere)]}, elicitation=USER_WORDS)
    assert "Cannot apply yet" in refused and 'quotes words that are not in needs.elicitation: "Always use their full names."' in refused
    strings = proposal_of(server, {"add_services": [notes_service([WIDENED])]}, elicitation=USER_WORDS)
    assert "Cannot apply yet" in strings and "criterion 1 does not say where it comes from" in strings
    unrecorded = proposal_of(server, {"add_services": [notes_service(cited)]})
    assert "Cannot apply yet" in unrecorded and "this plan records none of the user's words" in unrecorded
    assert org.runtime.service_catalog.service_names("ops") == []  # none of the refusals wrote anything

    from testkit.services_world import main  # at the terminal the user's own seat shows a string criterion with the line that says its source was not recorded
    plan_file = tmp_path / "terminal.yaml"
    plan_file.write_text(json.dumps({"reason": WHY, "extend": {"add_services": [notes_service([WIDENED])]}}))
    capsys.readouterr()
    main(["--root", str(org.root), "plan", str(plan_file)])
    assert "my wording: your words for it were not recorded" in capsys.readouterr().out

    applied = call(server, "apply_org", blueprint=json.dumps({"reason": WHY, "needs": {"elicitation": f"{USER_WORDS} Initials are fine."}, "extend": {"add_services": [notes_service(cited)]}}),
                   extend="current", approved=True, plan_id=plan_id_in(plan))
    assert "defined 1 service(s): notes of ops" in applied

    for meeting in ("monday", "tuesday", "wednesday"):  # three accepts the user gave to deliveries under the widened criterion
        task = org.request(ROOT, "notes", {"meeting": meeting})
        deliver(org, "ops", task)
        org.feedback(ROOT, task.id, "accept", source="human")
    first = call(server, "retro")
    clarify = [i for i in org.runtime.retro_records.last().items if i.kind == "clarify"]
    assert len(clarify) == 1 and clarify[0].key.startswith("clarify|notes|")
    assert "decisions, and, actions, own" in first and USER_WORDS in first

    time.sleep(1.1)
    task = org.request(ROOT, "notes", {"meeting": "thursday"})
    deliver(org, "ops", task)
    org.feedback(ROOT, task.id, "accept", source="human")
    second = call(server, "retro")
    assert second.startswith("RETRO BRIEF B2") and not [i for i in org.runtime.retro_records.last().items if i.kind == "clarify"]  # asked once
