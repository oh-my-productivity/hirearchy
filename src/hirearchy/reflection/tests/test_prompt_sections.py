# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import time

from testkit.reach.hirearchy.core import ROOT
from testkit.services_world import ENG, amend_legacy, confirmed_amendment, define, deliver, legacy_playbook, request_unheld, svc, work, write_version
from testkit.services_world import request_unheld as request  # a new request that clause 2 would hold: these tests are about other rules

WEEKDAY = "weekly-brief"


# --------------------------------------------------------------------- 2/3. reflect at the moment of rejection
def reflect_section(prompt):
    return prompt.split("# Reflect before you start: weekly-brief")[1].split("# New messages")[0]


def test_a_rejection_with_its_rework_request_brings_the_reflect_section(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first, lessons="Clean run.")
    svc.feedback(ROOT, first.id, "reject", "Sam's date is wrong.", source="human")
    svc.request(ROOT, WEEKDAY, {"topic": "ai"}, revises=first.id, budget=5)  # a rework: not a NEW request
    prompt = svc.run_prompt("ceo", svc.begin_run("ceo"))
    section = reflect_section(prompt)
    assert 'client feedback: reject R1 "Sam\'s date is wrong."' in section
    assert HUMAN_LEAD.replace("the request", "the rework").replace("plan the request", "plan the rework") in section.splitlines()
    assert "Before working on the new request" not in section
    assert "When a lesson of yours conflicts with the client's own feedback (not a relayed verdict), the client is right: apply the feedback "\
           "in this rework." in section
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
    svc.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    request(svc, "chips")
    section = reflect_section(svc.run_prompt("ceo", svc.begin_run("ceo")))
    assert "The client rejected a delivery: check it against their words" in section and "or a criterion link." in section
    assert section.rstrip().endswith("Then handle the request following the playbook.")


