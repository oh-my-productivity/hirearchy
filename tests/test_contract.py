"""The task contract: visible in every run prompt (QA-17) and affordable to delegate (QA-18)."""

import pytest

from orgmcp import templates
from orgmcp.core import ROOT, Org, OrgError

ENG = "ceo/eng"
CRITERIA = "exactly 33 words; acrostic P-L-A-N-T"
WORKER_CRITERIA = "exactly 33 words. First letters of the five lines spell PLANT."


def drain(org, addr):
    org.begin_run(addr)
    org.end_run(addr, ok=True)


@pytest.fixture
def scenario(org):
    """root -> ceo task (handled in an earlier run) -> ceo delegated to eng -> eng reported; returns the pieces."""
    task = org.delegate(ROOT, "ceo", "Strict blurb", "Write a blurb about plants.", CRITERIA, ["ceo/work/brief.md"], budget=20)
    drain(org, "ceo")
    sub = org.delegate("ceo", ENG, "Draft blurb", "Draft it.", WORKER_CRITERIA, budget=4)
    result = org.report(ENG, sub.id, "done", "35 words, acrostic ok")
    batch = [org.find_received("ceo", result.id)]
    return task, sub, result, batch


def prompt_for(org, addr, batch):
    return org.run_prompt(addr, batch)


# ---------------------------------------------------------------- open tasks


def test_prompt_carries_the_full_open_task_verbatim(org, scenario):
    task, _, _, batch = scenario
    prompt = prompt_for(org, "ceo", batch)
    assert f'{task.id} "Strict blurb" from root' in prompt  # the existing line is unchanged
    for fragment in ("Write a blurb about plants.", CRITERIA, "ceo/work/brief.md", "Acceptance criteria"):
        assert fragment in prompt


def test_answered_task_is_no_longer_in_the_contract_list(org, scenario):
    task, _, _, batch = scenario
    org.report("ceo", task.id, "failed", "gave up")
    assert CRITERIA not in prompt_for(org, "ceo", batch)


def test_open_task_in_the_batch_is_shown_once(org):
    task = org.delegate(ROOT, "ceo", "Strict blurb", "goal", CRITERIA, budget=10)
    prompt = prompt_for(org, "ceo", org.begin_run("ceo"))
    assert prompt.count(CRITERIA) == 1
    assert f'{task.id} "Strict blurb" from root' in prompt


def test_whoami_shows_the_contract_too(org):
    org.delegate(ROOT, "ceo", "Strict blurb", "goal", CRITERIA, budget=10)
    assert CRITERIA in org.whoami("ceo")


# ------------------------------------------------------- results and criteria


def test_result_is_followed_by_the_delegated_criteria_verbatim(org, scenario):
    _, sub, _, batch = scenario
    prompt = prompt_for(org, "ceo", batch)
    assert WORKER_CRITERIA in prompt
    assert f"({sub.id})" in prompt
    assert prompt.index("status: done") < prompt.index(WORKER_CRITERIA)  # right after the result it judges


def test_single_open_task_is_linked_to_the_delegation(org, scenario):
    task, _, _, batch = scenario
    prompt = prompt_for(org, "ceo", batch)
    assert f'probably serves your open task {task.id} "Strict blurb"' in prompt


def test_no_link_when_the_open_task_is_ambiguous(org):
    org.delegate(ROOT, "ceo", "First job", "g", "FIRST-CRITERION", budget=10)
    org.delegate(ROOT, "ceo", "Second job", "g", "SECOND-CRITERION", budget=1)
    sub = org.delegate("ceo", ENG, "t", "g", "SUB-CRITERION", budget=2)
    result = org.report(ENG, sub.id, "done", "ok")
    prompt = prompt_for(org, "ceo", [org.find_received("ceo", result.id)])
    assert "probably serves" not in prompt
    assert all(c in prompt for c in ("FIRST-CRITERION", "SECOND-CRITERION", "SUB-CRITERION"))  # contracts all shown


