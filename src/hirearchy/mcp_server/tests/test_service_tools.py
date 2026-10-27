# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import asyncio

import testkit.reach.yaml as yaml
from testkit.reach.hirearchy.core import ROOT
from testkit.mcp_server_world import build_server, services
from testkit.services_world import BRIEF, ENG, call, confirmed_amendment, define, deliver, fails, request, svc, work

from hirearchy.services import ServiceCommands

WEEKDAY = "weekly-brief"


def test_the_feedback_tool_text_no_longer_says_a_later_one_replaces_the_earlier(svc):
    doc = ServiceCommands.feedback.__doc__
    assert "replaces" not in doc and "stays in the case" in doc
    tools = {t.name: t for t in __import__("asyncio").run(build_server(svc, ROOT).list_tools())}
    assert "replaces this one" not in tools["feedback"].description
    assert "every verdict stays" in tools["feedback"].description


def described(org, addr):
    return {t.name: t for t in asyncio.run(build_server(org, addr).list_tools())}


def test_root_feedback_docstring_names_the_users_own_words_verbatim(svc):
    text = " ".join(described(svc, ROOT)["feedback"].description.split())
    assert "optional for accept: the user's own words, verbatim" in text
    assert "the user's own judgement" in text and "your own judgement" not in text
    assert "every verdict stays" in text
    assert 'source: "human" only when the verdict is the user\'s own judgement and note holds their words; "relayed" (the default)' in text
    assert 'criterion (reject only): what the rejection is about, as ids: "C<k>" (a contract criterion, see `services`)' in text
    # DR-46, replaced on purpose: `confirms` is now the answer that changes no criterion; a yes that changes the contract is define_service(answers=...)
    assert 'confirms: the user\'s answer that changes no criterion ("no", "a one-off", "about C<k> as it is"): call again with the same task_id, verdict "reject"' in text
    assert "after it, that rejection takes no confirms" in text
    assert "on the rejection itself it is shown as not confirmed, whatever the source" in text
    assert "only this link counts as the client's" not in text and "confirms: the user's yes." not in text
    assert "it records the link, not a new verdict" in text and "it never waives an acceptance criterion" in text


def test_root_define_service_has_answers_about_words_and_agents_do_not(svc):
    root, agent = described(svc, ROOT)["define_service"], described(svc, "ceo")["define_service"]
    props = root.inputSchema["properties"]
    assert set(props) - set(agent.inputSchema["properties"]) == {"answers", "about", "words"}
    for name in ("answers", "about", "words"):
        assert props[name]["anyOf"] == [{"type": "string"}, {"type": "null"}] and props[name]["default"] is None
    assert root.inputSchema["required"] == ["owner", "name"] == agent.inputSchema["required"]
    assert set(agent.inputSchema["properties"]) == {
        "owner", "name", "description", "acceptance", "deliverable", "budget", "inputs", "playbook", "locked", "notes", "add_acceptance", "remove_acceptance",
    }
    text = " ".join(agent.description.split())
    assert "answers" not in text and "CHANGING THE CRITERIA" not in text  # the agents' tool and docstring are what they were


def test_root_define_service_docstring_names_changing_the_criteria(svc):
    text = " ".join(described(svc, ROOT)["define_service"].description.split())
    assert "An amendment that changes nothing is refused. CHANGING THE CRITERIA (you, root): only as the user's answer after a rejection: " in text
    assert "answers=<the rejection's message id>, about=<the C or R id your one question named>, words=<their answer, verbatim> (it records their yes as the link itself); " in text
    assert "or, for a change the user asks for on their own outside any rejection, words=<their request, verbatim> alone (never admits a playbook revision). " in text
    assert text.endswith("Every delivered request of the service needs its verdict first.")


def test_root_feedback_docstring_names_one_off_tasks(svc):
    text = " ".join(described(svc, ROOT)["feedback"].description.split())
    assert text.startswith(
        'Record the user\'s verdict on a delivered task: one of your service requests (or a rework) or one of your one-off tasks: verdict "accept" or "reject". '
    )
    assert 'it is shown to the owner but weighs nothing when it revises its playbook. A one-off task takes no criterion or confirms (it has no contract). ' \
           'criterion (reject only): what the rejection is about' in text
    assert " ".join(described(svc, "ceo")["feedback"].description.split()).startswith("Tell the owner of a service whether a delivered request was good")


