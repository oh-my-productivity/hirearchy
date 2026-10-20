# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import time

from testkit.legacy.orgmcp.core import ROOT
from testkit.services_world import ENG, define, deliver, request, svc, work

WEEKDAY = "weekly-brief"


# --------------------------------------------------------------------- 2/3. reflect at the moment of rejection
def reflect_section(prompt):
    return prompt.split("# Reflect before you start: weekly-brief")[1].split("# New messages")[0]


def test_a_rejection_with_its_rework_request_brings_the_reflect_section(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first, lessons="Clean run.")
    svc.feedback(ROOT, first.id, "reject", "Sam's date is wrong.")
    svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=5)  # a rework: not a NEW request
    prompt = svc.run_prompt("ceo", svc.begin_run("ceo"))
    section = reflect_section(prompt)
    assert 'client feedback: reject "Sam\'s date is wrong."' in section
    assert (
        "The client rejected a delivery: decide now whether the playbook must change so this does not happen again "
        "(revise_playbook), then handle the rework."
    ) in section
    assert "Before working on the new request" not in section
    assert "When a lesson of yours conflicts with the client's feedback, the client is right: fix the playbook to match "\
           "the feedback (and say so in the reason)." in section
    assert section.rstrip().endswith("Then handle the rework following the playbook.")
    assert prompt.count("# Reflect before you start") == 1
    assert prompt.index("# Reflect before") < prompt.index("# New messages")


def test_two_rejections_in_one_batch_give_one_reflect_section_per_service(svc):
    a, b = request(svc, "a"), request(svc, "b")
    work(svc, "ceo")
    svc.report("ceo", a.id, "done", "ok", lessons="fine")
    svc.report("ceo", b.id, "done", "ok", lessons="fine")
    svc.end_run("ceo", ok=True)
    svc.feedback(ROOT, a.id, "reject", "first problem")
    svc.feedback(ROOT, b.id, "reject", "second problem")
    prompt = svc.run_prompt("ceo", svc.begin_run("ceo"))
    assert prompt.count("# Reflect before you start: weekly-brief") == 1
    assert "first problem" in prompt and "second problem" in prompt


def test_an_accept_or_a_rework_without_a_reject_brings_no_reflect_section(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "accept", "good")
    assert "# Reflect" not in svc.run_prompt("ceo", svc.begin_run("ceo"))
    svc.end_run("ceo", ok=True)


def test_a_reject_with_a_new_request_keeps_the_new_request_wording(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "Too long.")
    request(svc, "chips")
    section = reflect_section(svc.run_prompt("ceo", svc.begin_run("ceo")))
    assert "The client rejected a delivery: decide now" in section and "then handle the request." in section
    assert section.rstrip().endswith("Then handle the request following the playbook.")


def test_the_client_wins_step_is_in_every_reflect_section(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    request(svc, "chips")
    section = reflect_section(svc.run_prompt("ceo", svc.begin_run("ceo")))
    assert "the client is right: fix the playbook to match the feedback (and say so in the reason)" in section
    assert [line[:2] for line in section.splitlines() if line[:1].isdigit()][:2] == ["1.", "2."]


def test_a_locked_service_reflects_on_a_rejection_without_revising(svc):
    define(svc, name="locked-brief", owner="ceo", locked=True, description="Locked brief.")
    first = svc.request(ROOT, "locked-brief", {"topic": "ai"})
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "Too long.")
    svc.request(ROOT, "locked-brief", {"topic": "ai"}, revises=first.id, budget=3)
    section = svc.run_prompt("ceo", svc.begin_run("ceo")).split("# Reflect before you start: locked-brief")[1].split("# New messages")[0]
    assert "The client rejected a delivery. The contract is locked, so you cannot revise the playbook" in section
    assert "call `revise_playbook" not in section and "the client is right: follow the feedback" in section