def test_the_client_wins_step_is_in_every_reflect_section(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    request(svc, "chips")
    section = reflect_section(svc.run_prompt("ceo", svc.begin_run("ceo")))
    assert "the client is right: apply the feedback in this request." in section
    assert [line[:2] for line in section.splitlines() if line[:1].isdigit()][:2] == ["1.", "2."]


def test_a_locked_service_reflects_on_a_rejection_without_revising(svc):
    define(svc, name="locked-brief", owner="ceo", locked=True, description="Locked brief.")
    first = svc.request(ROOT, "locked-brief", {"topic": "ai"})
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    svc.request(ROOT, "locked-brief", {"topic": "ai"}, revises=first.id, budget=3)
    section = svc.run_prompt("ceo", svc.begin_run("ceo")).split("# Reflect before you start: locked-brief")[1].split("# New messages")[0]
    assert "The client rejected a delivery. The contract is locked, so you cannot change the playbook" in section
    assert "change one item with `revise_playbook`" not in section and "the client is right: follow the feedback" in section


def test_a_playbook_revised_after_the_rejection_leaves_no_reflect_section(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "Too long.")
    time.sleep(0.002)
    legacy_playbook(svc, "Steps.", reason="after the rejection")  # after a verdict a free v1 is refused (PB-FIRST-LATE)
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
        "# hirearchy run: you are `ceo`", "# Organization", "# Your charter (ceo/AGENT.md, owned by your parent)",
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
    assert "# Playbook: weekly-brief (v1, yours to improve one item at a time; 8 of 1000 words)" in prompt
    assert "> ## Steps\n> 1. [P1] Search the web.\n> 2. [P2] Write the brief." in prompt
    org.end_run("ceo", ok=True)
    deliver(org, "ceo", task)
    assert "# Playbook" not in org.run_prompt("ceo", org.begin_run("ceo"))  # the task is answered


def test_a_service_without_a_playbook_says_how_to_start_one(svc):
    org = svc
    request(org)
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Playbook: weekly-brief (v0, yours to improve)" in prompt
    assert 'No playbook yet: plan as usual; when you report this request, write v1 with revise_playbook(op="first", text=...)' in prompt
    assert "# Reflect" not in prompt  # no evidence yet


def test_v0_playbook_section_agrees_with_the_reflect_section(svc):
    org = svc
    first = request(org, "ai")
    deliver(org, "ceo", first, lessons="Thin on sources.")
    request(org, "chips")  # a new request with evidence from an earlier case and still no playbook
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    playbook = prompt.split("# Playbook: weekly-brief")[1].split("\n# ")[0]
    assert "# Reflect before you start: weekly-brief" in prompt
    assert (
        'No playbook yet: write v1 now from how the team works with revise_playbook(op="first", text=...) (Reflect before you start shows the '
        "evidence; rules from lessons or relayed verdicts are not steps), then follow it. The first version needs no evidence and is allowed only "
        "until the client's first verdict or rework; after that, add items one at a time (op=\"add\") with the client's evidence."
    ) in playbook
    assert "when you report this request" not in prompt  # the other text would contradict the reflect section
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
    org.feedback(ROOT, first.id, "reject", "No week-over-week changes.", source="human")
    new = request(org, "chips")
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Reflect before you start: weekly-brief" in prompt
    section = prompt.split("# Reflect before you start: weekly-brief")[1].split("# New messages")[0]
    assert "Evidence so far (there is no playbook yet):" in section and "No week-over-week changes." in section
    assert "change one item with `revise_playbook` (its description gives the ops)" in section and "whole new playbook" not in section
    assert "A rejection or a failure is enough to look into on its own" in section and "never lower it" in section
    assert "restore" not in section
    assert section.rstrip().endswith("Then handle the request following the playbook.")
    assert [line[:2] for line in section.splitlines() if line[:1].isdigit()] == ["1.", "2.", "3.", "4.", "5."]
    assert prompt.index("# Reflect before") < prompt.index("# New messages") < prompt.index(new.id, prompt.index("# New messages"))
    org.end_run("ceo", ok=True)


def test_the_reflect_section_no_longer_offers_restoring_a_whole_version_from_v2_on(svc):
    org = svc
    org.revise_playbook("ceo", "weekly-brief", "first", "first", [], text="Steps one.")
    c3 = confirmed_amendment(org, "Every claim names its source")  # the user's amendment and their yes: the evidence of v2
    org.revise_playbook("ceo", "weekly-brief", "add", "second", [c3], kind="step", text="Every claim names its source")
    time.sleep(0.002)
    first = request(org)
    deliver(org, "ceo", first)
    request(org, "again")
    section = org.run_prompt("ceo", org.begin_run("ceo")).split("# Reflect before you start")[1].split("# New messages")[0]
    assert "Evidence since v2:" in section and "restore that one" not in section  # op="restore" is per item (14.2)
    assert "history/PLAYBOOK.v<k>.md" not in section and [x[:2] for x in section.splitlines() if x[:1].isdigit()] == ["1.", "2.", "3.", "4.", "5."]


def test_no_reflect_section_for_rework_old_evidence_or_a_locked_playbook_edit_step(svc):
    org = svc
    first = request(org)
    deliver(org, "ceo", first)
    rework = request(org, revises=first.id, budget=3)  # not a NEW request
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Reflect" not in prompt and "# Playbook: weekly-brief" in prompt
    org.end_run("ceo", ok=True)
    deliver(org, "ceo", rework)
    legacy_playbook(org, "Steps.", reason="after the rework")  # after a rework a free v1 is refused (PB-FIRST-LATE)
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


# ------------------------------------------------------------------------------------------ the evidence gate in the texts
def step_3(section):
    return next(line for line in section.splitlines() if line.startswith("3. "))


def test_step_3_for_a_human_client_names_evidence_and_the_refusal_question(svc):
    org = svc
    first = request(org, "ai")
    deliver(org, "ceo", first, lessons="Thin on sources.")
    request(org, "chips")
    section = reflect_section(org.run_prompt("ceo", org.begin_run("ceo")))
    assert step_3(section) == STEP_3


def test_step_3_says_what_a_rule_needs_what_is_watched_and_what_needs_the_parents_acknowledgement(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first, lessons="Thin on sources.")
    request(svc, "chips")
    step = step_3(reflect_section(svc.run_prompt("ceo", svc.begin_run("ceo"))))
    assert "A rule, or a step that changes a check, an output or how a criterion is handled, needs evidence in `evidence`: the same criterion or " \
           "assertion failed in 2 different cases the client rejected, or the item is the own words of a criterion the client confirmed (" in step
    assert "Lessons and relayed verdicts are not evidence. An admitted item is watched: a related client rejection warns it, a second retires it." in step
    assert "Retiring or weakening an item that covers a criterion needs your parent's acknowledgement." in step  # Q4 (B10)
    assert "whole new playbook" not in step and "[C6]" not in step and "- C<k>" not in step


def step_3_after(org):
    """The owner's step 3 for a new request, once the user has rejected a delivery (``org`` may already hold amendments)."""
    first = request(org, "first")
    deliver(org, "ceo", first, lessons="Thin on sources.")
    org.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    request(org, "next")
    return step_3(reflect_section(org.run_prompt("ceo", org.begin_run("ceo"))))


CLAUSE = "a criterion the client confirmed ("


def test_step_3_names_the_confirmed_amendments(svc):
    org = svc
    assert f"{CLAUSE}none yet)" in step_3_after(org)  # no amendment at all
    assert "not confirmed yet" not in step_3_after(org)


def test_step_3_names_one_confirmed_amendment(svc):
    org = svc
    c3 = confirmed_amendment(org, "Every claim names its source")
    assert f"{CLAUSE}now {c3} (an item may be the own words of it))" in step_3_after(org)


def test_step_3_names_several_confirmed_amendments(svc):
    org = svc
    c3 = confirmed_amendment(org, "Every claim names its source", topic="one")
    c4 = confirmed_amendment(org, "Every figure names its date", topic="two")
    assert f"{CLAUSE}now {c3}, {c4} (an item may be the own words of one))" in step_3_after(org)


def test_step_3_says_which_amendments_are_not_confirmed_yet(svc):
    org = svc
    amend_legacy(org, add_acceptance=["Quote the source"])  # an amendment nobody confirmed: C3
    assert f"{CLAUSE}none yet; C3 not confirmed yet)" in step_3_after(org)
    c4 = confirmed_amendment(org, "Every claim names its source")
    amend_legacy(org, add_acceptance=["Quote the date"])
    assert f"{CLAUSE}now {c4} (an item may be the own words of it); C3, C5 not confirmed yet)" in step_3_after(org)


def test_eligible_ids_say_an_item_may_be_the_own_words(svc):
    """One id, several, none yet, and the unconfirmed ones appended (``_eligible``)."""
    org = svc
    assert f"{CLAUSE}none yet)" in step_3_after(org)
    c3 = confirmed_amendment(org, "Every claim names its source", topic="one")
    assert f"{CLAUSE}now {c3} (an item may be the own words of it))" in step_3_after(org)
    c4 = confirmed_amendment(org, "Every figure names its date", topic="two")
    assert f"{CLAUSE}now {c3}, {c4} (an item may be the own words of one))" in step_3_after(org)
    amend_legacy(org, add_acceptance=["Quote the source"])  # C5: nobody confirmed it
    amend_legacy(org, add_acceptance=["Quote the date"])  # C6
    assert f"{CLAUSE}now {c3}, {c4} (an item may be the own words of one); C5, C6 not confirmed yet)" in step_3_after(org)


def test_eligible_names_user_initiated_ids_as_never_admitted(svc):
    """A change the user asked for on their own is named apart from the unconfirmed ones: it never counts (``_eligible``)."""
    org = svc
    v1 = ["At most 600 words", "Every factual claim has a source URL"]
    write_version(org, 2, [*v1, "One page"], initiated="user", words="Keep it to one page.")  # C3
    assert f"{CLAUSE}none yet; C3 user-initiated (never rule (c)))" in step_3_after(org)
    write_version(org, 3, [*v1, "One page", "Names its week"], initiated="user", words="Name the week.")  # C4
    assert f"{CLAUSE}none yet; C3, C4 user-initiated (never rule (c)))" in step_3_after(org)
    amend_legacy(org, add_acceptance=["Quote the source"])  # C5: an amendment nobody confirmed
    assert f"{CLAUSE}none yet; C5 not confirmed yet; C3, C4 user-initiated (never rule (c)))" in step_3_after(org)
    c6 = confirmed_amendment(org, "Every figure names its date")
    assert f"{CLAUSE}now {c6} (an item may be the own words of it); C5 not confirmed yet; C3, C4 user-initiated (never rule (c)))" in step_3_after(org)


def test_step_3_leaves_out_a_removed_amendment(svc):
    org = svc
    amend_legacy(org, add_acceptance=["Quote the source"])
    amend_legacy(org, remove_acceptance=["Quote the source"])
    assert f"{CLAUSE}none yet)" in step_3_after(org)


def test_the_reject_preamble_speaks_of_rules_without_client_evidence(svc):
    org = svc
    first = request(org, "ai")
    deliver(org, "ceo", first, lessons="Thin on sources.")
    org.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    request(org, "chips")
    section = reflect_section(org.run_prompt("ceo", org.begin_run("ceo")))
    assert "Without the client's evidence (step 3) a rejection is a reason to look, not to change an item" in section
    assert "Revise the playbook when step 3 admits it" not in section and "A rule without the client's evidence" not in section
    assert "One rejection is a reason to look" not in section and "Revise the playbook only as step 3 says" not in section


def test_step_3_for_an_agent_client_says_nothing_can_admit(svc):
    org = svc
    define(org, owner=ENG, actor="ceo", name="eng-brief")
    org.send(ROOT, "ceo", "Runs to hand down.", budget=20)
    first = org.request("ceo", "eng-brief", {"topic": "x"}, budget=3)
    deliver(org, ENG, first, lessons="Thin on sources.")
    org.request("ceo", "eng-brief", {"topic": "y"}, budget=3)
    section = reflect_section_of(org.run_prompt(ENG, org.begin_run(ENG)), "eng-brief")
    assert step_3(section) == (
        "3. Your client is an agent, so nothing can admit a change (only the first version): apply the evidence when you plan this request, and if "
        "you think the playbook must change, send your parent (`send`) what you would change and why."
    )
    assert "evidence" not in step_3(section).replace("evidence when", "")


def reflect_section_of(prompt, service):
    return prompt.split(f"# Reflect before you start: {service}")[1].split("# New messages")[0]


def test_no_playbook_texts_ask_for_the_steps_followed_only(svc):
    org = svc
    request(org)
    plain = org.run_prompt("ceo", org.begin_run("ceo"))
    assert (
        'No playbook yet: plan as usual; when you report this request, write v1 with revise_playbook(op="first", text=...): the steps your team '
        "followed, nothing more (no evidence needed, and only until the client's first verdict or rework; after that, op=\"add\" with the "
        "client's evidence)."
    ) in plain
    org.end_run("ceo", ok=True)
    locked = "No playbook yet, and the contract is locked: plan as usual."
    define(org, name="locked-brief", locked=True)
    org.request(ROOT, "locked-brief", {"topic": "ai"})
    assert locked in org.run_prompt("ceo", org.begin_run("ceo"))  # the locked text is unchanged


# ------------------------------------------------------------------------------------------ the regression list
LIST_HEADER = "# Regression list: weekly-brief (the client's rejections, verbatim)"
OLDER = "- {n} older line(s) not shown: `services` lists them all."


def reject(org, words, topic="ai", **kw):
    """The user rejects a delivery with ``words`` (their own judgement: ``source="human"``); returns the request and the verdict note. A
    ``criterion`` is the user's yes: it is recorded as a ``confirms`` link after the verdict (on the verdict itself it would be relayed tier)."""
    task = request(org, topic)
    deliver(org, "ceo", task, lessons="L.")
    criterion = kw.pop("criterion", None)
    note = org.feedback(ROOT, task.id, "reject", words, source="human", **kw)
    if criterion:
        org.feedback(ROOT, task.id, "reject", "Yes, it is about that.", source="human", criterion=criterion, confirms=note.id)
    return task, note


def regression_list(prompt):
    return prompt.split(LIST_HEADER)[1].split("\n# ")[0]


def lines_of(prompt):
    return [line for line in regression_list(prompt).splitlines() if line.startswith("- ")]


def test_the_regression_list_follows_the_playbook_section(svc):
    org = svc
    first, note = reject(org, "Too long.")
    request(org, "chips")  # a new request: the playbook section, then the list, then the reflection
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert prompt.index("# Playbook: weekly-brief") < prompt.index(LIST_HEADER) < prompt.index("# Reflect before you start")
    assert f"\n{LIST_HEADER}\n" in prompt
    section = LIST_HEADER + regression_list(prompt)
    assert section.splitlines()[1] == (
        'Each line is something the client rejected. Check every delivery of this service against each line, except the lines marked "no '
        'lasting rule" (the client said it was a one-off: do not check them), and copy this list verbatim into every review or check task you '
        'delegate for it. A line is not a criterion: it becomes one when your parent adds it to the contract, or ends as "no lasting rule".'
    )
    assert section.splitlines()[2] == f'- R1, case {first.id}, verdict {note.id}: "Too long."'
    org.end_run("ceo", ok=True)


def test_the_regression_list_comes_before_reflect_when_only_reflect_is_shown(svc):
    org = svc
    first, note = reject(org, "Too long.")  # delivered: no open request, so no playbook section; the rejection alone brings the reflection
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Playbook: weekly-brief" not in prompt and "# Reflect before you start: weekly-brief" in prompt
    assert prompt.index(LIST_HEADER) < prompt.index("# Reflect before you start: weekly-brief")
    assert f'\n{LIST_HEADER}\n' in prompt and prompt.split("# Reflect before you start")[0].rstrip().endswith('"Too long."')
    org.end_run("ceo", ok=True)


def test_no_regression_list_for_a_non_owner_or_an_empty_list(svc):
    org = svc
    first = request(org, "ai")
    deliver(org, "ceo", first, lessons="L.")
    org.feedback(ROOT, first.id, "accept", "good", source="human")  # an accept is no assertion
    request(org, "chips")
    assert "# Regression list" not in org.run_prompt("ceo", org.begin_run("ceo"))
    org.end_run("ceo", ok=True)
    task = request(org, "relayed")
    deliver(org, "ceo", task, lessons="L.")
    org.feedback(ROOT, task.id, "reject", "The assistant finds it long.", source="relayed")  # nor is the assistant's own reading
    assert "# Regression list" not in org.run_prompt("ceo", org.begin_run("ceo"))
    org.end_run("ceo", ok=True)
    reject(org, "Too long.", "again")  # now there is an assertion, but only the owner is shown it
    assert org.runtime.service_prompt_sections.prompt_sections(ENG, []) == ""
    assert LIST_HEADER in org.runtime.service_prompt_sections.prompt_sections("ceo", org.begin_run("ceo"))
    org.end_run("ceo", ok=True)


def test_the_list_is_cut_to_the_newest_12_with_the_older_line_first(svc):
    org = svc
    for k in range(13):
        reject(org, f"Problem {k + 1}.", f"t{k}")
    request(org, "next")
    lines = lines_of(org.run_prompt("ceo", org.begin_run("ceo")))
    assert len(lines) == 13 and lines[0] == OLDER.format(n=1)
    assert [line.split(",")[0] for line in lines[1:]] == [f"- R{k}" for k in range(2, 14)]  # newest last, ids ascend
    assert lines[-1].endswith('"Problem 13."')
    org.end_run("ceo", ok=True)


def test_regression_lines_carry_their_own_assertion_ids(svc):
    org = svc
    (t1, n1), (t2, n2) = reject(org, "Too long.", "a"), reject(org, "Wrong week.", "b")
    request(org, "next")
    lines = lines_of(org.run_prompt("ceo", org.begin_run("ceo")))
    assert lines == [f'- R1, case {t1.id}, verdict {n1.id}: "Too long."', f'- R2, case {t2.id}, verdict {n2.id}: "Wrong week."']
    assert all(line.startswith(f"- R{k}, case ") for k, line in enumerate(lines, 1))
    org.end_run("ceo", ok=True)
    for k in range(11):  # 13 assertions: the older line first, then R2..R13
        reject(org, f"More {k}.", f"m{k}")
    request(org, "again")
    lines = lines_of(org.run_prompt("ceo", org.begin_run("ceo")))
    assert lines[0] == OLDER.format(n=1) and lines[1].startswith("- R2, case ") and lines[-1].startswith("- R13, case ")


def test_the_words_of_a_line_are_cut_to_300_characters(svc):
    org = svc
    reject(org, "w" * 400)
    request(org, "next")
    (line,) = lines_of(org.run_prompt("ceo", org.begin_run("ceo")))
    assert line.endswith(': "' + "w" * 299 + '…"')
    org.end_run("ceo", ok=True)


def test_a_no_lasting_rule_line_says_do_not_check_it(svc):
    org = svc
    first, note = reject(org, "Only this once.", criterion=["none"])
    request(org, "next")
    (line,) = lines_of(org.run_prompt("ceo", org.begin_run("ceo")))
    assert line == f'- R1, case {first.id}, verdict {note.id}, no lasting rule (the client said so): do not check it: "Only this once."'
    org.end_run("ceo", ok=True)


def test_unconfirmed_links_say_not_confirmed_by_the_client(svc):
    org = svc
    first, note = reject(org, "Too long.")
    second, other = reject(org, "Rambling.", "b")
    third, last = reject(org, "Three.", "c")
    org.feedback(ROOT, first.id, "reject", "Probably.", source="relayed", criterion=["C1"], confirms=note.id)  # the assistant's reading of R1
    org.feedback(ROOT, second.id, "reject", "Probably.", source="relayed", criterion=["none"], confirms=other.id)  # "a one-off", said by the assistant
    request(org, "next")
    lines = lines_of(org.run_prompt("ceo", org.begin_run("ceo")))
    assert lines[0] == f'- R1, case {first.id}, verdict {note.id}, about C1 (not confirmed by the client): "Too long."'
    assert lines[1] == f'- R2, case {second.id}, verdict {other.id}, possibly a one-off (not confirmed by the client): "Rambling."'
    assert lines[2] == f'- R3, case {third.id}, verdict {last.id}: "Three."'
    org.end_run("ceo", ok=True)


def test_a_confirmed_link_names_its_criteria(svc):
    org = svc
    first, note = reject(org, "Too long.", criterion=["C1", "C2"])
    request(org, "next")
    (line,) = lines_of(org.run_prompt("ceo", org.begin_run("ceo")))
    assert line == f'- R1, case {first.id}, verdict {note.id}, about C1, C2: "Too long."'
    org.end_run("ceo", ok=True)


def test_the_regression_line_marks_a_removed_criterion(svc):
    org = svc
    first, note = reject(org, "Too long.", criterion=["C1", "C2"])
    amend_legacy(org, add_acceptance=["One page"], remove_acceptance=["Every factual claim has a source URL"])
    request(org, "next")
    (line,) = lines_of(org.run_prompt("ceo", org.begin_run("ceo")))
    assert line == f'- R1, case {first.id}, verdict {note.id}, about C1, C2 (removed): "Too long."'
    org.end_run("ceo", ok=True)


# ------------------------------------------------------------------------------------------ the tier-aware Reflect texts
HUMAN_LEAD = (
    "The client rejected a delivery: check it against their words, the regression list and the contract before you plan the request. Without the "
    "client's evidence (step 3) a rejection is a reason to look, not to change an item: your parent asks the client whether it is a lasting "
    "requirement, and the answer reaches you as a contract change or a criterion link."
)
RELAYED_LEAD = (
    "A relayed rejection arrived (the assistant's own reading, not the client's words): apply what it asks in this request where the contract "
    "allows it; it is not the client's evidence, so it cannot change the playbook (step 3). Then handle the request."
)
AGENT_LEAD = (
    "Your client, an agent, rejected a delivery (its verdict is a hypothesis): apply what it asks in this request where the contract allows "
    "it; it is not the client's evidence, so it cannot change the playbook (step 3). Then handle the request."
)
LOCKED_END = ". The contract is locked, so you cannot change the playbook: apply what the feedback shows, then handle the request."
UNLOCKED_RAISE_BAR = (
    "The playbook may raise the bar, never lower it: the acceptance criteria come from the contract and travel with every request. Your parent "
    "asks the client whether a rejection is a lasting requirement: send nothing about it yourself beyond a refused change's question (step 3)."
)
LOCKED_RAISE_BAR = (
    "The playbook may raise the bar, never lower it: the acceptance criteria come from the contract and travel with every request. Your parent "
    "asks the client whether a rejection is a lasting requirement; do not send it yourself."
)
AGENT_RAISE_BAR = (
    "The playbook may raise the bar, never lower it: the acceptance criteria come from the contract and travel with every request. If the "
    "client's feedback is a lasting requirement, also tell your parent (`send`) so it can add it to the contract."
)


def rejected_then_new(org, source="human", name="weekly-brief"):
    """The client rejects a delivery (``source``) and asks again; returns the owner's Reflect section for the new request."""
    first = request(org, "ai")
    deliver(org, "ceo", first, lessons="Thin on sources.")
    org.feedback(ROOT, first.id, "reject", "Too long.", source=source)
    request(org, "chips")
    return reflect_section_of(org.run_prompt("ceo", org.begin_run("ceo")), name)


def numbered(section, n):
    return next(line for line in section.splitlines() if line.startswith(f"{n}. "))


def agent_client_section(org, locked=False):
    define(org, owner=ENG, actor="ceo", name="eng-brief", locked=locked)
    org.send(ROOT, "ceo", "Runs to hand down.", budget=20)
    first = org.request("ceo", "eng-brief", {"topic": "x"}, budget=3)
    deliver(org, ENG, first, lessons="Thin on sources.")
    org.feedback("ceo", first.id, "reject", "Too long.")
    org.request("ceo", "eng-brief", {"topic": "y"}, budget=3)
    return reflect_section_of(org.run_prompt(ENG, org.begin_run(ENG)), "eng-brief")


def test_the_human_lead_says_one_rejection_is_a_reason_to_look(svc):
    section = rejected_then_new(svc)
    assert HUMAN_LEAD in section.splitlines() and "decide now whether the playbook must change" not in section


def test_the_relayed_lead_says_it_cannot_change_the_playbook(svc):
    section = rejected_then_new(svc, source="relayed")
    assert RELAYED_LEAD in section.splitlines() and "The client rejected a delivery" not in section


def test_the_agent_lead_says_the_verdict_is_a_hypothesis(svc):
    assert AGENT_LEAD in agent_client_section(svc).splitlines()


def test_the_locked_lead_keeps_its_text_with_the_new_subject(svc):
    define(svc, name="locked-brief", locked=True)
    first = svc.request(ROOT, "locked-brief", {"topic": "ai"})
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    request_unheld(svc, "again", name="locked-brief")
    lines = reflect_section_of(svc.run_prompt("ceo", svc.begin_run("ceo")), "locked-brief").splitlines()
    assert "The client rejected a delivery" + LOCKED_END in lines
    svc.end_run("ceo", ok=True)
    second = svc.request(ROOT, "locked-brief", {"topic": "more"})
    deliver(svc, "ceo", second)
    svc.feedback(ROOT, second.id, "reject", "Wrong.", source="relayed")
    svc.request(ROOT, "locked-brief", {"topic": "last"})
    section = reflect_section_of(svc.run_prompt("ceo", svc.begin_run("ceo")), "locked-brief")
    assert "A relayed rejection arrived (the assistant's own reading, not the client's words)" + LOCKED_END in section.splitlines()


def test_step_1_names_the_regression_list_except_for_an_agent_client(svc):
    tail = ". A rejection or a failure is enough to look into on its own; a single slow case is not."
    human = rejected_then_new(svc)
    assert "1. Look for what repeats, and for anything the client rejected (the regression list)" + tail in human.splitlines()
    assert "1. Look for what repeats, and for anything the client rejected" + tail in agent_client_section(svc).splitlines()


def test_step_2_unlocked_and_locked_texts(svc):
    unlocked = rejected_then_new(svc)
    assert (
        "2. When a lesson of yours conflicts with the client's own feedback (not a relayed verdict), the client is right: apply the feedback in "
        "this request."
    ) in unlocked.splitlines()
    locked = agent_client_section(svc, locked=True)
    assert (
        "2. When a lesson of yours conflicts with the client's own feedback (not a relayed verdict), the client is right: follow the feedback."
    ) in locked.splitlines()


def test_raise_bar_for_a_human_client_unlocked_allows_only_the_refusal_question(svc):
    section = rejected_then_new(svc)
    assert UNLOCKED_RAISE_BAR in numbered(section, 4) and "do not send it yourself" not in section


def test_raise_bar_for_a_human_client_locked_says_do_not_send_it_yourself(svc):
    define(svc, name="locked-brief", locked=True)
    first = svc.request(ROOT, "locked-brief", {"topic": "ai"})
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    request_unheld(svc, "again", name="locked-brief")
    section = reflect_section_of(svc.run_prompt("ceo", svc.begin_run("ceo")), "locked-brief")
    assert LOCKED_RAISE_BAR in section and "send nothing about it yourself" not in section


def test_raise_bar_for_an_agent_client_is_unchanged(svc):
    section = agent_client_section(svc)
    assert AGENT_RAISE_BAR in numbered(section, 4) and "do not send it yourself" not in section


# ------------------------------------------------------------------------------------------ D-E7-2 F-E7-8: a blocked request the client has not moved past is still working
def blocked_after_a_rejection(org):
    """The client rejected a delivery (R1, read in an earlier run), then asked again; the owner reported that request ``blocked``. Returns that request."""
    first = request(org, "ai")
    deliver(org, "ceo", first, lessons="Fine.")
    org.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    second = request(org, "chips")
    deliver(org, "ceo", second, status="blocked", lessons="Waiting on the client.")
    return second


def test_a_blocked_request_with_only_a_grant_in_the_batch_keeps_its_playbook_and_regression_list(svc):
    """F-E7-8 (E7 s1, runs after the lead's blocked report): the batch holds only the grant note, and the request is blocked, not answered."""
    org = svc
    second = blocked_after_a_rejection(org)
    org.send(ROOT, "ceo", "Three more runs.", reply_to=second.id, budget=3)
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Playbook: weekly-brief (" in prompt
    assert "# Regression list: weekly-brief (the client's rejections, verbatim)" in prompt
    assert "# Reflect" not in prompt  # no new request and no rejection in the batch
    assert prompt.index("# Your services") < prompt.index("# Playbook: weekly-brief") < prompt.index("# Regression list: weekly-brief")
    org.end_run("ceo", ok=True)


def test_a_blocked_request_the_client_accepted_after_the_block_leaves_the_listing_alone(svc):
    org = svc
    second = blocked_after_a_rejection(org)
    org.feedback(ROOT, second.id, "accept", "Fine.", source="human")  # the client moved past the blocked request
    org.send(ROOT, "ceo", "Three more runs.", reply_to=second.id, budget=3)
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Your services" in prompt and "# Playbook" not in prompt and "# Regression list" not in prompt and "# Reflect" not in prompt
    org.end_run("ceo", ok=True)


def test_a_rejection_in_the_batch_with_a_blocked_request_held_gives_playbook_regression_list_and_reflect_in_that_order(svc):
    """F-E7-8 (design 7.4): the rejection is of another case; the blocked request is not moved past, so the service is still being worked on."""
    org = svc
    first = request(org, "ai")
    deliver(org, "ceo", first, lessons="Thin on sources.")
    second = request(org, "chips")
    deliver(org, "ceo", second, status="blocked", lessons="Waiting on the client.")
    org.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    order = [prompt.index(h) for h in ("# Playbook: weekly-brief", "# Regression list: weekly-brief", "# Reflect before you start: weekly-brief")]
    assert order == sorted(order) and prompt.count("# Playbook: weekly-brief") == 1
    org.end_run("ceo", ok=True)


# ------------------------------------------------------------------------------------------ 14.1: the items and their watch states
# These tests build ``QuotedPlaybookSection`` over a ``ReflectionWorld`` (the services, the mail and the settings of one organization) with a stand-in
# for the watch, so that each state is one value of ``ItemWatch`` and not a story of verdicts (the stories are FEAT-010's).
import dataclasses  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from hirearchy.kernel import OrgError  # noqa: E402
from hirearchy.reflection._sections import QuotedPlaybookSection  # noqa: E402
from hirearchy.reflection.testing import ReflectionWorld, fs_world  # noqa: E402
from hirearchy.services import AmendmentBasis, ItemWatch, Rejection  # noqa: E402
from hirearchy.services.testing import AdmittingServiceEvidence  # noqa: E402

from . import _support as sup  # noqa: E402

STATES = "Item states: "


@pytest.fixture
def pw(tmp_path: Path) -> ReflectionWorld:
    """A world where ``ceo`` owns ``weekly-brief`` with playbook v1 (``first``: P1-P3, steps under ``## Steps``)."""
    w = sup.populated(fs_world(tmp_path))
    sup.define(w)
    sup.first_playbook(w, sup.STEPS)
    return w


def kept(*ids, kind="step", version=1):
    return [ItemWatch(i, kind, "kept", version) for i in ids]


def section_of(w, watch, *, basis=None, locked=False, evidence=None, reflecting=False):
    """The playbook section for ``ceo``'s ``weekly-brief`` over a stand-in watch (``evidence`` replaces the stand-in)."""
    evidence = evidence or AdmittingServiceEvidence(basis=basis, watch=watch)
    contract = w.s.catalog.read_contract("ceo", sup.SERVICE)
    if locked:
        contract = dataclasses.replace(contract, locked=True)
    return QuotedPlaybookSection(w.s.catalog, w.s.d.settings, w.paths, evidence).section("ceo", contract, reflecting=reflecting)


def states_line(text):
    lines = [x for x in text.splitlines() if x.startswith(STATES) or x.startswith("Playbook v") or x.startswith("Item states")]
    assert len(lines) == 1, text
    return lines[0]


def test_the_states_line_names_ids_states_versions_and_rejections_only(pw):
    pw.s.commands.revise_playbook("ceo", sup.SERVICE, "add", "a rule", ["R1"], kind="rule", when="the date is missing", then="ask for it")
    watch = [*kept("P1", "P2", "P3"), ItemWatch("P4", "rule", "new", 2, k=3, clean=2, r=(0, 4))]
    text = section_of(pw, watch)
    head, *_ = text.splitlines()
    assert head == "# Playbook: weekly-brief (v2, yours to improve one item at a time; 16 of 1000 words)"
    assert "> ## Rules\n> - [P4] WHEN the date is missing THEN ask for it WHY R1" in text
    assert states_line(text) == (
        "Item states: P4 rule, new since v2 (watched: a related client rejection warns it, a second retires it). All other items: kept."
    )
    assert "clean" not in text and "2 of 3" not in text and " k " not in text  # agents see facts, not targets (08 P6)


def test_all_items_kept_is_one_short_line(pw):
    assert states_line(section_of(pw, kept("P1", "P2", "P3"))) == "Item states: all items kept."


def test_a_warning_names_its_rejection_its_case_and_the_text_it_restores(pw):
    pw.s.commands.revise_playbook("ceo", sup.SERVICE, "edit", "tighter", ["R1"], item="P2", text="Write it twice.")
    started = pw.s.catalog.read_playbook("ceo", sup.SERVICE).revised
    basis = AmendmentBasis((Rejection("n1", "R1", "t1", "x", (), "no", "", case="c-ask0"),), ())
    watch = [*kept("P1", "P3"), ItemWatch("P2", "step", "warning", 2, watch_start=started, related=("R1",))]
    assert states_line(section_of(pw, watch, basis=basis)) == (
        "Item states: P2 step, warning: rejection R1 (case c-ask0) is related; one more retires it and restores the text of v1. "
        "All other items: kept."
    )


def test_a_warning_without_an_earlier_text_does_not_promise_a_restore(pw):
    pw.s.commands.revise_playbook("ceo", sup.SERVICE, "add", "one more", ["R1"], kind="step", text="Send it.")
    started = pw.s.catalog.read_playbook("ceo", sup.SERVICE).revised
    basis = AmendmentBasis((Rejection("n1", "R1", "t1", "x", (), "no", "", case="c-ask0"),), ())
    watch = [*kept("P1", "P2", "P3"), ItemWatch("P4", "step", "warning", 2, watch_start=started, related=("R1",))]
    assert states_line(section_of(pw, watch, basis=basis)) == (
        "Item states: P4 step, warning: rejection R1 (case c-ask0) is related; one more retires it. All other items: kept."
    )


def test_waiting_for_the_clients_verdict_and_for_the_users_answer(pw):
    pw.s.commands.revise_playbook("ceo", sup.SERVICE, "add", "a rule", ["R1"], kind="rule", when="the date is missing", then="ask for it")
    one = [*kept("P1", "P2", "P3"), ItemWatch("P4", "rule", "new", 2, waiting=1)]
    assert "P4 rule, new since v2 (waiting for the client's verdict on 1 case)." in section_of(pw, one)
    two = [*kept("P1", "P2", "P3"), ItemWatch("P4", "rule", "new", 2, waiting=2)]
    assert "P4 rule, new since v2 (waiting for the client's verdict on 2 cases)." in section_of(pw, two)
    answer = [*kept("P1", "P2", "P3"), ItemWatch("P4", "rule", "new", 2, pending=("R4",))]
    assert "P4 rule, new since v2 (waiting for the user's answer to R4)." in section_of(pw, answer)
    both = [*kept("P1", "P2", "P3"), ItemWatch("P4", "rule", "new", 2, waiting=1, pending=("R4", "R5"))]
    assert "(waiting for the client's verdict on 1 case; waiting for the user's answer to R4, R5)." in section_of(pw, both)


def test_retire_due_and_its_locked_form(pw):
    watch = [*kept("P1", "P3"), ItemWatch("P2", "step", "warning", 1, related=("R4", "R6"), retire_due=True)]
    assert states_line(section_of(pw, watch)) == (
        "Item states: P2: retire due (R4, R6 are related): the runtime retires it at the next change; follow the contract. All other items: kept."
    )
    assert states_line(section_of(pw, watch, locked=True)) == (
        "Item states: P2: retire due (R4, R6 are related): the runtime retires it at the client's next answer; follow the contract. "
        "All other items: kept."
    )


def test_a_carried_watch_shows_its_old_id(pw):
    watch = [*kept("P1", "P2"), ItemWatch("P3", "step", "warning", 1, related=("R4",), carried="P9")]
    assert states_line(section_of(pw, watch)) == (
        "Item states: P3 step, warning (carried from P9): rejection R4 is related; one more retires it. All other items: kept."
    )
    new = [*kept("P1", "P2"), ItemWatch("P3", "step", "new", 1, carried="P9")]
    assert (
        "P3 step, new since v1 (carried from P9; watched: a related client rejection warns it, a second retires it)." in section_of(pw, new)
    )


def test_a_restored_text_is_named_as_such(pw):
    watch = [*kept("P1", "P3"), ItemWatch("P2", "step", "restored", 3, restores=1)]
    assert states_line(section_of(pw, watch)) == "Item states: P2 step, restored (the watch put back the text of v1). All other items: kept."


def test_every_item_listed_leaves_no_other_items_sentence(pw):
    watch = [ItemWatch(i, "step", "new", 1) for i in ("P1", "P2", "P3")]
    line = states_line(section_of(pw, watch))
    assert line.startswith("Item states: P1 step, new since v1 (") and line.endswith("retires it).") and "All other" not in line


def test_a_legacy_playbook_shows_its_future_ids(tmp_path):
    w = sup.populated(fs_world(tmp_path))
    sup.define(w)
    sup.legacy_playbook(w, "## Steps\n1. Search.\n2. Write.\n")
    sup.ask(w)
    text = w.sections.prompt_sections("ceo", [])
    playbook = text.split("# Playbook: weekly-brief")[1]
    assert playbook.startswith(" (v1, yours to improve one item at a time; 6 of 1000 words)\n> ## Steps\n> 1. [P1] Search.\n> 2. [P2] Write.\n")
    assert "\nItems get these ids when you first change one.\nItem states: all items kept." in playbook


def test_an_empty_item_list(pw):
    pw.s.commands.revise_playbook("ceo", sup.SERVICE, "retire", "no longer", [], item="P1")
    pw.s.commands.revise_playbook("ceo", sup.SERVICE, "retire", "no longer", [], item="P2")
    pw.s.commands.revise_playbook("ceo", sup.SERVICE, "retire", "no longer", [], item="P3")
    sup.ask(pw)
    playbook = pw.sections.prompt_sections("ceo", []).split("# Playbook: weekly-brief")[1]
    assert "\n> ## Steps\nPlaybook v4 has no items: add one (op=\"add\")." in playbook


def test_an_unparseable_file_quotes_the_raw_body_with_its_line(pw):
    meta, _ = pw.s.store.read_playbook("ceo", sup.SERVICE)
    pw.s.store.write_playbook("ceo", sup.SERVICE, 2, {**meta, "version": 2}, "## Steps\nnot an item line\n", 1)
    reason = pw.s.catalog.read_playbook("ceo", sup.SERVICE).parse_error
    assert reason.startswith("line ")
    sup.ask(pw)
    playbook = pw.sections.prompt_sections("ceo", []).split("# Playbook: weekly-brief")[1]
    assert "\n> ## Steps\n> not an item line\n" in playbook
    assert (
        f"Playbook v2 is not in item form ({reason}): your next change first turns its text into new items (no change of words)." in playbook
    )


def test_the_two_no_playbook_texts_for_op_first(svc):
    org = svc
    request(org)
    plain = org.run_prompt("ceo", org.begin_run("ceo"))
    assert (
        'No playbook yet: plan as usual; when you report this request, write v1 with revise_playbook(op="first", text=...): the steps your team '
        "followed, nothing more (no evidence needed, and only until the client's first verdict or rework; after that, op=\"add\" with the "
        "client's evidence)."
    ) in plain
    org.end_run("ceo", ok=True)
    first = request(org, "ai")
    deliver(org, "ceo", first, lessons="Thin on sources.")
    request(org, "chips")
    reflecting = org.run_prompt("ceo", org.begin_run("ceo"))
    assert (
        'No playbook yet: write v1 now from how the team works with revise_playbook(op="first", text=...) (Reflect before you start shows the '
        "evidence; rules from lessons or relayed verdicts are not steps), then follow it. The first version needs no evidence and is allowed "
        "only until the client's first verdict or rework; after that, add items one at a time (op=\"add\") with the client's evidence."
    ) in reflecting
    assert "evidence=[]" not in plain + reflecting


def test_a_failed_watch_read_says_item_states_could_not_be_read(pw):
    class Unreadable(AdmittingServiceEvidence):
        def watch(self, owner, service):
            raise OrgError("the mailbox of root cannot be read")

    text = section_of(pw, [], evidence=Unreadable())
    assert "> 1. [P1] Search." in text  # the body is still quoted
    assert states_line(text) == "Item states could not be read (the mailbox of root cannot be read); follow the contract where an item differs from it."


def test_a_locked_playbook_keeps_its_head_and_its_no_playbook_text(pw):
    text = section_of(pw, kept("P1", "P2", "P3"), locked=True)
    assert text.splitlines()[0] == "# Playbook: weekly-brief (v1, locked by your parent)"


# ------------------------------------------------------------------------------------------ 14.2 and 12: the Reflect section, one item at a time, in at most 600 words
from hirearchy.reflection import _sections  # noqa: E402
from hirearchy.reflection._sections import EvidenceReflectSection  # noqa: E402

INTRO = "Your playbook is how your team delivers this service; you own it and change it one item at a time. Evidence since v1:"
LEAD_HUMAN = (
    "The client rejected a delivery: check it against their words, the regression list and the contract before you plan the request. Without the "
    "client's evidence (step 3) a rejection is a reason to look, not to change an item: your parent asks the client whether it is a lasting "
    "requirement, and the answer reaches you as a contract change or a criterion link."
)
STEP_1 = (
    "1. Look for what repeats, and for anything the client rejected (the regression list). A rejection or a failure is enough to look into on "
    "its own; a single slow case is not."
)
STEP_2 = (
    "2. When a lesson of yours conflicts with the client's own feedback (not a relayed verdict), the client is right: apply the feedback in this request."
)
STEP_3 = (
    "3. If a change to how the team works would prevent it, change one item with `revise_playbook` (its description gives the ops). A rule, or a "
    "step that changes a check, an output or how a criterion is handled, needs evidence in `evidence`: the same criterion or assertion failed in 2 "
    "different cases the client rejected, or the item is the own words of a criterion the client confirmed (none yet). Lessons and relayed verdicts "
    "are not evidence. An admitted item is watched: a related client rejection warns it, a second retires it. Retiring or weakening an item that "
    "covers a criterion needs your parent's acknowledgement. If a change is refused, nothing is written: send your parent its question once and go on."
)
STEP_4 = (
    "4. The playbook may raise the bar, never lower it: the acceptance criteria come from the contract and travel with every request. Your parent "
    "asks the client whether a rejection is a lasting requirement: send nothing about it yourself beyond a refused change's question (step 3)."
)
STEP_5 = "5. If nothing needs to change, change nothing. Then handle the request following the playbook."


def test_the_reflect_text_word_for_word_for_a_human_unlocked_client(svc):
    svc.revise_playbook("ceo", "weekly-brief", "first", "one", [], text="## Steps\n1. Search.\n2. Write.")
    time.sleep(0.002)
    first = request(svc, "ai")
    deliver(svc, "ceo", first, lessons="Thin on sources.")
    svc.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    request(svc, "chips")
    section = reflect_section(svc.run_prompt("ceo", svc.begin_run("ceo")))
    lines = section.strip().splitlines()
    assert lines[0] == INTRO and lines[1].startswith("Cases with new evidence")
    assert lines[-6:] == [LEAD_HUMAN, STEP_1, STEP_2, STEP_3, STEP_4, STEP_5]
    assert "Warning:" not in section


def reflect_for(w, *, locked=False, agent=False, rejected="", new_request=True, watch=(), digest="", eligible=None):
    """The Reflect section over a stand-in watch for ``ceo``'s ``weekly-brief`` (or the agent client's ``eng-brief``), with ``digest`` as its text."""
    name, owner = ("eng-brief", "ceo/eng") if agent else (sup.SERVICE, "ceo")
    contract = w.s.catalog.read_contract(owner, name)
    if locked:
        contract = dataclasses.replace(contract, locked=True)
    evidence = AdmittingServiceEvidence(watch=watch)
    reflect = EvidenceReflectSection(w.s.catalog, w.s.d.settings, w.paths, w.history, evidence)
    return reflect.section(owner, contract, lambda words: digest, rejected=rejected, new_request=new_request)


@pytest.fixture
def rw(tmp_path):
    """A world with both services the Reflect section is built for: ``ceo``'s ``weekly-brief`` (client: the user) and ``ceo/eng``'s ``eng-brief``
    (client: ``ceo``, an agent), each with 7 criteria of every kind ``{eligible}`` lists and enough ids to need its ``+n more``."""
    w = sup.populated(fs_world(tmp_path))
    sup.define(w)
    w.s.d.post(sup_message_grant())
    sup.define(w, owner="ceo/eng", name="eng-brief", actor="ceo")
    return w


def sup_message_grant():
    from hirearchy.kernel import Message

    return Message(sender="root", to="ceo", type="note", body="runs for you", title="grant", budget=20)


def warning(*ids):
    return [ItemWatch(f"P{n}", "step", "warning", 1, related=(f"R{n}",)) for n in ids]


def test_the_warning_line_lists_at_most_5_items_then_n_more(rw):
    one = reflect_for(rw, watch=warning(12), rejected="human")
    assert "\nWarning: P12 (R12) has one related rejection; a second retires it.\n" in one
    two = reflect_for(rw, watch=warning(12, 13), rejected="human")
    assert "\nWarning: P12 (R12), P13 (R13) each have one related rejection; a second retires it.\n" in two
    five = reflect_for(rw, watch=warning(1, 2, 3, 4, 5))
    assert "\nWarning: P1 (R1), P2 (R2), P3 (R3), P4 (R4), P5 (R5) each have one related rejection; a second retires it.\n" in five
    seven = reflect_for(rw, watch=warning(1, 2, 3, 4, 5, 6, 7))
    assert "\nWarning: P1 (R1), P2 (R2), P3 (R3), P4 (R4), P5 (R5), +2 more each have one related rejection; a second retires it.\n" in seven
    assert "Warning:" not in reflect_for(rw, watch=[ItemWatch("P1", "step", "new", 1), ItemWatch("P2", "step", "kept", 1)])
    due = [ItemWatch("P1", "step", "warning", 1, related=("R1", "R2"), retire_due=True)]
    assert "Warning:" not in reflect_for(rw, watch=due)  # two related rejections: not "one related rejection"
    assert reflect_for(rw, watch=warning(3)).index("Warning:") < reflect_for(rw, watch=warning(3)).index("1. Look for")


def test_the_warning_line_is_left_out_when_the_watch_cannot_be_read(rw):
    class Unreadable(AdmittingServiceEvidence):
        def watch(self, owner, service):
            raise OrgError("the mailbox of root cannot be read")

    contract = rw.s.catalog.read_contract("ceo", sup.SERVICE)
    text = EvidenceReflectSection(rw.s.catalog, rw.s.d.settings, rw.paths, rw.history, Unreadable()).section("ceo", contract, lambda words: "D")
    assert "Warning:" not in text and "3. If a change" in text


def words_of(text):
    return len(text.split())


def longest_eligible(w):
    """Six criteria of every kind ``{eligible}`` lists, so that each of its three lists is cut at 5 ids and ends with ``+1 more``: C3-C8 added by an
    amendment the client confirmed, C9-C14 added by amendments nobody confirmed, C15-C20 the user's own."""
    def criteria_text(extra):
        meta, _ = w.s.store.read_contract("ceo", sup.SERVICE)
        return [*meta["acceptance"], *extra]

    for n in range(6):  # confirmed: the amendment, then a case the client rejected and the user's yes on it
        sup.amend_legacy(w, add_acceptance=[f"Confirmed rule {n}"])
        added = next(c.id for c in reversed(w.s.catalog.criteria("ceo", sup.SERVICE)) if c.text == f"Confirmed rule {n}" and c.current)
        task = sup.ask(w, f"confirmed {n}")
        sup.deliver(w, task)
        no = sup.note_on(w, task, verdict="reject", source="human", body=f"Missing: {n}")
        sup.note_on(w, task, reply_to=no.id, source="human", criterion=added)
    for n in range(6):
        sup.amend_legacy(w, add_acceptance=[f"Unconfirmed rule {n}"])
    meta, body = w.s.store.read_contract("ceo", sup.SERVICE)
    version = int(meta["version"]) + 1
    w.s.store.write_contract(
        "ceo", sup.SERVICE,
        {**meta, "version": version, "acceptance": criteria_text([f"The user's own rule {n}" for n in range(6)]), "defined_by": "root",
         "defined": w.s.d.clock.now().isoformat(timespec="microseconds"), "initiated": "user", "words": "Add these."},
        body, version - 1,
    )
    return w.evidence


def test_the_fixed_text_is_at_most_400_words_in_every_variant_at_its_longest(rw):
    from itertools import product

    longest_eligible(rw)
    contract = rw.s.catalog.read_contract("ceo", sup.SERVICE)
    clause = EvidenceReflectSection(rw.s.catalog, rw.s.d.settings, rw.paths, rw.history, AdmittingServiceEvidence())._eligible("ceo", contract.name)
    assert clause.count("+1 more") == 3 and clause.startswith("now C3, C4, C5, C6, C7, +1 more (an item may be the own words of one); C9")
    watch = warning(10, 11, 12, 13, 14, 15, 16)
    longest = checked = 0
    for locked, agent, rejected, new, warned in product((False, True), (False, True), ("", "human", "relayed", "agent"), (True, False), (False, True)):
        text = reflect_for(rw, locked=locked, agent=agent, rejected=rejected, new_request=new, watch=watch if warned else ())
        n = words_of(text)
        longest = max(longest, n)
        checked += 1
        assert n <= _sections.REFLECT_FIXED_WORDS, (locked, agent, rejected, new, warned, n)
    assert checked == 64 and _sections.REFLECT_FIXED_WORDS == 400 and _sections.REFLECT_WORDS == 600
    assert longest > 350  # the bound is measured on the real texts at their longest, not on empty ones


def test_each_id_list_of_the_fixed_text_is_cut_at_5_ids():
    assert _sections.eligible_clause([], [], []) == "none yet"
    assert _sections.eligible_clause(["C3"], [], []) == "now C3 (an item may be the own words of it)"
    assert _sections.eligible_clause(["C3", "C4"], ["C5"], ["C6", "C7"]) == (
        "now C3, C4 (an item may be the own words of one); C5 not confirmed yet; C6, C7 user-initiated (never rule (c))"
    )
    assert _sections.eligible_clause([], ["C5"], []) == "none yet; C5 not confirmed yet"
    ids = [f"C{n}" for n in range(3, 15)]
    assert _sections.eligible_clause(ids, [], []) == "now C3, C4, C5, C6, C7, +7 more (an item may be the own words of one)"


def test_the_whole_section_is_at_most_600_words(tmp_path):
    w = sup.populated(fs_world(tmp_path))
    story = wordy_cases(w)
    sup.ask(w, "open")
    text = w.sections.prompt_sections("ceo", w.s.d.inbox("ceo"))
    section = text.split("# Reflect before you start: weekly-brief")[1].split("\n# ")[0]
    assert words_of(section) <= _sections.REFLECT_WORDS
    assert len(story.asks) == 8 and "- case " in section  # the digest keeps at least one case


def wordy_cases(w):
    """Eight delivered cases whose lessons are about 60 words each: the digest alone would run to about 450 words."""
    from . import _stories

    sup.define(w)
    story = _stories.Story()
    for i in range(8):
        task = sup.ask(w, f"topic {i}")
        story.asks.append(task)
        story.results.append(sup.deliver(w, task, runs=1, lessons=" ".join(f"w{i}x{k}" for k in range(60))))
        w.s.d.clock.advance(1)
    return story


def test_todays_step_5_whole_version_restore_is_gone(rw):
    sup.first_playbook(rw, sup.STEPS)
    sup.add_step(rw, "More.")
    text = reflect_for(rw)
    assert "restore" not in text and "history/PLAYBOOK.v<k>.md" not in text
    assert [x[:2] for x in text.splitlines() if x[:1].isdigit()] == ["1.", "2.", "3.", "4.", "5."]