def test_root_feedback_docstring_asks_for_the_reading(svc):
    text = " ".join(described(svc, ROOT)["feedback"].description.split())
    assert "on the rejection itself it is shown as not confirmed, whatever the source. Pass your reading there (one id: what you read the rejection as), and the reply gives the exact question naming it. " in text
    assert 'A yes that changes the contract is define_service(..., answers=<the rejection\'s message id>, about=<the id>, words=<their answer>), which records the link itself; after it, that rejection takes no confirms.' in text


def test_root_feedback_reply_names_message_and_source(svc):
    server = build_server(svc, ROOT)
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    reply = call(server, "feedback", task_id=first.id, verdict="reject", note="Too long.", source="human", criterion=["c1"])
    no = [m for m in svc.sent(ROOT) if m.feedback][-1]
    assert reply.startswith(
        f"feedback reject recorded on {first.id} for ceo (message {no.id}, source human, about C1 (not confirmed)); it does not wake ceo\n"
        "The criterion on the rejection itself (C1) is recorded as not confirmed. This rejection is R1. Next: ask the user exactly ONE yes/no "
        'question, in these words: "About C1: add "<the rule, in their words>" as a lasting rule? Yes or no." '
    )
    assert "Next, before define_service: " not in reply and "Only after their yes call define_service" not in reply
    assert f'task_id="{first.id}", verdict="reject", confirms="{no.id}"' in reply  # the step names the call that records the user's no
    assert (no.source, no.criterion) == ("human", "C1")
    call(server, "feedback", task_id=first.id, verdict="reject", note="No, as it is.", source="human", criterion=["none"], confirms=no.id)  # the user's answer
    second = request(svc, "chips")
    deliver(svc, "ceo", second)
    reply = call(server, "feedback", task_id=second.id, verdict="accept")
    yes = [m for m in svc.sent(ROOT) if m.feedback][-1]
    assert reply == f"feedback accept recorded on {second.id} for ceo (message {yes.id}, source relayed); it does not wake ceo"
    assert yes.source == "relayed"
    reply = call(server, "feedback", task_id=first.id, verdict="reject", note="Yes, always.", source="human", criterion=["C1"], confirms=no.id)
    link = [m for m in svc.sent(ROOT) if m.criterion and not m.feedback][-1]
    assert reply == f"recorded: rejection {no.id} is about C1 (source human; message {link.id}); it does not wake ceo"
    assert (link.reply_to, link.source) == (no.id, "human")


def test_root_one_off_feedback_reply_is_the_receipt_then_the_step(svc):
    server = build_server(svc, ROOT)
    plain = svc.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)
    deliver(svc, "ceo", plain)
    reply = call(server, "feedback", task_id=plain.id, verdict="reject", note="Too long.")
    relayed = [m for m in svc.sent(ROOT) if m.feedback][-1]
    assert reply == (
        f"feedback reject recorded on {plain.id} for ceo (message {relayed.id}, source relayed); it does not wake ceo\n"
        'Recorded as relayed (your own reading): quality counts it as no verdict of the user. If the user said it, record their words, verbatim, '
        'with source="human".'
    )
    reply = call(server, "feedback", task_id=plain.id, verdict="reject", note="Too long.", source="human")
    human = [m for m in svc.sent(ROOT) if m.feedback][-1]
    assert reply == (
        f"feedback reject recorded on {plain.id} for ceo (message {human.id}, source human); it does not wake ceo\n"
        'Next: if the user wants it redone, send it back with delegate(to="ceo", title=..., goal=<their corrections, in their words>, '
        f'acceptance=<the criteria, verbatim>, revises="{plain.id}", source="human"). A one-off task has no contract: no criterion changes.'
    )
    reply = call(server, "feedback", task_id=plain.id, verdict="accept", source="human")
    accepted = [m for m in svc.sent(ROOT) if m.feedback][-1]
    assert reply == f"feedback accept recorded on {plain.id} for ceo (message {accepted.id}, source human); it does not wake ceo"


