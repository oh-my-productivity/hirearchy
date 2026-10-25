"""Contract of ``CaseHistory``: the cases of a service are derived from the messages of its client and the run logs of its owner's team."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from hirearchy.kernel import Message, msg_time
from hirearchy.reflection import CaseHistory
from hirearchy.reflection._cases import DerivedCaseHistory
from hirearchy.reflection._ports import PlaybookTimelines, RunCounter
from hirearchy.reflection.testing import IMPLEMENTATIONS, ReflectionWorld, fs_world, memory_world

from ._support import SERVICE, STEPS, ask, define, deliver, implementations, nested, note_on, populated, rate, revise, rework


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    return populated(request.param(tmp_path))


@pytest.fixture(params=implementations(IMPLEMENTATIONS[CaseHistory]))
def history(request: pytest.FixtureRequest, tmp_path: Path) -> CaseHistory:
    made = request.param(tmp_path)
    assert isinstance(made, CaseHistory)
    return made


# ------------------------------------------------------------------------------ cases


def test_a_service_nobody_defined_has_no_cases(w: ReflectionWorld) -> None:
    assert w.history.cases("ceo", SERVICE) == []


def test_the_service_of_a_top_level_agent_has_the_human_for_client(w: ReflectionWorld) -> None:
    define(w)
    ask(w)
    assert [c.owner for c in w.history.cases("ceo", SERVICE)] == ["ceo"]


def test_an_unanswered_request_is_an_open_case(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w, title="T", budget=7)
    (case,) = w.history.cases("ceo", SERVICE)
    assert (case.id, case.state, case.result, case.finished) == (task.id, "open", None, None)
    assert (case.reworks, case.budget, case.runs, case.verdicts, case.lessons) == (0, 7, 0, [], [])
    assert case.tasks == [task] and case.title == "T" and case.started is not None


@pytest.mark.parametrize("status", ["done", "failed"])
def test_a_final_result_ends_the_case(w: ReflectionWorld, status: str) -> None:
    define(w)
    task = ask(w)
    result = deliver(w, task, status=status)
    (case,) = w.history.cases("ceo", SERVICE)
    assert case.state == status and case.result == result and case.finished is not None


def test_a_blocked_result_leaves_the_case_unfinished_but_answered(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task, status="blocked", lessons="Sources were not provided.")
    (case,) = w.history.cases("ceo", SERVICE)
    assert case.state == "blocked" and case.finished is None and case.lessons == ["Sources were not provided."]


def test_the_latest_result_of_a_task_is_its_outcome(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task, status="blocked")
    done = deliver(w, task, status="done")
    (case,) = w.history.cases("ceo", SERVICE)
    assert case.state == "done" and case.result == done


def test_cases_are_oldest_first_and_one_per_chain(w: ReflectionWorld) -> None:
    define(w)
    one, two, three = ask(w, "a"), ask(w, "b"), ask(w, "c")
    assert [c.id for c in w.history.cases("ceo", SERVICE)] == [one.id, two.id, three.id]


def test_a_rework_belongs_to_the_case_it_sends_back(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w)
    deliver(w, first)
    again = rework(w, first, budget=3)
    deliver(w, again, lessons="Applied.")
    (case,) = w.history.cases("ceo", SERVICE)
    assert case.id == first.id and case.tasks == [first, again] and case.reworks == 1 and case.budget == 13
    assert case.result is not None and case.result.reply_to == again.id and case.lessons == ["Applied."]


def test_a_rework_of_a_rework_stays_in_the_chain(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w)
    second = rework(w, first, budget=2)
    third = rework(w, second, budget=2)
    (case,) = w.history.cases("ceo", SERVICE)
    assert [t.id for t in case.tasks] == [first.id, second.id, third.id] and case.reworks == 2


def test_the_requests_of_other_services_and_owners_are_not_in_it(w: ReflectionWorld) -> None:
    define(w)
    define(w, name="other")
    define(w, owner="ops", name="ops-brief")
    mine = ask(w)
    other = w.s.commands.request("root", "other", {"topic": "x"})
    w.s.commands.request("root", "ops-brief", {"topic": "x"})
    assert [c.id for c in w.history.cases("ceo", SERVICE)] == [mine.id]
    assert [c.id for c in w.history.cases("ceo", "other")] == [other.id]
    assert len(w.history.cases("ops", "ops-brief")) == 1


# ------------------------------------------------------------------------------ lessons and verdicts


def test_lessons_come_from_the_results_in_order_of_the_chain(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w)
    one = deliver(w, first, lessons="First lesson.")
    again = rework(w, first, budget=2)
    two = deliver(w, again, lessons="Second lesson.")
    (case,) = w.history.cases("ceo", SERVICE)
    assert case.lessons == ["First lesson.", "Second lesson."] and case.lesson_ids == [one.id, two.id]


def test_a_result_without_a_lessons_section_adds_none(w: ReflectionWorld) -> None:
    define(w)
    deliver(w, ask(w))
    (case,) = w.history.cases("ceo", SERVICE)
    assert case.lessons == [] and case.lesson_ids == []


def test_the_clients_verdicts_stay_in_order_with_the_task_they_were_given_on(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w)
    deliver(w, first)
    no = rate(w, first, "reject", "Too long.")
    w.s.d.clock.advance(1)
    again = rework(w, first, budget=2)
    deliver(w, again)
    w.s.d.clock.advance(1)
    yes = rate(w, again, "accept", "Better.")
    (case,) = w.history.cases("ceo", SERVICE)
    assert [(v.verdict, v.note, v.task_id, v.step, v.message) for v in case.verdicts] == [
        ("reject", "Too long.", first.id, 0, no), ("accept", "Better.", again.id, 1, yes),
    ]
    assert all(v.created is not None for v in case.verdicts) and case.verdict == "accept" and case.feedback == yes


def test_a_bare_accept_has_no_words(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task)
    rate(w, task, "accept")
    (case,) = w.history.cases("ceo", SERVICE)
    assert [(v.verdict, v.note) for v in case.verdicts] == [("accept", "")]


def test_a_case_nobody_rated_has_no_verdict(w: ReflectionWorld) -> None:
    define(w)
    deliver(w, ask(w))
    (case,) = w.history.cases("ceo", SERVICE)
    assert case.verdict is None and case.feedback is None and not case.rejected and case.evidence_at == case.finished


# ------------------------------------------------------------------------------ tiers, links, client kind and relayed reworks


def test_verdicts_carry_their_tier(w: ReflectionWorld) -> None:
    define(w)
    first, second, third = ask(w, "a"), ask(w, "b"), ask(w, "c")
    for task in (first, second, third):
        deliver(w, task)
    note_on(w, first, verdict="reject", source="human")
    note_on(w, second, verdict="reject", source="relayed")
    note_on(w, third, verdict="accept")  # written before sources existed
    one, two, three = w.history.cases("ceo", SERVICE)
    assert [c.verdicts[0].tier for c in (one, two, three)] == ["human", "relayed", "human"]


def test_a_legacy_root_note_without_source_is_human(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task)
    note_on(w, task, verdict="reject", body="Too long.")  # as every note written before sources existed
    (case,) = w.history.cases("ceo", SERVICE)
    (verdict,) = case.verdicts
    assert verdict.message.source is None and verdict.tier == "human" and (verdict.links, verdict.links_tier) == ((), "")


def test_an_agent_clients_verdict_is_of_the_agent_tier(w: ReflectionWorld) -> None:
    answered = nested(w)
    w.s.commands.feedback("ceo", answered.reply_to or "", "reject", "No.")
    (case,) = w.history.cases("ceo/eng", "inner")
    assert [v.tier for v in case.verdicts] == ["agent"]


def test_a_link_note_is_not_a_verdict(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task)
    no = note_on(w, task, verdict="reject", source="human")
    link = note_on(w, task, reply_to=no.id, criterion="C2", source="human")
    (case,) = w.history.cases("ceo", SERVICE)
    assert [v.message for v in case.verdicts] == [no] and case.feedback == no and case.verdict == "reject"
    assert (case.verdicts[0].links, case.verdicts[0].links_tier) == (("C2",), "human") and link.id > no.id


def test_a_link_note_replying_to_nothing_of_the_case_is_ignored(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task)
    no = note_on(w, task, verdict="reject", source="human")
    note_on(w, task, reply_to="20260101T000000000000-root-0001", criterion="C1", source="human")
    plain = note_on(w, task, reply_to=no.id, source="human")  # no criterion: an ordinary note
    (case,) = w.history.cases("ceo", SERVICE)
    assert [v.message for v in case.verdicts] == [no] and case.verdicts[0].links == () and plain.criterion is None


def test_the_latest_human_link_wins_over_a_later_relayed_one(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task)
    no = note_on(w, task, verdict="reject", source="human")
    note_on(w, task, reply_to=no.id, criterion="C1", source="human")
    note_on(w, task, reply_to=no.id, criterion="C2, R1", source="human")
    note_on(w, task, reply_to=no.id, criterion="none", source="relayed")
    (case,) = w.history.cases("ceo", SERVICE)
    assert (case.verdicts[0].links, case.verdicts[0].links_tier) == (("C2", "R1"), "human")


def test_without_a_human_link_the_latest_of_any_tier_wins(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task)
    no = note_on(w, task, verdict="reject", source="relayed")
    note_on(w, task, reply_to=no.id, criterion="C1", source="relayed")
    note_on(w, task, reply_to=no.id, criterion="C2", source="relayed")
    (case,) = w.history.cases("ceo", SERVICE)
    assert (case.verdicts[0].links, case.verdicts[0].links_tier) == (("C2",), "relayed")


def test_the_link_on_the_verdict_itself_is_a_candidate(w: ReflectionWorld) -> None:
    define(w)
    first, second = ask(w, "a"), ask(w, "b")
    for task in (first, second):
        deliver(w, task)
    own = note_on(w, first, verdict="reject", source="human", criterion="C1")
    other = note_on(w, second, verdict="reject", source="human", criterion="C1")
    note_on(w, second, reply_to=other.id, criterion="C2", source="human")  # a later link replaces the verdict's own
    one, two = w.history.cases("ceo", SERVICE)
    assert (one.verdicts[0].message, one.verdicts[0].links, one.verdicts[0].links_tier) == (own, ("C1",), "relayed")
    assert (two.verdicts[0].links, two.verdicts[0].links_tier) == (("C2",), "human")


def test_a_criterion_on_the_rejection_itself_is_relayed_tier(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task)
    note_on(w, task, verdict="reject", source="human", criterion="C1")
    (case,) = w.history.cases("ceo", SERVICE)
    (verdict,) = case.verdicts
    assert verdict.tier == "human"  # the rejection is still the user's judgement: only what it is about needs the yes
    assert (verdict.links, verdict.links_tier) == (("C1",), "relayed")


def test_a_human_confirms_link_wins_over_the_verdicts_own_criterion(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task)
    no = note_on(w, task, verdict="reject", source="human", criterion="C1")
    note_on(w, task, reply_to=no.id, criterion="C2", source="human")
    (case,) = w.history.cases("ceo", SERVICE)
    assert (case.verdicts[0].links, case.verdicts[0].links_tier) == (("C2",), "human")


def test_every_human_link_note_confirms_what_it_names(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task)
    no = note_on(w, task, verdict="reject", source="human", criterion="C4")  # its own criterion is never a confirmation
    note_on(w, task, reply_to=no.id, criterion="C1", source="human")
    note_on(w, task, reply_to=no.id, criterion="C2, R1", source="human")
    note_on(w, task, reply_to=no.id, criterion="C3", source="relayed")
    (case,) = w.history.cases("ceo", SERVICE)
    (verdict,) = case.verdicts
    assert verdict.confirmed == ("C1", "C2")  # in note order, links only (an R<j> is not a criterion), the relayed C3 left out
    assert (verdict.links, verdict.links_tier) == (("C2", "R1"), "human")  # the effective link keeps its winner rule


def test_a_verdict_with_no_criterion_and_no_link_note_has_no_link(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task)
    rate(w, task, "reject", "Too long.")
    (case,) = w.history.cases("ceo", SERVICE)
    assert (case.verdicts[0].links, case.verdicts[0].links_tier) == ((), "")


def test_client_kind_is_human_under_root_and_agent_otherwise(w: ReflectionWorld) -> None:
    define(w)
    ask(w)
    nested(w)
    (human,) = w.history.cases("ceo", SERVICE)
    (agent,) = w.history.cases("ceo/eng", "inner")
    assert (human.client_kind, agent.client_kind) == ("human", "agent")


def test_relayed_reworks_count_the_chains_relayed_tasks_after_the_first(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w)
    deliver(w, first)
    second = rework(w, first, source="relayed")
    deliver(w, second)
    third = rework(w, second, source="human")
    deliver(w, third)
    rework(w, third, source="relayed")
    deliver(w, ask(w, "other"))
    one, two = w.history.cases("ceo", SERVICE)
    assert (one.reworks, one.relayed_reworks) == (3, 2) and (two.reworks, two.relayed_reworks) == (0, 0)


def test_a_rework_without_a_source_is_not_counted_as_relayed(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w)
    deliver(w, first)
    w.s.d.post(Message(sender="root", to="ceo", type="task", title="again", body="b", service=SERVICE, revises=first.id, budget=2))
    (case,) = w.history.cases("ceo", SERVICE)
    assert (case.reworks, case.relayed_reworks) == (1, 0)


# ------------------------------------------------------------------------------ the runs a case's results returned


def test_a_case_counts_the_runs_its_results_returned(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w, budget=5)
    deliver(w, first, budget=3)
    second = rework(w, first, budget=4)
    deliver(w, second, budget=2)
    rework(w, second, budget=4)  # a task without a result adds 0
    (case,) = w.history.cases("ceo", SERVICE)
    assert case.returned == 5 and case.budget == 13


def test_a_case_clamps_each_results_returned_runs_to_its_tasks_budget(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w, budget=4)
    deliver(w, task, budget=9)
    (case,) = w.history.cases("ceo", SERVICE)
    assert case.returned == 4


# ------------------------------------------------------------------------------ runs and the playbook


def test_the_runs_of_the_owner_and_its_team_in_the_window_of_the_case_are_counted(w: ReflectionWorld) -> None:
    define(w)
    w.use_run("ceo")  # before the request: not part of it
    task = ask(w)
    w.use_run("ceo")
    w.use_run("ceo/eng")
    w.use_run("ops")  # not in the owner's subtree
    deliver(w, task, runs=2)
    w.use_run("ceo")  # after the final result: not part of it
    (case,) = w.history.cases("ceo", SERVICE)
    assert case.runs == 4


def test_an_open_case_counts_the_runs_up_to_now(w: ReflectionWorld) -> None:
    define(w)
    ask(w)
    w.use_run("ceo")
    w.use_run("ceo/qa")
    (case,) = w.history.cases("ceo", SERVICE)
    assert case.runs == 2


def test_the_window_ends_where_the_next_task_to_the_owner_begins(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w, "a")
    w.use_run("ceo")
    second = ask(w, "b")  # a second case begins while the first is still open
    w.use_run("ceo")
    w.use_run("ceo")
    one, two = w.history.cases("ceo", SERVICE)
    assert (one.id, two.id) == (first.id, second.id) and (one.runs, two.runs) == (1, 2)


def test_the_playbook_is_the_one_the_request_was_sent_under(w: ReflectionWorld) -> None:
    define(w)
    before = ask(w, "a")
    deliver(w, before)
    revise(w)
    after = ask(w, "b")
    one, two = w.history.cases("ceo", SERVICE)
    assert (one.id, one.playbook, two.id, two.playbook) == (before.id, 0, after.id, 1)


def test_the_version_used_is_the_one_in_force_when_the_case_was_first_answered(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    revise(w)  # the owner revises the playbook right after the request arrives ...
    deliver(w, task)  # ... and the request is delivered under the new version
    (case,) = w.history.cases("ceo", SERVICE)
    assert (case.playbook, case.used) == (0, 1)


def test_an_unanswered_case_uses_the_version_in_force_now(w: ReflectionWorld) -> None:
    define(w)
    ask(w)
    revise(w)
    (case,) = w.history.cases("ceo", SERVICE)
    assert case.used == 1


def test_requests_from_before_the_service_was_created_again_are_not_part_of_it(w: ReflectionWorld) -> None:
    define(w)
    old = ask(w, "old")
    w.s.commands.retire_service("root", "ceo", SERVICE, "obsolete")
    w.s.d.clock.advance(1)
    define(w)
    new = ask(w, "new")
    assert [c.id for c in w.history.cases("ceo", SERVICE)] == [new.id] != [old.id]


# ------------------------------------------------------------------------------ case_of


def test_every_task_of_a_chain_finds_its_case(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w)
    again = rework(w, first, budget=2)
    for task in (first, again):
        case = w.history.case_of(task)
        assert case is not None and case.id == first.id


def test_a_task_that_is_not_a_service_request_has_no_case(w: ReflectionWorld) -> None:
    plain = w.s.d.post(Message(sender="root", to="ceo", type="task", body="b", title="plain", budget=2))
    assert w.history.case_of(plain) is None


def test_a_request_to_an_unknown_agent_has_no_case(w: ReflectionWorld) -> None:
    ghost = Message(sender="root", to="ghost", type="task", body="b", service=SERVICE, id="T1")
    assert w.history.case_of(ghost) is None


def test_a_request_of_a_retired_service_has_no_case(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    w.s.commands.retire_service("root", "ceo", SERVICE, "obsolete")
    assert w.history.case_of(task) is None


# ------------------------------------------------------------------------------ the timeline of the playbook


def test_the_timeline_lists_every_version_with_its_time_oldest_first(w: ReflectionWorld) -> None:
    define(w)
    revise(w, STEPS, "one")
    revise(w, STEPS + "\n4. More.", "two")
    timeline = w.history.playbook_timeline("ceo", SERVICE)
    assert [v for v, _ in timeline] == [1, 2] and timeline[0][1] < timeline[1][1]


def test_a_service_without_a_playbook_has_an_empty_timeline(w: ReflectionWorld) -> None:
    define(w)
    assert w.history.playbook_timeline("ceo", SERVICE) == []
    assert w.history.playbook_timeline("ceo", "nope") == []


def test_the_implementations_read_the_same_world(history: CaseHistory) -> None:
    assert history.cases("ceo", SERVICE) == []


# ------------------------------------------------------------------------------ chains (0b 4.1)


def test_chains_without_since_keep_every_request(w: ReflectionWorld) -> None:
    define(w)
    old = ask(w, "old")
    w.s.commands.retire_service("root", "ceo", SERVICE, "obsolete")
    w.s.d.clock.advance(1)
    define(w)
    new = ask(w, "new")
    assert [c.id for c in w.history.cases("ceo", SERVICE)] == [new.id]
    assert [c.id for c in w.history.chains("ceo", SERVICE, since=None, runs=True)] == [old.id, new.id]


def test_chains_since_a_time_keep_the_requests_at_or_after_it(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w, "a")
    w.s.d.clock.advance(1)
    second = ask(w, "b")
    w.s.d.clock.advance(1)
    third = ask(w, "c")
    since = msg_time(second)
    assert since is not None and msg_time(first) is not None and msg_time(third) is not None
    assert [c.id for c in w.history.chains("ceo", SERVICE, since=since, runs=True)] == [second.id, third.id]  # at the time itself: kept
    assert [c.id for c in w.history.chains("ceo", SERVICE, since=since + timedelta(microseconds=1), runs=True)] == [third.id]


def test_chains_with_runs_false_read_no_run_log_charter_or_playbook(w: ReflectionWorld) -> None:
    """Mail only: a run counter and a playbook timeline that raise are never asked, and the run numbers are 0."""
    define(w)
    first = ask(w)
    w.use_run("ceo")
    deliver(w, first, runs=2, budget=1)
    relayed = rework(w, first, source="relayed", budget=3)
    revise(w)
    mail_only = DerivedCaseHistory(w.s.catalog, w.s.d.agents, w.s.d.mail, w.s.hints, _Refusing(), _Refusing())
    (case,) = mail_only.chains("ceo", SERVICE, since=None, runs=False)
    assert (case.runs, case.relayed_runs, case.used) == (0, 0, 0)
    assert [t.id for t in case.tasks] == [first.id, relayed.id] and (case.returned, case.relayed_returned, case.budget) == (1, 0, 13)


def test_cases_equal_chains_since_the_contract_created_with_runs(w: ReflectionWorld) -> None:
    define(w)
    old = ask(w, "old")
    w.s.commands.retire_service("root", "ceo", SERVICE, "obsolete")
    w.s.d.clock.advance(1)
    define(w)
    first = ask(w, "new")
    w.use_run("ceo")
    deliver(w, first, runs=2, budget=1)
    rate(w, first, "reject", "No.")
    deliver(w, rework(w, first, budget=3), runs=1)
    contract = w.s.catalog.read_contract("ceo", SERVICE)
    assert contract is not None and contract.created is not None and old.id != first.id
    assert w.history.cases("ceo", SERVICE) == w.history.chains("ceo", SERVICE, since=contract.created, runs=True) != []


def test_chains_need_no_contract(w: ReflectionWorld) -> None:
    """A request of a service nobody defined (or whose contract cannot be read) still has its chain; ``cases`` stays ``[]`` without a contract."""
    task = w.s.d.post(Message(sender="root", to="ceo", type="task", body="b", title="t", service=SERVICE, budget=4))
    assert w.history.cases("ceo", SERVICE) == []
    (case,) = w.history.chains("ceo", SERVICE, since=None, runs=True)
    assert (case.id, case.owner, case.service, case.client_kind) == (task.id, "ceo", SERVICE, "human")


class _Refusing(RunCounter, PlaybookTimelines):
    """A run counter and a playbook timeline that fail the test when asked."""

    def runs_between(self, team: Sequence[str], start: str, end: str | None) -> int:
        raise AssertionError("a run log was read")

    def stamps(self, team: Sequence[str], start: str, end: str | None) -> list[tuple[str, bool]]:
        raise AssertionError("a run log was read")

    def timeline(self, owner: str, service: str) -> list[tuple[int, datetime]]:
        raise AssertionError("a playbook was read")
