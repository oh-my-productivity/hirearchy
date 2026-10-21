# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.hirearchy.core import ROOT

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