def test_mcp_reject_with_a_reading_then_define_service_answers_is_admitted(svc):
    """DR-46: root passes its reading as `criterion` on the rejection; the reply gives the exact question with that id, and the user's yes is
    recorded by define_service(answers=..., about=<that id>, words=...), which writes the link itself."""
    server = build_server(svc, ROOT)
    task = request(svc, "ai")
    deliver(svc, "ceo", task)
    reply = call(server, "feedback", task_id=task.id, verdict="reject", note="Always start with a Summary line.", source="human", criterion=["C1"])
    no = [m for m in svc.sent(ROOT) if m.feedback][-1]
    assert 'in these words: "About C1: add "<the rule, in their words>" as a lasting rule? Yes or no."' in reply
    assert f'answers="{no.id}", about="C1", words="<their answer, verbatim>"' in reply
    answer = call(server, "define_service", owner="ceo", name=WEEKDAY, add_acceptance=["Starts with a Summary line"], answers=no.id, about="C1",
                  words="Yes, add it.")
    (link,) = [m for m in svc.sent(ROOT) if m.reply_to == no.id and m.criterion]
    assert f"Recorded as the user's answer to R1 (rejection {no.id}; your question named C1): link {link.id} names C3." in answer
    assert (link.criterion, link.source) == ("C3", "human")
    assert "C3: Starts with a Summary line" in answer and "(not confirmed)" not in answer.split("Recorded as")[0].split("Acceptance criteria now")[1]


def test_agent_feedback_surface_is_unchanged(svc):
    agent = described(svc, "ceo")["feedback"]
    assert set(agent.inputSchema["properties"]) == {"task_id", "verdict", "note"}
    text = " ".join(agent.description.split())
    assert 'source: "human"' not in text and 'criterion (reject only)' not in text and "confirms:" not in text and "the user's own" not in text
    assert "optional for accept. It costs no run" in text and "Give it on your own judgement of each delivery" in text
    assert set(described(svc, ROOT)["feedback"].inputSchema["properties"]) == {"task_id", "verdict", "note", "source", "criterion", "confirms"}


def test_revise_playbook_without_evidence_is_a_schema_error(svc):
    ceo = build_server(svc, "ceo")
    message = fails(ceo, "revise_playbook", service=WEEKDAY, content="## Steps\n1. Search.", reason="first draft")
    assert "evidence" in message and "required" in message.lower()
    assert services.read_playbook(svc, "ceo", WEEKDAY).version == 0
    schema = {t.name: t for t in asyncio.run(ceo.list_tools())}["revise_playbook"].inputSchema
    assert schema["required"] == ["service", "content", "reason", "evidence"]
    assert schema["properties"]["evidence"] == {"items": {"type": "string"}, "title": "Evidence", "type": "array"}
    assert "now v1" in call(ceo, "revise_playbook", service=WEEKDAY, content="## Steps\n1. Search.", reason="first draft", evidence=[])


def test_the_revise_playbook_docstring_asks_for_the_clients_evidence(svc):
    text = " ".join(described(svc, "ceo")["revise_playbook"].description.split())
    assert "evidence (required): the ids it rests on, from the regression list and the digest in your prompt" in text
    assert "It is admitted only when the same criterion or regression assertion failed in 2 different cases the client rejected" in text
    assert "Pass evidence=[] only for the first playbook (the steps your team followed, nothing more), or to restore unchanged a version your parent wrote." in text
    assert "A refusal writes nothing and gives you a question to send your parent once; do not wait for the answer" in text


def test_revise_playbook_docstring_says_line_by_line(svc):
    text = " ".join(described(svc, "ceo")["revise_playbook"].description.split())
    assert (
        "contract by an amendment the client confirmed (your Reflect section and the amendment note name them); line by line: under the first "
        'rule every line you add or change carries the id it rests on ("[C6]"), under the second it is only that criterion\'s words '
        '("- C<k>: <its text>"); a link note id counts as its criterion; your lessons, relayed verdicts and an agent client\'s verdicts are not evidence.'
    ) in text


