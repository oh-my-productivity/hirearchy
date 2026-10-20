# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.orgmcp.core import ROOT

ENG = "ceo/eng"
CRITERIA = "exactly 33 words; a non-author reviews the final text"


def drain(org, addr):
    org.begin_run(addr)
    org.end_run(addr, ok=True)


@pytest.fixture
def blocked(org):
    """root -> ceo task; ceo delegated to eng (serving it); eng reported done; ceo reported the root task blocked."""
    task = org.delegate(ROOT, "ceo", "Strict blurb", "Write it.", CRITERIA, budget=20)
    drain(org, "ceo")
    sub = org.delegate("ceo", ENG, "Draft blurb", "Draft it.", "exactly 33 words", budget=4)
    first = org.report("ceo", task.id, "blocked", "review judged a stale draft; no budget to rework")
    result = org.report(ENG, sub.id, "done", "33 words")
    return task, sub, first, result


def test_blocked_task_is_answered_not_open_but_state_says_it_can_be_re_reported(org, blocked):
    task, *_ = blocked
    assert task.id not in {t.id for t in org.open_tasks("ceo")}  # answered: it does not keep the scheduler busy
    assert task.id not in {t.id for t in org.outstanding(ROOT)}
    state = org.whoami("ceo")
    assert "reported blocked; you may re-report it once the blocker is resolved" in state
    assert f'{task.id} "Strict blurb"' in state and CRITERIA in state  # the contract to meet is in front of it
    org.report("ceo", task.id, "done", "all criteria met")
    assert "reported blocked" not in org.whoami("ceo")
