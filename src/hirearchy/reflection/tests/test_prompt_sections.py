# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import time

from testkit.reach.hirearchy.core import ROOT
from testkit.services_world import ENG, amend_legacy, confirmed_amendment, define, deliver, request, svc, work, write_version

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
           "in this rework, and change the playbook only as step 3 says (say so in the reason)." in section
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
    assert "The client rejected a delivery: check the delivery against its words" in section and "then handle the request." in section
    assert section.rstrip().endswith("Then handle the request following the playbook.")


def test_the_client_wins_step_is_in_every_reflect_section(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    request(svc, "chips")
    section = reflect_section(svc.run_prompt("ceo", svc.begin_run("ceo")))
    assert "the client is right: apply the feedback in this request, and change the playbook only as step 3 says (say so in the reason)" in section
    assert [line[:2] for line in section.splitlines() if line[:1].isdigit()][:2] == ["1.", "2."]


def test_a_locked_service_reflects_on_a_rejection_without_revising(svc):
    define(svc, name="locked-brief", owner="ceo", locked=True, description="Locked brief.")
    first = svc.request(ROOT, "locked-brief", {"topic": "ai"})
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    svc.request(ROOT, "locked-brief", {"topic": "ai"}, revises=first.id, budget=3)
    section = svc.run_prompt("ceo", svc.begin_run("ceo")).split("# Reflect before you start: locked-brief")[1].split("# New messages")[0]
    assert "The client rejected a delivery. The contract is locked, so you cannot revise the playbook" in section
    assert "call `revise_playbook" not in section and "the client is right: follow the feedback" in section


def test_a_playbook_revised_after_the_rejection_leaves_no_reflect_section(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first)
    svc.feedback(ROOT, first.id, "reject", "Too long.")
    time.sleep(0.002)
    svc.revise_playbook("ceo", WEEKDAY, "Steps.", "after the rejection", [])
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
    assert (
        "No playbook yet: write v1 now from how the team works (Reflect before you start shows the evidence; rules from lessons or relayed "
        "verdicts are not steps), then follow it (the first version needs no evidence: evidence=[])."
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
    assert "revise_playbook(service, content, reason, evidence)" in section and "at most 1000 words" in section
    assert "A rejection or a failure is enough to look into on its own" in section and "never lower it" in section
    assert "restore" not in section  # nothing earlier to restore at v0
    assert section.rstrip().endswith("Then handle the request following the playbook.")
    assert [line[:2] for line in section.splitlines() if line[:1].isdigit()] == ["1.", "2.", "3.", "4.", "5."]
    assert prompt.index("# Reflect before") < prompt.index("# New messages") < prompt.index(new.id, prompt.index("# New messages"))
    org.end_run("ceo", ok=True)


def test_the_reflect_section_offers_restoring_an_older_version_from_v2_on(svc):
    org = svc
    org.revise_playbook("ceo", "weekly-brief", "Steps one.", "first", [])
    c3 = confirmed_amendment(org, "Every claim names its source")  # the user's amendment and their yes: the evidence of v2
    org.revise_playbook("ceo", "weekly-brief", "Steps one.\n- C3: Every claim names its source", "second", [c3])
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
    rework = request(org, revises=first.id, budget=3)  # not a NEW request
    prompt = org.run_prompt("ceo", org.begin_run("ceo"))
    assert "# Reflect" not in prompt and "# Playbook: weekly-brief" in prompt
    org.end_run("ceo", ok=True)
    deliver(org, "ceo", rework)
    org.revise_playbook("ceo", "weekly-brief", "Steps.", "after the rework", [])
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
    assert step_3(section) == (
        "3. If a change to how the team works would prevent it, call `revise_playbook(service, content, reason, evidence)` with the whole new "
        "playbook (at most 1000 words): concrete steps (who does what, in which order, which check), not slogans. Name the cases in the reason, "
        "and list in `evidence` what it rests on: regression assertions (R<k>), criteria (C<k>), verdict or case ids. It is admitted only when "
        "the same criterion or assertion failed in 2 different cases the client rejected (then every line it adds or changes carries that id, "
        'e.g. "[C6]"), or when it cites a criterion your parent added to the contract by an amendment the client confirmed (none yet): then it '
        'may add only that criterion\'s own words, one line each, "- C<k>: <its text>". A link note id counts as its criterion. Your lessons and '
        "relayed verdicts (the assistant's own reading) are not evidence. If it is refused, nothing is "
        "written: send your parent the refusal's question once and go on with the playbook as it is. The new version applies to this request."
    )


def test_step_3_says_lines_carry_their_id_or_are_the_criterions_words(svc):
    first = request(svc, "ai")
    deliver(svc, "ceo", first, lessons="Thin on sources.")
    request(svc, "chips")
    step = step_3(reflect_section(svc.run_prompt("ceo", svc.begin_run("ceo"))))
    assert 'failed in 2 different cases the client rejected (then every line it adds or changes carries that id, e.g. "[C6]"), or when' in step
    assert 'then it may add only that criterion\'s own words, one line each, "- C<k>: <its text>". A link note id counts as its criterion. ' in step
    assert "Your lessons and relayed verdicts (the assistant's own reading) are not evidence. If it is refused" in step


def step_3_after(org):
    """The owner's step 3 for a new request, once the user has rejected a delivery (``org`` may already hold amendments)."""
    first = request(org, "first")
    deliver(org, "ceo", first, lessons="Thin on sources.")
    org.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    request(org, "next")
    return step_3(reflect_section(org.run_prompt("ceo", org.begin_run("ceo"))))


CLAUSE = "contract by an amendment the client confirmed ("


def test_step_3_names_the_confirmed_amendments(svc):
    org = svc
    assert f"{CLAUSE}none yet):" in step_3_after(org)  # no amendment at all
    assert "are not confirmed" not in step_3_after(org) and "is not confirmed" not in step_3_after(org)


def test_step_3_names_one_confirmed_amendment(svc):
    org = svc
    c3 = confirmed_amendment(org, "Every claim names its source")
    assert f"{CLAUSE}now {c3}: a revision citing it may add its words):" in step_3_after(org)


def test_step_3_names_several_confirmed_amendments(svc):
    org = svc
    c3 = confirmed_amendment(org, "Every claim names its source", topic="one")
    c4 = confirmed_amendment(org, "Every figure names its date", topic="two")
    assert f"{CLAUSE}now {c3}, {c4}: a revision citing one of them may add its words):" in step_3_after(org)


def test_step_3_says_which_amendments_are_not_confirmed_yet(svc):
    org = svc
    amend_legacy(org, add_acceptance=["Quote the source"])  # an amendment nobody confirmed: C3
    assert f"{CLAUSE}none yet; C3 is not confirmed yet):" in step_3_after(org)
    c4 = confirmed_amendment(org, "Every claim names its source")
    amend_legacy(org, add_acceptance=["Quote the date"])
    assert f"{CLAUSE}now {c4}: a revision citing it may add its words; C3, C5 are not confirmed yet):" in step_3_after(org)


def test_eligible_ids_say_may_add_its_words(svc):
    """One id, several, none yet, and the unconfirmed ones appended (``_eligible``)."""
    org = svc
    assert f"{CLAUSE}none yet):" in step_3_after(org)
    c3 = confirmed_amendment(org, "Every claim names its source", topic="one")
    assert f"{CLAUSE}now {c3}: a revision citing it may add its words):" in step_3_after(org)
    c4 = confirmed_amendment(org, "Every figure names its date", topic="two")
    assert f"{CLAUSE}now {c3}, {c4}: a revision citing one of them may add its words):" in step_3_after(org)
    amend_legacy(org, add_acceptance=["Quote the source"])  # C5: nobody confirmed it
    amend_legacy(org, add_acceptance=["Quote the date"])  # C6
    assert f"{CLAUSE}now {c3}, {c4}: a revision citing one of them may add its words; C5, C6 are not confirmed yet):" in step_3_after(org)


def test_eligible_names_user_initiated_ids_as_never_admitted(svc):
    """A change the user asked for on their own is named apart from the unconfirmed ones: it never counts (``_eligible``)."""
    org = svc
    v1 = ["At most 600 words", "Every factual claim has a source URL"]
    write_version(org, 2, [*v1, "One page"], initiated="user", words="Keep it to one page.")  # C3
    assert f"{CLAUSE}none yet; C3 is user-initiated (rule (c) never admits it)):" in step_3_after(org)
    write_version(org, 3, [*v1, "One page", "Names its week"], initiated="user", words="Name the week.")  # C4
    assert f"{CLAUSE}none yet; C3, C4 are user-initiated (rule (c) never admits them)):" in step_3_after(org)
    amend_legacy(org, add_acceptance=["Quote the source"])  # C5: an amendment nobody confirmed
    assert f"{CLAUSE}none yet; C5 is not confirmed yet; C3, C4 are user-initiated (rule (c) never admits them)):" in step_3_after(org)
    c6 = confirmed_amendment(org, "Every figure names its date")
    assert f"{CLAUSE}now {c6}: a revision citing it may add its words; C5 is not confirmed yet; C3, C4 are user-initiated (rule (c) never admits them)):" in step_3_after(org)


def test_step_3_leaves_out_a_removed_amendment(svc):
    org = svc
    amend_legacy(org, add_acceptance=["Quote the source"])
    amend_legacy(org, remove_acceptance=["Quote the source"])
    assert f"{CLAUSE}none yet):" in step_3_after(org)


def test_the_reject_preamble_speaks_of_rules_without_client_evidence(svc):
    org = svc
    first = request(org, "ai")
    deliver(org, "ceo", first, lessons="Thin on sources.")
    org.feedback(ROOT, first.id, "reject", "Too long.", source="human")
    request(org, "chips")
    section = reflect_section(org.run_prompt("ceo", org.begin_run("ceo")))
    assert "A rule without the client's evidence (step 3) is a reason to look, not to change how the team works" in section
    assert "Revise the playbook when step 3 admits it, then handle the request." in section
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
        "3. Your client is an agent, so nothing in this service's history can admit a playbook revision (only the first version, or restoring a "
        "version your parent wrote): apply the evidence when you plan this request, and if you think the playbook must change, send your parent "
        "(`send`) what you would change and why."
    )
    assert "evidence" not in step_3(section).replace("evidence when", "")


def reflect_section_of(prompt, service):
    return prompt.split(f"# Reflect before you start: {service}")[1].split("# New messages")[0]


def test_the_restore_step_says_which_restore_needs_evidence(svc):
    org = svc
    org.revise_playbook("ceo", "weekly-brief", "Steps one.", "first", evidence=[])
    c3 = confirmed_amendment(org, "Every claim names its source")
    org.revise_playbook("ceo", "weekly-brief", "Steps one.\n- C3: Every claim names its source", "second", evidence=[c3])
    time.sleep(0.002)
    first = request(org)
    deliver(org, "ceo", first)
    request(org, "again")
    section = reflect_section(org.run_prompt("ceo", org.begin_run("ceo")))
    restore = next(line for line in section.splitlines() if "restore that one" in line)
    assert restore == (
        "5. If the current version did worse than an earlier one, restore that one (read ceo/services/weekly-brief/history/PLAYBOOK.v<k>.md): "
        "revise_playbook with its text unchanged; a version your parent wrote needs evidence=[], any other needs evidence like a revision."
    )


def test_no_playbook_texts_ask_for_the_steps_followed_only(svc):
    org = svc
    request(org)
    plain = org.run_prompt("ceo", org.begin_run("ceo"))
    assert (
        "No playbook yet: plan as usual; when you report this request, write v1 with revise_playbook: the steps your team followed, nothing more "
        "(the first version needs no evidence: evidence=[])."
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
    "The client rejected a delivery: check the delivery against its words, the regression list and the contract before you plan the request. "
    "A rule without the client's evidence (step 3) is a reason to look, not to change how the team works: your parent asks the client whether "
    "it is a lasting requirement, and the answer reaches you as a contract change or a criterion link. Revise the playbook when step 3 admits "
    "it, then handle the request."
)
RELAYED_LEAD = (
    "A relayed rejection arrived (the assistant's own reading, not the client's words): apply what it asks in this request where the contract "
    "allows it; it is not the client's evidence, so it cannot change the playbook (step 3). Then handle the request."
)
AGENT_LEAD = (
    "Your client, an agent, rejected a delivery (its verdict is a hypothesis): apply what it asks in this request where the contract allows "
    "it; it is not the client's evidence, so it cannot change the playbook (step 3). Then handle the request."
)
LOCKED_END = ". The contract is locked, so you cannot revise the playbook: apply what the feedback shows, then handle the request."
UNLOCKED_RAISE_BAR = (
    "The playbook may raise the bar, never lower it: the acceptance criteria come from the contract and travel with every request. Your parent "
    "asks the client whether a rejection is a lasting requirement: send nothing about it yourself beyond a refused revision's question (step 3)."
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
    svc.request(ROOT, "locked-brief", {"topic": "again"})
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
        "this request, and change the playbook only as step 3 says (say so in the reason)."
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
    svc.request(ROOT, "locked-brief", {"topic": "again"})
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