def test_root_request_rework_without_source_is_relayed(svc):
    server = build_server(svc, ROOT)
    first = request(svc, "ai")
    deliver(svc, "ceo", first, runs=1)
    call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id, budget=3)
    call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id, budget=3, source="human")
    plain = call(server, "request", service=WEEKDAY, inputs={"topic": "other"})
    sent = svc.received("ceo")
    assert [m.source for m in sent if m.revises == first.id] == ["relayed", "human"]
    assert [m.source for m in sent if m.id in plain] == [None]  # a fresh request is the user's ask: not stamped
    assert "source: relayed" in [m for m in sent if m.revises == first.id][0].to_text()


# ----------------------------------------------------------------------------------------- 4. case totals
def test_the_rework_reply_states_the_case_total_in_its_relayed_form(svc):
    """D-E5-1 (A3): root's rework without a source is relayed. Its reply states the case total, says the rework has used no run yet and that its
    runs are the assistant's own spend, and no longer says "exceeds ... tell the user" on the runs handed down for it (0a.2 did)."""
    server = build_server(svc, ROOT)
    first = request(svc, "ai")  # 10 runs handed down (the contract's); 4 used, 6 come back
    deliver(svc, "ceo", first, runs=4)
    plain = call(server, "request", service=WEEKDAY, inputs={"topic": "other"})
    assert "case total" not in plain  # not a rework: nothing to total
    reply = call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id, budget=8)  # 18 handed down, 6 came back: 12 can be spent
    (rework,) = [m for m in svc.sent(ROOT) if m.revises == first.id]
    assert "case total: 4 runs used of 18 handed down (contract: 10 per request)" in reply
    assert f"Your relayed rework {rework.id} has used no run yet; its runs will be your own spend, not the user's: report them to the user as yours" in reply
    assert "exceeds" not in reply and "tell the user" not in reply


def test_the_rework_the_user_asked_for_states_the_case_total_without_the_relayed_sentences(svc):
    """D-E5-1 (A3): a human rework (source "human") with a budget of 8 raises the approval to 4 + 6 + 8 = 18: its reply holds the case total only."""
    server = build_server(svc, ROOT)
    first = request(svc, "ai")
    deliver(svc, "ceo", first, runs=4)
    reply = call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id, budget=8, source="human")
    assert "case total: 4 runs used of 18 handed down (contract: 10 per request)" in reply
    assert "relayed" not in reply.split("case total:")[1] and "exceeds" not in reply and "tell the user" not in reply


def test_a_human_rework_without_a_budget_is_handed_what_is_left_of_the_approved_runs(svc):
    """D-E5-1 (4.5): the first request used 3 of its 10 runs and 7 came back, so the rework the user asked for, sent without a budget, gets 7."""
    server = build_server(svc, ROOT)
    first = request(svc, "ai")
    deliver(svc, "ceo", first, runs=3)
    reply = call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id, source="human")
    (rework,) = [m for m in svc.sent(ROOT) if m.revises == first.id]
    assert rework.budget == 7 and "budget 7" in reply
    assert "case total: 3 runs used of 17 handed down (contract: 10 per request)" in reply
    relayed = call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id)  # no source: the assistant's own, the contract's 10
    assert "budget 10" in relayed


def hire_second_report(svc):
    svc.hire("ceo", "qa", "Tester", "Test things.")  # ceo now has two agents below: a round of its team is 1 + 2 * 2 = 5


NOTHING_LEFT = "Nothing else is left of the runs the user approved for this case."
DEFAULT_RUN = "Nothing else was left of the runs the user approved for this case when this rework was sent: its own run is beyond them, and the ask includes it."
DEFAULT_RUN_HELD = (
    "Nothing else was left of the runs the user approved for this case when this rework was sent: its own run is beyond them, and the runs the team "
    "holds cover the round without it. Ask for nothing; tell the user that this 1 run is beyond their approval."
)
TOP_UP = (
    "This rework has {budget} run(s), and a rework of this team needs about 5 (1, plus 2 for each agent below ceo). {left} Ask the user now "
    'for {ask} more run(s), with that number; on yes, grant {ask}: send(to="ceo", budget={ask}, body=<why>) '
    '(CLI: hirearchy send ceo "<why>" --budget {ask}).'
)


