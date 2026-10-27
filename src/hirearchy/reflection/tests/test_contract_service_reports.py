"""Contract of ``ServiceReports``: the ``services`` listing and the totals of a case, text for text as ``services.py`` printed them."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import Message, OrgError
from hirearchy.reflection import ServiceReports, case_spend
from hirearchy.reflection.testing import IMPLEMENTATIONS, ReflectionWorld, fs_world, memory_world

from . import _stories
from ._golden import expected
from ._support import SERVICE, STEPS, ask, define, deliver, implementations, populated, rework, s1_t6

NO_SERVICES = (
    "No services yet. A parent defines a standing service for a direct report with define_service(owner, "
    "name, description, acceptance, deliverable, budget, inputs): the contract. Then request(service, inputs) "
    "asks for it, and feedback(task_id, verdict) tells the owner how it went."
)


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    return populated(request.param(tmp_path))


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ServiceReports]))
def reports(request: pytest.FixtureRequest, tmp_path: Path) -> ServiceReports:
    made = request.param(tmp_path)
    assert isinstance(made, ServiceReports)
    return made


# ------------------------------------------------------------------------------ services_text


def test_without_services_the_text_says_how_to_define_one(w: ReflectionWorld) -> None:
    assert w.reports.services_text("root") == NO_SERVICES == w.reports.services_text("ceo")


def test_an_unknown_actor_is_refused(w: ReflectionWorld) -> None:
    with pytest.raises(OrgError, match="no such agent: ghost"):
        w.reports.services_text("ghost")


@pytest.mark.parametrize("name", list(_stories.LISTINGS))
def test_the_client_sees_the_services_of_its_reports(w: ReflectionWorld, name: str) -> None:
    story = _stories.LISTINGS[name](w)
    assert w.reports.services_text("root") == expected(f"services_root_{name}.txt", story)


@pytest.mark.parametrize("name", list(_stories.LISTINGS))
def test_the_owner_sees_the_services_it_offers(w: ReflectionWorld, name: str) -> None:
    story = _stories.LISTINGS[name](w)
    assert w.reports.services_text("ceo") == expected(f"services_ceo_{name}.txt", story)


def test_a_service_without_requests_says_so(w: ReflectionWorld) -> None:
    define(w, playbook=STEPS)
    text = w.reports.services_text("root")
    assert "  record: no requests yet" in text and '  playbook v1 (2026-10-18): "' in text


def test_a_locked_service_is_marked_to_its_owner_only(w: ReflectionWorld) -> None:
    define(w, locked=True)
    assert "- weekly-brief (contract v1, playbook v0, locked): " in w.reports.services_text("ceo")
    assert "locked" not in w.reports.services_text("root")


def test_each_owner_is_listed_with_its_own_services(w: ReflectionWorld) -> None:
    define(w)
    define(w, owner="ops", name="ops-brief")
    text = w.reports.services_text("root")
    assert "- weekly-brief (offered by ceo; " in text and "- ops-brief (offered by ops; " in text
    assert "ops-brief" not in w.reports.services_text("ceo")


# ------------------------------------------------------------------------------ case_total


@pytest.mark.parametrize("name", list(_stories.LISTINGS))
def test_the_total_of_every_request_of_a_story(w: ReflectionWorld, name: str) -> None:
    story = _stories.LISTINGS[name](w)
    assert "\n".join(f"ask{n}: {w.reports.case_total(a) or '<empty>'}" for n, a in enumerate(story.asks)) == expected(f"totals_{name}.txt", story)


def test_a_plain_task_has_no_total(w: ReflectionWorld) -> None:
    plain = w.s.d.post(Message(sender="root", to="ceo", type="task", body="b", title="plain", budget=2))
    assert w.reports.case_total(plain) == ""


def test_a_case_within_its_budget_does_not_ask_to_tell_the_user(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task, runs=3)
    assert w.reports.case_total(task) == "case total: 3 runs used of 10 handed down (contract: 10 per request)"


def test_a_case_whose_user_requests_ran_more_than_were_handed_down_says_so(w: ReflectionWorld) -> None:
    """Rule R (design 13): the user's rework (``source="human"``, budget 5 on top of 10) runs 16 runs against the 15 approved. Before 0a.3 the
    relayed default of this rework printed this sentence on the runs handed down alone (E5's false positive); it now needs a real overrun."""
    define(w)
    first = ask(w)
    deliver(w, first)
    again = w.s.commands.request("root", SERVICE, {"topic": "ai"}, revises=first.id, budget=5, source="human")
    deliver(w, again, runs=15)
    assert w.reports.case_total(again) == (
        "case total: 16 runs used of 15 handed down (contract: 10 per request). The user's requests now cost 16 runs, more than the 15 the user "
        "approved for this case (contract: 10 per request, plus 5 approved beyond it): tell the user."
    )


def test_a_relayed_rework_handed_down_more_than_the_contract_gives_is_no_overspend(w: ReflectionWorld) -> None:
    """The relayed form of the same chain (the default of a rework root sends without a source): 15 runs handed down against the contract's 10
    is the assistant's own business and says nothing of the user (D-E5-1, E5 s1 T6)."""
    define(w)
    first = ask(w)
    deliver(w, first)
    again = w.s.commands.request("root", SERVICE, {"topic": "ai"}, revises=first.id, budget=5)
    assert w.reports.case_total(again) == f"case total: 1 runs used of 15 handed down (contract: 10 per request). {none_yet(again.id)}"
    assert "exceeds" not in w.reports.case_total(again) and "tell the user" not in w.reports.case_total(again)


def test_a_request_of_a_retired_service_has_no_total(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    w.s.commands.retire_service("root", "ceo", SERVICE, "obsolete")
    assert w.reports.case_total(task) == ""


def test_the_implementations_agree_on_an_empty_organization(reports: ServiceReports) -> None:
    assert reports.services_text("root") == NO_SERVICES


def test_case_total_warns_only_when_more_runs_were_used_than_the_contract_gives(w: ReflectionWorld) -> None:
    """Study E3's numbers, memo by memo, with its 15-run contract: runs handed down above 15 are no overspend (F-E3-7), runs used above 15 are."""
    define(w, budget=15)
    for used, handed in ((12, 21), (15, 25), (14, 20)):
        task = ask(w, f"t{used}", budget=handed)
        deliver(w, task, runs=used)
        total = w.reports.case_total(task)
        assert total == f"case total: {used} runs used of {handed} handed down (contract: 15 per request)"
        assert "exceeds" not in total
    over = ask(w, "over", budget=15)
    deliver(w, over, runs=16)
    assert w.reports.case_total(over) == (
        "case total: 16 runs used of 15 handed down (contract: 15 per request). "
        "This case now exceeds the per-request budget of 15: tell the user."
    )


# ------------------------------------------------------------------------------ case_total, D-E5-1 (design 4.4)
OWN = "report them to the user as yours, and never ask the user to fund them."


def own_spend(ids: str, several: bool = False) -> str:
    """``RELAYED_SPEND``."""
    return f"The runs of your relayed rework{'s' if several else ''} are your own spend, not the user's: {OWN}"


def none_yet(ids: str, several: bool = False) -> str:
    """``RELAYED_NONE_YET``."""
    who, has, its = ("s", "have", "their") if several else ("", "has", "its")
    return f"Your relayed rework{who} {ids} {has} used no run yet; {its} runs will be your own spend, not the user's: {OWN}"


def unsplit(ids: str, n: int, several: bool = False) -> str:
    """``RELAYED_UNSPLIT`` (DR-0a3-1, P-2)."""
    who, has, it, its, cap = ("s", "have", "they", "their", "Their") if several else ("", "has", "it", "its", "Its")
    return (
        f"Your relayed rework{who} {ids} {has} no run counted apart: a request of the user's followed before {it} finished, so {its} runs could not "
        f"be split from the user's interval, which holds {n} run(s) since then, all counted with the user's requests. {cap} runs are your own "
        f"spend, not the user's: {OWN}"
    )


def todays_text(w: ReflectionWorld, task: Message) -> str:
    """The case total as 0a.2 printed it (the agent client's text must stay these bytes)."""
    (c,) = [x for x in w.history.cases(task.to, task.service or "") if task.id in {t.id for t in x.tasks}]
    contract = w.s.catalog.read_contract(task.to, task.service or "")
    assert contract is not None
    text = f"case total: {c.runs} runs used of {c.budget} handed down (contract: {contract.budget} per request)"
    if case_spend(c) > contract.budget:
        text += f". This case now exceeds the per-request budget of {contract.budget}: tell the user."
    return text


def agent_client(w: ReflectionWorld, runs: tuple[int, int], relayed: bool) -> Message:
    """``ceo`` asks its report ``ceo/eng`` for ``inner`` and sends the request back; the second request carries ``source: relayed`` when ``relayed``
    (the tier an agent's rework inherits from the work it was made in). Returns the second request."""
    w.s.d.post(Message(sender="root", to="ceo", type="note", body="runs for you", title="grant", budget=60))
    define(w, "ceo/eng", "inner", actor="ceo")
    first = w.s.commands.request("ceo", "inner", {"topic": "ai"})
    deliver(w, first, runs=runs[0])
    second = w.s.d.post(Message(
        sender="ceo", to="ceo/eng", type="task", title="inner: ai", body="again", budget=5, revises=first.id, service="inner",
        source="relayed" if relayed else None,
    ))
    deliver(w, second, runs=runs[1])
    return second


@pytest.mark.parametrize("relayed", [False, True], ids=["plain rework", "inherited relayed rework"])
@pytest.mark.parametrize("runs", [(2, 3), (6, 7)], ids=["within", "over"])
def test_an_agent_clients_case_total_is_todays_text_whatever_its_relayed_reworks(w: ReflectionWorld, runs: tuple[int, int], relayed: bool) -> None:
    """I6: only a human client's case is split; an agent client keeps the bytes of 0a.2, the OVER_CONTRACT sentence included."""
    second = agent_client(w, runs, relayed)
    assert w.reports.case_total(second) == todays_text(w, second)
    assert ("exceeds" in w.reports.case_total(second)) is (sum(runs) > 10)
    assert "relayed" not in w.reports.case_total(second)


def test_a_human_case_without_a_relayed_task_and_without_a_top_up_prints_todays_bytes(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task, runs=11)
    assert w.reports.case_total(task) == todays_text(w, task) == (
        "case total: 11 runs used of 10 handed down (contract: 10 per request). This case now exceeds the per-request budget of 10: tell the user."
    )


def test_an_explicit_human_budget_raises_the_approval_so_the_runs_it_pays_for_are_no_overspend(w: ReflectionWorld) -> None:
    """D-E5-1 (4.3): the user's rework with a budget of 8 on top of 10 approves 18; 12 runs used is no overspend, where 0a.2 said "exceeds"."""
    define(w)
    first = ask(w)
    deliver(w, first, runs=5)
    again = rework(w, first, budget=8)
    deliver(w, again, runs=7)
    assert w.reports.case_total(again) == "case total: 12 runs used of 18 handed down (contract: 10 per request)"


def test_the_user_s_requests_that_cost_more_than_the_user_approved_say_so_with_the_top_up(w: ReflectionWorld) -> None:
    """DR-0a3-11: a first request sent with an explicit budget above the contract's is approved beyond it, not a top-up."""
    define(w, budget=12)
    task = ask(w, budget=15)
    deliver(w, task, runs=13)
    assert w.reports.case_total(task) == "case total: 13 runs used of 15 handed down (contract: 12 per request)"
    over = ask(w, "again", budget=15)
    deliver(w, over, runs=16)
    assert w.reports.case_total(over) == (
        "case total: 16 runs used of 15 handed down (contract: 12 per request). The user's requests now cost 16 runs, more than the 15 the user "
        "approved for this case (contract: 12 per request, plus 3 approved beyond it): tell the user."
    )


def test_a_relayed_rework_that_has_not_run_yet_is_named_and_nothing_is_counted_apart(w: ReflectionWorld) -> None:
    """The row `relayed_runs == 0`: head form 1 (never "0 by your relayed rework") and RELAYED_NONE_YET."""
    define(w)
    first = ask(w)
    deliver(w, first, runs=3)
    relayed = rework(w, first, source="relayed", budget=6)
    assert w.reports.case_total(relayed) == (
        f"case total: 3 runs used of 16 handed down (contract: 10 per request). {none_yet(relayed.id)}"
    )


def test_several_relayed_reworks_that_have_not_run_yet_are_named_in_the_plural(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w)
    deliver(w, first, runs=2)
    one = rework(w, first, source="relayed", budget=3)
    deliver(w, one, runs=0, budget=3)
    two = rework(w, one, source="relayed", budget=3)
    ids = f"{one.id}, {two.id}"
    assert w.reports.case_total(two) == f"case total: 2 runs used of 16 handed down (contract: 10 per request). {none_yet(ids, True)}"


def test_a_relayed_rework_answered_before_the_next_request_is_named_none_yet_whatever_follows(w: ReflectionWorld) -> None:
    """DR-0a3-1: R (6) is answered with its whole budget back before H is sent, so nothing of R lies in H's interval: RELAYED_NONE_YET."""
    define(w)
    first = ask(w)
    deliver(w, first, runs=1)
    relayed = rework(w, first, source="relayed", budget=6)
    deliver(w, relayed, runs=0, budget=6)
    human = rework(w, relayed)
    for _ in range(4):
        w.use_run("ceo")
    assert w.reports.case_total(human) == f"case total: 5 runs used of 26 handed down (contract: 10 per request). {none_yet(relayed.id)}"


def test_a_relayed_rework_overlapped_by_the_next_request_says_its_runs_could_not_be_split(w: ReflectionWorld) -> None:
    """DR-0a3-1: R (6) is followed by H before any run and has no result: its runs fall in H's interval (4 runs since then). Form 1 and
    RELAYED_UNSPLIT, never "has used no run yet"."""
    define(w)
    first = ask(w)
    deliver(w, first, runs=1)
    relayed = rework(w, first, source="relayed", budget=6)
    human = rework(w, relayed)
    for _ in range(4):
        w.use_run("ceo")
    total = w.reports.case_total(human)
    assert total == f"case total: 5 runs used of 26 handed down (contract: 10 per request). {unsplit(relayed.id, 4)}"
    assert "has used no run yet" not in total and "by your relayed rework" not in total


def test_several_relayed_reworks_overlapped_by_the_next_request_are_named_in_the_plural(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w)
    deliver(w, first, runs=1)
    one = rework(w, first, source="relayed", budget=3)
    two = rework(w, one, source="relayed", budget=3)
    human = rework(w, two)
    for _ in range(2):
        w.use_run("ceo")
    assert w.reports.case_total(human) == (
        f"case total: 3 runs used of 26 handed down (contract: 10 per request). {unsplit(f'{one.id}, {two.id}', 2, True)}"
    )


def test_the_runs_of_a_relayed_rework_are_named_apart_and_called_the_assistants_own_spend(w: ReflectionWorld) -> None:
    """E5 s1 T6 (design 4.4): 15 runs, 10 the user's and 5 the relayed rework's; 17 approved, so no "exceeds" and no "tell the user"."""
    define(w, budget=12)
    relayed = s1_t6(w)
    total = w.reports.case_total(relayed)
    assert total == (
        f"case total: 15 runs used: 10 by the user's requests, 5 by your relayed rework {relayed.id}; 30 handed down (contract: 12 per request). "
        f"{own_spend(relayed.id)}"
    )
    assert "exceeds" not in total and "tell the user" not in total


def test_several_relayed_reworks_with_runs_are_named_in_the_plural(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w)
    deliver(w, first, runs=1)
    one = rework(w, first, source="relayed", budget=3)
    deliver(w, one, runs=1)
    two = rework(w, one, source="relayed", budget=3)
    deliver(w, two, runs=2)
    assert w.reports.case_total(two) == (
        f"case total: 4 runs used: 1 by the user's requests, 3 by your relayed reworks {one.id}, {two.id}; 16 handed down (contract: 10 per request). "
        f"{own_spend(one.id, True)}"
    )


def test_the_user_s_overspend_comes_before_the_relayed_sentence_and_ignores_the_relayed_runs(w: ReflectionWorld) -> None:
    """The user's requests cost 11 against 10 approved, and the relayed rework's 3 runs are not added to that."""
    define(w)
    first = ask(w)
    deliver(w, first, runs=11)
    relayed = rework(w, first, source="relayed", budget=3)
    deliver(w, relayed, runs=3)
    assert w.reports.case_total(relayed) == (
        f"case total: 14 runs used: 11 by the user's requests, 3 by your relayed rework {relayed.id}; 13 handed down (contract: 10 per request). "
        "The user's requests now cost 11 runs, more than the 10 the user approved for this case (contract: 10 per request): tell the user. "
        f"{own_spend(relayed.id)}"
    )


def overlapped_by_a_user_rework(w: ReflectionWorld, own: int) -> Message:
    """Contract 10. A request (budget 4, 4 runs); a relayed rework R (6) with 2 runs and no result; a human rework H (3) in whose interval R's 4 later
    runs fall, and the ``own`` runs H makes itself. Returns H."""
    define(w)
    first = ask(w, budget=4)
    deliver(w, first, runs=4)
    relayed = rework(w, first, source="relayed", budget=6)
    for _ in range(2):
        w.use_run("ceo")
    human = rework(w, relayed, budget=3)
    for _ in range(4):
        w.use_run("ceo")
    deliver(w, human, runs=own)
    return human


def test_the_overlap_of_a_relayed_rework_is_not_counted_against_the_user(w: ReflectionWorld) -> None:
    """D-E5-1 (`relayed_overlap`): 14 of the 16 runs lie in the user's intervals and 4 of those can be R's, so the user's cost is 10, which is what
    was approved: no "exceeds" (declared limit 3: an overrun of that size would be hidden)."""
    human = overlapped_by_a_user_rework(w, own=6)
    total = w.reports.case_total(human)
    assert "exceeds" not in total and "tell the user" not in total
    assert total.startswith("case total: 16 runs used: 14 by the user's requests, 2 by your relayed rework ")


def test_two_more_runs_in_the_user_s_interval_than_the_overlap_can_explain_are_an_overspend(w: ReflectionWorld) -> None:
    """The same chain with 2 more charged runs in H's interval: the user's cost is 12 against 10 approved."""
    human = overlapped_by_a_user_rework(w, own=8)
    total = w.reports.case_total(human)
    assert "The user's requests now cost 12 runs, more than the 10 the user approved for this case (contract: 10 per request): tell the user." in total
    assert total.startswith("case total: 18 runs used: 16 by the user's requests, 2 by your relayed rework ")


def memo_reworked_after_another_request(w: ReflectionWorld, after: int) -> Message:
    """Contract 12. Memo 1 is done (8 runs, 4 returned); memo 2 is requested and runs 4 runs; then memo 1's human rework (the 4 that are left); then
    ``after`` more runs of the team. Returns the rework."""
    define(w, budget=12)
    memo1 = ask(w, "memo 1")
    deliver(w, memo1, runs=8, budget=4)
    ask(w, "memo 2")
    for _ in range(4):
        w.use_run("ceo")
    again = rework(w, memo1, budget=4)
    for _ in range(after):
        w.use_run("ceo")
    return again


def test_limit_2_a_reopened_window_prints_no_exceeds_at_the_rework(w: ReflectionWorld) -> None:
    """Declared limit 2 (4.3): the 4 runs of memo 2 count in memo 1's case and in what the user approved, so the rework is no overspend."""
    again = memo_reworked_after_another_request(w, after=0)
    assert w.reports.case_total(again) == "case total: 12 runs used of 16 handed down (contract: 12 per request)"


def test_limit_2_pin_the_runs_of_another_request_after_the_rework_can_make_the_overspend_sentence_fire(w: ReflectionWorld) -> None:
    """Declared limit 2 and DR-0a3-7: once the window has reopened, memo 2's later runs keep counting in memo 1's case, as 0a.2's sentence did.
    5 runs after the rework, which carries 4, make the user's requests "cost" 17 against 16 approved: OVER_APPROVED fires on runs the user's requests
    did not use. Not corrected in 0a.3 (0b's window rule)."""
    again = memo_reworked_after_another_request(w, after=5)
    assert w.reports.case_total(again) == (
        "case total: 17 runs used of 16 handed down (contract: 12 per request). The user's requests now cost 17 runs, more than the 16 the user "
        "approved for this case (contract: 12 per request, plus 4 approved beyond it): tell the user."
    )