def test_link_ignores_tasks_assigned_after_the_delegation(org):
    first = org.delegate(ROOT, "ceo", "First job", "g", "FIRST-CRITERION", budget=10)
    sub = org.delegate("ceo", ENG, "t", "g", "SUB-CRITERION", budget=2)
    org.delegate(ROOT, "ceo", "Later job", "g", "LATER-CRITERION", budget=1)
    result = org.report(ENG, sub.id, "done", "ok")
    prompt = prompt_for(org, "ceo", [org.find_received("ceo", result.id)])
    assert f'probably serves your open task {first.id} "First job"' in prompt
    assert prompt.count("probably serves") == 1


def test_delegated_task_is_shown_once(org, scenario):
    prompt = prompt_for(org, "ceo", scenario[3])
    assert prompt.count(WORKER_CRITERIA) == 1
    assert prompt.count(CRITERIA) == 1


def test_note_and_task_messages_get_no_extra_block(org):
    org.send(ROOT, "ceo", "hello")
    prompt = prompt_for(org, "ceo", org.begin_run("ceo"))
    assert "that this result answers" not in prompt


# ------------------------------------------------------------ default budget


def test_default_budget_is_capped_by_default_budget_setting(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=50)
    assert org.delegate("ceo", ENG, "t", "g", "a").budget == 10


def test_default_budget_is_what_is_affordable(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    msg = org.delegate("ceo", ENG, "t", "g", "a")
    assert msg.budget == 5 and org.budget("ceo") == 1  # 6 - (0 outstanding + 1)


def test_default_budget_reserves_a_run_per_outstanding_delegation(org):
    org.hire("ceo", "ops", "Ops", "Do ops.")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=8)
    org.delegate("ceo", ENG, "t", "g", "a", budget=2)  # 6 left, 1 outstanding
    msg = org.delegate("ceo", "ceo/ops", "t", "g", "a")
    assert msg.budget == 4  # 6 - (1 outstanding + 1 for this one)
    assert org.budget("ceo") == 2  # exactly the two reserved runs


def test_default_budget_below_one_explains_the_options(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=2)  # 2 left: 0 outstanding + 1 reserve = 1 affordable
    org.delegate("ceo", ENG, "t", "g", "a")
    org.hire("ceo", "ops", "Ops", "Do ops.")
    with pytest.raises(OrgError) as e:
        org.delegate("ceo", "ceo/ops", "t", "g", "a")
    text = str(e.value)
    assert "send" in text and "yourself" in text and "blocked" in text


def test_default_budget_with_exactly_the_reserve_left_fails(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=1)
    with pytest.raises(OrgError, match="cannot afford"):
        org.delegate("ceo", ENG, "t", "g", "a")


def test_root_default_budget_is_the_configured_default(org):
    assert org.delegate(ROOT, "ceo", "T", "g", "a").budget == org.config["default_budget"]


def test_explicit_budget_keeps_the_strict_check(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=6)
    with pytest.raises(OrgError, match="not enough budget"):
        org.delegate("ceo", ENG, "t", "g", "a", budget=6)
    assert org.delegate("ceo", ENG, "t", "g", "a", budget=5).budget == 5
    with pytest.raises(OrgError, match="at least 1"):
        org.delegate("ceo", ENG, "t", "g", "a", budget=0)


# ----------------------------------------------------------------- the rules


def test_rules_carry_the_contract_protocol(org):
    rules = org.rules()
    assert "verbatim" in rules and "never paraphrase" in rules.lower().replace("; ", " ")
    assert "verifiably met" in rules and "33 words means 33" in rules
    assert "`blocked` or `failed`" in rules and "cannot afford" in rules
    assert "`revises`" in rules or "revises=" in rules  # old rule 3 guidance survives
    assert "MEMORY.md" in rules and "condense" in rules  # old rule 6 guidance survives


def test_rules_numbering_is_contiguous():
    import re

    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", templates.ORG_RULES, re.M)]
    assert numbers == list(range(1, len(numbers) + 1))