def test_the_reply_to_a_user_rework_below_a_round_of_the_team_names_the_top_up_after_the_case_total(svc):
    """D-E5-1 (4.5): 8 of the first request's 10 runs were used and 2 came back, so the rework without a budget gets the 2 that are left; a round is 5."""
    hire_second_report(svc)
    server = build_server(svc, ROOT)
    first = request(svc, "ai")
    deliver(svc, "ceo", first, runs=8)
    reply = call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id, source="human")
    (rework,) = [m for m in svc.sent(ROOT) if m.revises == first.id]
    total = "case total: 8 runs used of 12 handed down (contract: 10 per request)"
    assert rework.budget == 2 and f"budget 2 " in reply
    assert reply.endswith(f"\n{total}\n{TOP_UP.format(budget=2, ask=3, left=NOTHING_LEFT)}")  # the top-up comes after the case total
    assert "exceeds" not in reply


def test_a_user_rework_with_nothing_left_is_sent_with_one_run_and_the_reply_asks_for_the_rest(svc):
    """Nothing is refused: the rework carries 1 run, the reply holds the case total and the top-up for ``need``. D-E7-2 A1 (14 Rule A1, item 6): that 1
    run is beyond the user's approval, so the ask and the grant include it (5, was 4) and the reply names it."""
    hire_second_report(svc)
    server = build_server(svc, ROOT)
    first = request(svc, "ai")
    deliver(svc, "ceo", first, runs=10)  # all 10 used, none back
    reply = call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id, source="human")
    (rework,) = [m for m in svc.sent(ROOT) if m.revises == first.id]
    assert rework.budget == 1 and "case total: 10 runs used of 11 handed down (contract: 10 per request)" in reply
    assert reply.endswith(TOP_UP.format(budget=1, ask=5, left=DEFAULT_RUN))


def test_the_reply_to_a_user_rework_of_a_blocked_request_with_unspent_runs_says_the_team_holds_them(svc):
    """D-E6-2 (B2): the first request is blocked with 2 of its 10 runs used, so the team still holds 8 of the user's runs for it: the rework without a
    budget gets 1 run, and the reply ends with the HELD sentence after the case total, asking nothing (0a.3 asked for 4 more). D-E7-2 A1 (14 Rule A1,
    item 11): that 1 run is the default with nothing left, so the HELD sentence is followed by the one that names it, and the case total says the case
    exceeds the contract's budget (A2: 2 used and 8 held, plus the 1 run, are 11 of 10)."""
    hire_second_report(svc)
    server = build_server(svc, ROOT)
    first = request(svc, "ai")
    deliver(svc, "ceo", first, status="blocked", runs=2)
    reply = call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id, source="human")
    (rework,) = [m for m in svc.sent(ROOT) if m.revises == first.id]
    assert rework.budget == 1 and "budget 1 " in reply
    held = f"The team still holds 8 of the user's runs for {first.id}; the rework can use them."
    total = "case total: 2 runs used of 11 handed down (contract: 10 per request). This case now exceeds the per-request budget of 10: tell the user."
    assert reply.endswith(f"\n{total}\n{held} {DEFAULT_RUN_HELD}")
    assert "Ask the user now" not in reply and "Nothing else is left" not in reply


def test_a_rework_within_the_contract_budget_gets_no_warning(svc):
    server = build_server(svc, ROOT)
    first = svc.request(ROOT, WEEKDAY, {"topic": "ai"}, budget=3)
    deliver(svc, "ceo", first, runs=2)
    reply = call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id, budget=4)
    assert "case total: 2 runs used of 7 handed down (contract: 10 per request)" in reply and "exceeds" not in reply