def test_a_playbook_revised_after_the_rejection_leaves_no_reflect_section(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "Too long.")
    time.sleep(0.002)
    svc.revise_playbook("ceo", WEEKDAY, "Steps.", "after the rejection")
    svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=3)
    assert "# Reflect" not in svc.run_prompt("ceo", svc.begin_run("ceo"))


# ------------------------------------------------------------------------------------------ prompt
def headers(prompt):
    return [line for line in prompt.splitlines() if line.startswith("# ")]


def test_an_org_without_services_gets_the_prompt_it_always_had(org):
    org.delegate(ROOT, "ceo", "Plan", "Make a plan", "plan.md exists", budget=4)
    batch = org.begin_run("ceo")
    prompt = org.run_prompt("ceo", batch)
    assert headers(prompt) == [
        "# orgmcp run: you are `ceo`", "# Organization", "# Your charter (ceo/AGENT.md, owned by your parent)",
        "# Role: Chief executive", "# Your memory (ceo/MEMORY.md)", "# Your state", "# New messages for this run (1)",
    ]
    assert "Your services" not in prompt and "Playbook:" not in prompt and "Reflect before" not in prompt
    assert prompt.count("\n\n\n") == 0 and "- Paths: every path" in prompt
    # the gap between the state and the messages is the single blank line it always was
    assert "Yours start with `ceo/`.\n\n# New messages for this run (1)\n" in prompt
    org.end_run("ceo", ok=True)
    # a service offered by someone else changes nothing for ceo
    define(org, owner=ENG, actor="ceo")
    org.delegate(ROOT, "ceo", "Plan 2", "Make a plan", "plan.md exists", budget=4)
    assert headers(org.run_prompt("ceo", org.begin_run("ceo"))) == headers(prompt)
    # and the tree and tools of a service-less agent are unchanged
    assert "services:" not in org.tree().split("ceo ")[1].split("\n")[0]


def test_the_prompt_lists_the_owners_services_every_run(svc):
    org = svc
    org.delegate(ROOT, "ceo", "Plain", "g", "c", budget=2)  # a plain task: no playbook, no reflection
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Your services" in prompt and "# Playbook" not in prompt and "# Reflect" not in prompt
    assert (
        "- weekly-brief: contract v1, no playbook yet, 0 request(s) so far; contract: ceo/services/weekly-brief/SERVICE.md; "
        "playbook: ceo/services/weekly-brief/PLAYBOOK.md"
    ) in prompt
    assert prompt.index("# Your services") < prompt.index("# New messages")


def test_the_playbook_is_shown_only_with_an_open_service_task(org):
    define(org, playbook="## Steps\n1. Search the web.\n2. Write the brief.")
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))  # nothing to do
    assert "# Your services" in prompt and "# Playbook" not in prompt and "Search the web" not in prompt
    org.end_run("ceo", ok=True)
    task = request(org)
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Playbook: weekly-brief (v1, yours to improve)" in prompt
    assert "> ## Steps\n> 1. Search the web.\n> 2. Write the brief." in prompt
    org.end_run("ceo", ok=True)
    deliver(org, "ceo", task)
    assert "# Playbook" not in org.run_prompt("ceo", org.begin_run("ceo"))  # the task is answered


def test_a_service_without_a_playbook_says_how_to_start_one(svc):
    org = svc
    request(org)
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Playbook: weekly-brief (v0, yours to improve)" in prompt
    assert "No playbook yet: plan as usual; when you report this request, write v1 with revise_playbook" in prompt
    assert "# Reflect" not in prompt  # no evidence yet


def test_v0_playbook_section_agrees_with_the_reflect_section(svc):
    org = svc
    first = request(org, "ai")
    deliver(org, "ceo", first, lessons="Thin on sources.")
    request(org, "chips")  # a new request with evidence from an earlier case and still no playbook
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    playbook = prompt.split("# Playbook: weekly-brief")[1].split("\n# ")[0]
    assert "# Reflect before you start: weekly-brief" in prompt
    assert "No playbook yet: write v1 now from the evidence below (Reflect before you start), then follow it." in playbook
    assert "when you report this request" not in prompt  # the old text would contradict the reflect section
    assert prompt.index("# Playbook: weekly-brief") < prompt.index("# Reflect before you start")  # "below" is true
    org.end_run("ceo", ok=True)