# ------------------------------------------------------------------------------------------ 5. escaping
def test_angle_brackets_and_ampersands_are_stored_exactly_as_given(svc):
    reason = 'Cases rejected for <weekday> & "dates"; keep &lt;literal&gt; -> done'
    content = "## Steps\n1. Resolve <weekday> and <date> & check \"quotes\" and &amp; entities.\n"
    server = build_server(svc, "ceo")
    call(server, "revise_playbook", service=WEEKDAY, content=content, reason=reason, evidence=[])
    pb = services.read_playbook(svc, "ceo", WEEKDAY)
    assert pb.reason == reason and pb.body == content.strip()
    raw = (svc.dir("ceo") / "services" / WEEKDAY / "PLAYBOOK.md").read_text()
    assert "<weekday>" in raw and "&lt;literal&gt;" in raw and "&amp;lt;" not in raw
    # the notice to the client, the listing and the owner's prompt carry the same characters
    assert reason in [m.body for m in svc.messages(ROOT, "inbox")][-1]
    assert f'"{reason}"' in services.services_text(svc, ROOT)
    request(svc, "ai")
    assert "Resolve <weekday> and <date> & check" in svc.run_prompt("ceo", svc.begin_run("ceo"))

    # the same through the Org API, and in the archived history
    svc.end_run("ceo", ok=True)  # the run the prompt above opened
    c3 = confirmed_amendment(svc, "Names the week it covers")  # the user's amendment and their yes: the evidence of v2
    svc.revise_playbook("ceo", WEEKDAY, content.rstrip() + "\n- C3: Names the week it covers", "second <i> & more", [c3])
    assert services.read_playbook(svc, "ceo", WEEKDAY).reason == "second <i> & more"
    assert "<weekday>" in (svc.dir("ceo") / "services" / WEEKDAY / "history" / "PLAYBOOK.v1.md").read_text()


# ------------------------------------------------------------------------------------ tools by role
def tool_names(org, addr):
    return {t.name for t in asyncio.run(build_server(org, addr).list_tools())}


CLIENT_TOOLS = {"services", "define_service", "request", "feedback"}


def test_tools_are_registered_by_role(org):
    assert not tool_names(org, ENG) & (CLIENT_TOOLS | {"revise_playbook"})  # a plain worker sees none
    assert CLIENT_TOOLS <= tool_names(org, "ceo") and "revise_playbook" not in tool_names(org, "ceo")
    assert CLIENT_TOOLS <= tool_names(org, ROOT) and "revise_playbook" not in tool_names(org, ROOT)
    define(org)
    define(org, owner=ENG, actor="ceo", name="eng-brief")
    assert {"services", "revise_playbook"} <= tool_names(org, ENG) and not {"define_service", "request"} & tool_names(org, ENG)
    assert CLIENT_TOOLS | {"revise_playbook"} <= tool_names(org, "ceo")  # ceo is both a client and an owner
    org.hire(ROOT, "lone", "Lone worker", "Works alone.")
    define(org, owner="lone", name="lone-brief")
    assert tool_names(org, "lone") & (CLIENT_TOOLS | {"revise_playbook"}) == {"services", "revise_playbook"}


def test_the_services_tool_describes_what_you_can_request_and_offer(org):
    server = build_server(org, ROOT)
    assert "No services yet" in call(server, "services") and "define_service" in call(server, "services")
    define(org, playbook="Steps.")
    t1 = request(org, "ai")
    deliver(org, "ceo", t1, runs=3)
    no1 = org.feedback(ROOT, t1.id, "reject", "Bad.", source="human")
    org.feedback(ROOT, t1.id, "reject", "Yes, it is about C2.", source="human", criterion=["C2"], confirms=no1.id)
    t2 = request(org, "chips")
    deliver(org, "ceo", t2, runs=2)
    no2 = org.feedback(ROOT, t2.id, "reject", "Still bad.", source="human")
    org.feedback(ROOT, t2.id, "reject", "Yes, it is about C2.", source="human", criterion=["C2"], confirms=no2.id)  # C2 failed in two cases: the evidence of v2
    org.revise_playbook("ceo", "weekly-brief", "Better steps. [C2]", "Case rejected for missing sources", ["C2"])
    out = call(server, "services")
    assert out.splitlines()[0] == "Services you can request (from your direct reports):"
    assert "- weekly-brief (offered by ceo; contract v1, playbook v2): A one-page brief" in out
    assert "inputs: topic* (what the brief is about), week (ISO week; default the current one)   (* required)" in out
    assert ("each request: 10 runs; acceptance criteria (ceo/services/weekly-brief/SERVICE.md):\n"
            "    C1: At most 600 words\n    C2: Every factual claim has a source URL\n  record:") in out
    assert f"record: 2 request(s): 2 done, 0 failed, 0 open; 0 reworked; avg {(3 + 2) / 2:g} runs; feedback 0 accept, 2 reject" in out
    assert '  playbook v2 (' in out and '"Case rejected for missing sources"' in out
    assert "Services you offer" not in out
    mine = call(build_server(org, "ceo"), "services")
    assert "Services you offer:" in mine and "playbook file: ceo/services/weekly-brief/PLAYBOOK.md" in mine
    assert "Services you can request" not in mine  # ceo's report offers nothing


# ------------------------------------------------------------------------------- the whole loop
def test_define_request_report_reject_reflect_revise_and_compare_versions(org):
    root = build_server(org, ROOT)

    out = call(root, "define_service", owner="ceo", name="weekly-brief", description=BRIEF["description"],
               acceptance=BRIEF["acceptance"], deliverable=BRIEF["deliverable"], budget=10, inputs=BRIEF["inputs"])
    assert "defined service `weekly-brief`" in out
    ceo = build_server(org, "ceo")  # the owner's run starts after the definition: it now has revise_playbook
    out = call(root, "request", service="weekly-brief", inputs={"topic": "ai"})
    assert "requested service `weekly-brief` from ceo" in out and "Call start() if the scheduler is not running." in out
    task = org.outstanding(ROOT)[0]

    # the owner's first run: no playbook yet
    prompt = org.run_prompt("ceo", work(org, "ceo", 2))
    assert "No playbook yet" in prompt and "# Reflect" not in prompt
    assert "pass `lessons`" in fails(ceo, "report", task_id=task.id, status="done", summary="Delivered.")
    out = call(ceo, "report", task_id=task.id, status="done", summary="Delivered.", lessons="Used 2 runs; no checks.")
    assert "reported done" in out and "This service has no playbook yet: write v1 now with revise_playbook" in out
    org.end_run("ceo", ok=True)
    assert "now v1" in call(ceo, "revise_playbook", service="weekly-brief", content="## Steps\n1. Search.",
                            reason="first draft", evidence=[])
    assert services.read_playbook(org, "ceo", "weekly-brief").version == 1

    # the client rejects the delivery
    out = call(root, "feedback", task_id=task.id, verdict="reject", note="Missing week-over-week changes.", source="human")
    assert "feedback reject recorded" in out
    assert "needs a note" in fails(root, "feedback", task_id=task.id, verdict="reject")

    # the user's yes comes before the next request (clause 2: a new request waits for it)
    rejection = max(m.id for m in org.sent(ROOT) if m.feedback)
    assert "has no recorded answer yet" in fails(root, "request", service="weekly-brief", inputs={"topic": "chips"})
    call(root, "define_service", owner="ceo", name="weekly-brief", add_acceptance=["Shows the changes since last week"],  # C3: the evidence of v2
         answers=rejection, about="C1", words="Yes, add it.")  # Rule A: the user's yes, and the product writes the link

    # the next request: the prompt shows the rejection before the new message
    second = org.request(ROOT, "weekly-brief", {"topic": "chips"})
    prompt = org.run_prompt("ceo", work(org, "ceo", 1))
    section = prompt.split("# Reflect before you start: weekly-brief")[1].split("# New messages")[0]
    assert "Evidence since v1:" in section and "Missing week-over-week changes." in section
    assert "Used 2 runs; no checks." in section
    out = call(ceo, "revise_playbook", service="weekly-brief",
               content="## Steps\n1. Search.\n- C3: Shows the changes since last week", reason=f"case {task.id} rejected: no changes", evidence=["C3"])
    assert "playbook of `weekly-brief` is now v2" in out
    out = call(ceo, "report", task_id=second.id, status="done", summary="Delivered again.", lessons="Step 2b worked.")
    assert "Lessons recorded: they are your team's view and are shown before the next request. A playbook revision rests on the client's evidence" in out
    org.end_run("ceo", ok=True)
    call(root, "feedback", task_id=second.id, verdict="accept")

    # stats show both versions
    listing = call(root, "services")
    assert "playbook v2" in listing and "2 request(s): 2 done, 0 failed, 0 open" in listing
    assert "feedback 1 accept, 1 reject" in listing
    per = services.stats_by_version(services.cases(org, "ceo", "weekly-brief"))
    # request 1 was delivered with no playbook (v1 was written after its report); request 2 was sent at v1 but
    # revised to v2 before it was worked on, so v2 is the version that delivered it
    assert sorted(per) == [0, 2] and [c.playbook for c in services.cases(org, "ceo", "weekly-brief")] == [0, 1]
    assert (per[0].reject, per[0].requests) == (1, 1) and (per[2].accept, per[2].requests) == (1, 1)
    # the evidence was consumed by the revision: nothing new until the next case finishes
    assert services.reflection_digest(org, "ceo", "weekly-brief") is not None  # case 2 finished after v2
    ids = [m.id for m in org.received(ROOT) if m.type == "result"]
    assert len(ids) == 2
    meta = yaml.safe_load((org.dir("ceo") / "services" / "weekly-brief" / "PLAYBOOK.md").read_text().split("---\n")[1])
    assert meta["version"] == 2 and meta["by"] == "ceo"