def test_a_long_playbook_is_cut_with_a_pointer_to_the_file(org):
    define(org, playbook="wordwordword " * 700)  # under the word cap, over the render limit (8000 characters)
    request(org)
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "playbook cut" in prompt and 'read(path="ceo/services/weekly-brief/PLAYBOOK.md")' in prompt


def test_the_reflect_section_comes_before_a_new_request_when_there_is_evidence(svc):
    org = svc
    first = request(org, "ai")
    deliver(org, "ceo", first, runs=2, lessons="Thin on sources.")
    org.feedback(ROOT, first.id, "reject", "No week-over-week changes.")
    new = request(org, "chips")
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Reflect before you start: weekly-brief" in prompt
    section = prompt.split("# Reflect before you start: weekly-brief")[1].split("# New messages")[0]
    assert "Evidence so far (there is no playbook yet):" in section and "No week-over-week changes." in section
    assert "revise_playbook(service, content, reason)" in section and "at most 1000 words" in section
    assert "A rejection or a failure is enough on its own" in section and "never lower it" in section
    assert "restore" not in section  # nothing earlier to restore at v0
    assert section.rstrip().endswith("Then handle the request following the playbook.")
    assert [line[:2] for line in section.splitlines() if line[:1].isdigit()] == ["1.", "2.", "3.", "4.", "5."]
    assert prompt.index("# Reflect before") < prompt.index("# New messages") < prompt.index(new.id, prompt.index("# New messages"))
    org.end_run("ceo", ok=True)


def test_the_reflect_section_offers_restoring_an_older_version_from_v2_on(svc):
    org = svc
    org.revise_playbook("ceo", "weekly-brief", "Steps one.", "first")
    org.revise_playbook("ceo", "weekly-brief", "Steps two.", "second")
    time.sleep(0.002)
    first = request(org)
    deliver(org, "ceo", first)
    request(org, "again")
    section = org.run_prompt("ceo", org.begin_run("ceo")).split("# Reflect before you start")[1].split("# New messages")[0]
    assert "Evidence since v2:" in section and "restore that one" in section
    assert "ceo/services/weekly-brief/history/PLAYBOOK.v<k>.md" in section


def test_no_reflect_section_for_rework_old_evidence_or_a_locked_playbook_edit_step(svc):
    org = svc
    first = request(org)
    deliver(org, "ceo", first)
    rework = org.delegate(ROOT, "ceo", "Fix", "g", "c", budget=3, revises=first.id)  # not a NEW request
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Reflect" not in prompt and "# Playbook: weekly-brief" in prompt
    org.end_run("ceo", ok=True)
    deliver(org, "ceo", rework)
    org.revise_playbook("ceo", "weekly-brief", "Steps.", "after the rework")
    request(org)  # new request, but no evidence since v1
    assert "# Reflect" not in org.run_prompt("ceo", org.begin_run("ceo"))


def test_the_locked_variant_shows_evidence_but_no_revision_steps(org):
    define(org, locked=True)
    first = request(org)
    deliver(org, "ceo", first)
    org.feedback(ROOT, first.id, "reject", "Too long.")
    request(org)
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    section = prompt.split("# Reflect before you start: weekly-brief")[1].split("# New messages")[0]
    assert "locked by your parent" in section and "Too long." in section
    assert "call `revise_playbook" not in section and "restore" not in section
    assert "(v0, locked by your parent)" in prompt and "No playbook yet, and the contract is locked" in prompt
    assert "(locked)" in prompt.split("# Your services")[1].split("# ")[0]