def test_a_locked_service_reports_without_the_revision_hint(org):
    define(org, locked=True)
    ceo = build_server(org, "ceo")
    task = request(org)
    work(org, "ceo")
    out = call(ceo, "report", task_id=task.id, status="done", summary="Delivered.", lessons="Fine.")
    assert out.startswith("reported done") and "revise_playbook" not in out
    assert "locked by root" in fails(ceo, "revise_playbook", service="weekly-brief", content="x", reason="r", evidence=[])


# ----------------------------------------------------------------------------------------- clause 2: a new request waits for the answers (design 13.1, 14.5)
def test_root_request_meets_request_unanswered_through_mcp(svc):
    server = build_server(svc, ROOT)
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    no = svc.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    sent = len(svc.sent(ROOT))
    text = fails(server, "request", service=WEEKDAY, inputs={"topic": "next"})
    assert f"refused: rejection R1 (message {no.id}) on task {first.id} of `weekly-brief` has no recorded answer yet, so the next request of `weekly-brief` waits" in text
    assert text.endswith("A rework of that case (revises=) is not held. Nothing was sent.")
    assert len(svc.sent(ROOT)) == sent
    assert "requested service `weekly-brief`" in call(server, "request", service=WEEKDAY, inputs={"topic": "ai"}, revises=first.id, source="human")  # a rework is not held


def test_root_request_docstring_says_a_new_request_waits_for_the_answers(svc):
    text = " ".join(described(svc, ROOT)["request"].description.split())
    assert "A new request waits until every rejection since the previous one has the user's answer; the refusal gives the question." in text
    assert "answer" not in " ".join(described(svc, "ceo")["request"].description.split())  # the agents' tool is what it was


# ----------------------------------------------------------------------------------------- clause 2: a human accept waits for the case's answers (design 13.2, 14.5)
def test_root_feedback_with_source_human_meets_feedback_unanswered(svc):
    server = build_server(svc, ROOT)
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    no = svc.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    sent = len(svc.sent(ROOT))
    text = fails(server, "feedback", task_id=first.id, verdict="accept", source="human")
    assert f"refused: rejection R1 (message {no.id}) on task {first.id} of this case of `weekly-brief` has no recorded answer yet, so the user's accept waits" in text
    assert text.endswith("Nothing was recorded.") and len(svc.sent(ROOT)) == sent
    relayed = call(server, "feedback", task_id=first.id, verdict="accept")  # the MCP default source is relayed: never held
    assert "source relayed" in relayed


def test_root_feedback_docstring_says_an_accept_waits_for_the_cases_answers(svc):
    text = " ".join(described(svc, ROOT)["feedback"].description.split())
    assert "An accept waits while an earlier rejection of the same case has no answer from the user; the refusal gives the question." in text
    assert "waits" not in " ".join(described(svc, "ceo")["feedback"].description.split())  # the agents' tool is what it was
