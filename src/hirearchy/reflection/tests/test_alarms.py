"""The repeat and cost alarms over the judged cases of a record (design 6): pure rules over values.

The tests build the cases, the deliveries (``deliveries_of``), the assertions (``regressions``) and the record by hand; message ids order like the number
of seconds in them, so case ``k`` is made of the seconds ``100 k`` onwards."""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction

import pytest

from hirearchy.kernel import Message, latest_results, link_ids, msg_time, verdict_tier
from hirearchy.reflection import (
    QUALITY_DEFAULTS, Case, CostAlarm, CostCase, QualityThresholds, RepeatAlarm, ServiceRecord, Verdict, case_spend, cost_alarm, deliveries_of, judged_cases,
    over_cost, regressions, repeat_alarm, user_approved, user_cost,
)

OWNER = "ceo"
T = QualityThresholds()  # min_judged 3, window 3, failures 2, ratio 1.25


def ident(n: int, sender: str = "ceo") -> str:
    return f"20260101T00{n // 60:02d}{n % 60:02d}000000-{sender.replace('/', '-')}-{n:04d}"


def task(n: int, budget: int = 10) -> Message:
    return Message(sender="root", to=OWNER, type="task", body="b", title=f"t{n}", id=ident(n, "root"), service="s", budget=budget)


def done(for_task: Message, n: int, status: str = "done") -> Message:
    return Message(sender=OWNER, to="root", type="result", body="Delivered.", id=ident(n), reply_to=for_task.id, status=status)


def verdict(
    on: Message, n: int, kind: str, *, links: tuple[str, ...] = (), link_source: str | None = "human", tier: str = "human", own: tuple[str, ...] = (),
) -> Verdict:
    """A verdict of ``kind`` on ``on`` sent at second ``n`` (source ``tier``, its own ``criterion`` field ``own``) with one link note naming ``links``, sent
    a second later."""
    note = Message(
        sender="root", to=OWNER, type="note", body="no", id=ident(n, "root"), reply_to=on.id, feedback=kind, source=tier, criterion=", ".join(own) or None,
    )
    link_notes: list[Message] = []
    confirmed: tuple[str, ...] = ()
    link_tier = ""
    if links:
        link = Message(sender="root", to=OWNER, type="note", body="link", id=ident(n + 1, "root"), reply_to=note.id, criterion=", ".join(links), source=link_source)
        link_notes.append(link)
        link_tier = verdict_tier(link)
        confirmed = tuple(x for x in link_ids(link) if x.startswith("C")) if link_tier == "human" else ()
    return Verdict(kind, "no", msg_time(note), on.id, 0, note, tier=tier, links=links, links_tier=link_tier, confirmed=confirmed, link_notes=tuple(link_notes))


@dataclass
class Spec:
    """One case of a record: its verdict (``reject`` with ``links``, ``accept``, or none) and the figures of its runs."""

    verdict: str | None = "reject"
    links: tuple[str, ...] = ()
    link_source: str | None = "human"
    on_a_blocked_result: bool = False  # the verdict is given on a blocked result, before the done one: it is on no delivery
    state: str = "done"  # done | failed | blocked | open (an open case has no result)
    runs: int = 4
    handed: int = 10  # the budget of its task
    over: dict[str, object] | None = None  # Case fields to override
    own: tuple[str, ...] = ()  # the rejection's own `criterion` field: the assistant's reading, before any link note


def make(specs: list[Spec], *, budget: int = 10, service: str = "s", client_kind: str = "human") -> ServiceRecord:
    cases: list[Case] = []
    finals: list[Message] = []
    for k, spec in enumerate(specs, start=1):
        base = 100 * k
        t = task(base + 1, spec.handed)
        verdicts: list[Verdict] = []
        if spec.state == "open":
            pass
        elif spec.on_a_blocked_result:
            finals.append(done(t, base + 10, "blocked"))
            if spec.verdict:
                verdicts.append(verdict(t, base + 20, spec.verdict, links=spec.links, link_source=spec.link_source, own=spec.own))
            finals.append(done(t, base + 30))  # the done result comes after the verdict
        else:
            finals.append(done(t, base + 10, "done" if spec.state == "done" else spec.state))
            if spec.verdict:
                verdicts.append(verdict(t, base + 20, spec.verdict, links=spec.links, link_source=spec.link_source, own=spec.own))
        result = next((r for r in reversed(finals) if r.reply_to == t.id), None)
        case = Case(
            id=t.id, service=service, owner=OWNER, tasks=[t], result=result, state=spec.state, playbook=0, used=0, reworks=0, budget=spec.handed, runs=spec.runs,
            lessons=[], verdicts=verdicts, started=None, finished=None, client_kind=client_kind,
        )
        cases.append(replace(case, **(spec.over or {})))  # type: ignore[arg-type]  # the fields a test overrides are the Case's own
    results = latest_results(finals)
    deliveries = tuple(d for c in cases for d in deliveries_of(c, results, {}))
    return ServiceRecord(OWNER if service else "", service, "root", client_kind, budget=budget, cases=tuple(cases), deliveries=deliveries, assertions=tuple(regressions(cases)))


def rejecting(*links: str, **kw: object) -> Spec:
    return Spec("reject", tuple(links), **kw)  # type: ignore[arg-type]


# ------------------------------------------------------------------------------------------------------------------------ judged cases


def test_judged_cases_are_ordered_by_their_latest_counted_verdict() -> None:
    record = make([Spec("accept"), Spec(None), Spec("reject"), Spec("accept")])
    first, _, third, fourth = record.cases
    assert [c.id for c in judged_cases(record)] == [first.id, third.id, fourth.id]  # the case without a verdict is not judged
    # a verdict given later to an earlier case moves it after the others
    later = replace(record.cases[0], verdicts=[*record.cases[0].verdicts, verdict(task(101), 900, "accept")])
    delivery = replace(record.deliveries[0], verdicts=(*record.deliveries[0].verdicts, later.verdicts[-1]))
    moved = replace(record, cases=(later, *record.cases[1:]), deliveries=(delivery, *record.deliveries[1:]))
    assert [c.id for c in judged_cases(moved)] == [third.id, fourth.id, first.id]


def test_a_verdict_on_a_blocked_result_does_not_make_a_case_judged() -> None:
    record = make([Spec("reject", on_a_blocked_result=True), Spec("accept")])
    assert [c.id for c in judged_cases(record)] == [record.cases[1].id]


# ------------------------------------------------------------------------------------------------------------------------ repeat


@pytest.mark.parametrize("judged", [0, 1, 2])
def test_repeat_reads_n_a_below_min_judged_at_0_1_and_2_judged_cases(judged: int) -> None:
    alarm = repeat_alarm(make([rejecting("C1") for _ in range(judged)]), T)
    assert alarm == RepeatAlarm("n/a", judged)


def test_repeat_looks_at_the_last_window_judged_cases() -> None:
    # C1 failed in the first two cases only: outside the last three, it does not fire
    record = make([rejecting("C1"), rejecting("C1"), rejecting("C2"), rejecting("C3"), rejecting("C4")])
    alarm = repeat_alarm(record, T)
    assert alarm.state == "no" and alarm.window == tuple(c.id for c in record.cases[2:])
    assert [s for s, _ in alarm.subjects] == ["R3", "R4", "R5", "C2", "C3", "C4"] and {n for _, n in alarm.subjects} == {1}
    wider = repeat_alarm(record, replace(T, repeat_window=5))
    assert wider.state == "fires" and wider.fired == ("C1",) and wider.cases == (("C1", tuple(c.id for c in record.cases[:2])),)
    assert repeat_alarm(record, replace(T, repeat_window=5, repeat_failures=3)).state == "no"


def test_subjects_come_from_the_assertion_its_confirmed_ids_its_about_and_human_r_links() -> None:
    # R2 repeats R1 (a human link to R1, which is about C5); R3 names C6 and C7 by human links
    record = make([rejecting("C5"), rejecting("R1"), rejecting("C6", "C7")])
    alarm = repeat_alarm(record, T)
    assert alarm.state == "fires"
    # case 2: its assertion R2, the R1 it links (human), and what R1 is about (C5); case 3: R3, and C6, C7 (confirmed, and about)
    assert alarm.subjects == (("R1", 2), ("R2", 1), ("R3", 1), ("C5", 2), ("C6", 1), ("C7", 1))
    assert alarm.fired == ("R1", "C5")


def test_an_unconfirmed_link_is_never_a_subject_and_is_listed_as_not_counted_under_every_state() -> None:
    relayed = rejecting("C6", "C3", link_source="relayed")  # only the assistant's reading names them
    two = make([relayed, rejecting("C1")])
    alarm = repeat_alarm(two, T)  # 2 of 3 judged cases: n/a, and the reading is listed all the same
    assert alarm.state == "n/a" and alarm.not_counted == (("R1", ("C6", "C3")),)
    three = make([relayed, rejecting("C1"), rejecting("C1")])
    assert [s for s, _ in repeat_alarm(three, T).subjects] == ["R1", "R2", "R3", "C1"]  # C6 and C3 are no subject, R1 itself is
    assert repeat_alarm(three, T).not_counted == (("R1", ("C6", "C3")),)
    fires = repeat_alarm(make([rejecting("C1"), rejecting("C1"), rejecting("C1"), relayed]), T)
    assert fires.state == "fires" and fires.not_counted == (("R4", ("C6", "C3")),)
    assert repeat_alarm(make([rejecting("C1", link_source="relayed")] * 3), T).state == "no"


def test_below_min_judged_every_judged_case_contributes_its_readings_and_above_only_the_window() -> None:
    relayed = rejecting("C9", link_source="relayed")
    record = make([relayed, rejecting("C1"), rejecting("C1"), rejecting("C1")])
    assert repeat_alarm(record, T).not_counted == ()  # the window is the last three: the relayed reading is outside it
    assert repeat_alarm(make([relayed, rejecting("C1")]), T).not_counted == (("R1", ("C9",)),)


def test_a_rejection_not_on_a_delivery_gives_no_subject() -> None:
    record = make([rejecting("C1", on_a_blocked_result=True), rejecting("C2"), rejecting("C2"), Spec("accept")])
    alarm = repeat_alarm(record, T)
    assert alarm.judged == 3 and alarm.state == "fires" and alarm.fired == ("C2",)
    assert "C1" not in dict(alarm.subjects) and "R1" not in dict(alarm.subjects)  # the first case has no judged delivery; its rejection names nothing


def test_two_subjects_fire_listed_r_ids_then_c_ids_by_number() -> None:
    record = make([rejecting("C11", "C2"), rejecting("C2", "C11"), rejecting("R1", "R2"), rejecting("C2")])
    alarm = repeat_alarm(record, replace(T, repeat_window=4, repeat_failures=2))
    assert alarm.state == "fires"
    assert alarm.fired == ("R1", "R2", "C2", "C11")  # R ids first, then C ids, each by number (C2 before C11)
    assert [s for s, _ in alarm.subjects] == ["R1", "R2", "R3", "R4", "C2", "C11"]
    assert alarm.cases[0][0] == "R1"


def test_a_no_alarm_lists_the_subjects_it_counted() -> None:
    record = make([rejecting("C1"), rejecting("C2"), rejecting("C3")])
    alarm = repeat_alarm(record, T)
    assert alarm.state == "no" and alarm.fired == () and [s for s, _ in alarm.subjects] == ["R1", "R2", "R3", "C1", "C2", "C3"]


def test_one_off_records_read_does_not_apply() -> None:
    record = make([rejecting() for _ in range(4)], service="")
    alarm = repeat_alarm(record, T)
    assert (alarm.state, alarm.judged) == ("does not apply", 4) and alarm.window == () and alarm.fired == ()


def test_not_counted_ids_keep_the_rejections_recorded_order() -> None:
    record = make([rejecting("C9", "C3", "R7", link_source="relayed"), rejecting("C1"), rejecting("C1")])
    assert repeat_alarm(record, T).not_counted == (("R1", ("C9", "C3", "R7")),)  # not sorted: the order the rejection recorded


def test_a_rejections_own_reading_that_a_human_link_does_not_confirm_is_listed_as_not_counted() -> None:
    """Design 9.3, DR2-3 (s1r): the rejection's own `criterion` says C5, the user's link says C9: the reading C5 is not confirmed by any human link, so it is
    listed, under every state, and it is no subject; the confirmed C9 is."""
    record = make([rejecting("C9", own=("C5",))])
    alarm = repeat_alarm(record, T)
    assert alarm.state == "n/a" and alarm.not_counted == (("R1", ("C5",)),)
    three = make([rejecting("C9", own=("C5",)), rejecting("C9"), rejecting("C1")])
    alarm = repeat_alarm(three, T)
    assert alarm.not_counted == (("R1", ("C5",)),) and "C5" not in dict(alarm.subjects) and dict(alarm.subjects)["C9"] == 2 and alarm.fired == ("C9",)


def test_a_reading_that_a_human_link_names_too_is_confirmed_and_not_listed() -> None:
    record = make([rejecting("C9", "C3", own=("C3", "C5")), rejecting("C1", own=("C1",)), rejecting("C1")])
    assert repeat_alarm(record, T).not_counted == (("R1", ("C5",)),)  # C3 is confirmed by the link, C1 likewise; only C5 is left
    assert repeat_alarm(make([rejecting("none", own=("C5",))]), T).not_counted == (("R1", ("C5",)),)  # "none" confirms nothing
    assert repeat_alarm(make([rejecting("C9"), rejecting("C1")]), T).not_counted == ()  # no own reading: nothing to list


def test_the_thresholds_are_the_defaults_of_the_design() -> None:
    assert (T.min_judged, T.repeat_window, T.repeat_failures, T.cost_ratio) == (3, 3, 2, Fraction("1.25")) and QUALITY_DEFAULTS["min_judged"] == 3


# ------------------------------------------------------------------------------------------------------------------------ cost


def spent(user: int, **over: object) -> Spec:
    """A judged case whose user's runs are ``user`` (a finished case: its runs, less the relayed ones)."""
    return Spec("accept", runs=user, over=dict(over))


@pytest.mark.parametrize("judged", [0, 1, 2])
def test_cost_reads_n_a_below_min_judged(judged: int) -> None:
    alarm = cost_alarm(make([spent(30) for _ in range(judged)]), T)
    assert alarm == CostAlarm("n/a", judged, judged)  # the cases are compared in the data, the alarm is not evaluated


def test_cost_fires_strictly_above_the_ratio_exact_at_1_25_times_20_is_25() -> None:
    budget = 20
    at = cost_alarm(make([spent(25), spent(4), spent(4)], budget=budget), T)
    assert (at.state, at.compared, at.cases) == ("no", 3, ())  # 25 is exactly 1.25 x 20
    over = cost_alarm(make([spent(26), spent(4), spent(4)], budget=budget), T)
    assert over.state == "fires" and over.cases == (CostCase(over.cases[0].case, 26, 20, 0, 26),) and over.cases[0].ratio == Fraction(13, 10)
    assert not over_cost(make([spent(25)], budget=20).cases[0], 20, Fraction("1.25")) and over_cost(make([spent(26)], budget=20).cases[0], 20, Fraction("1.25"))
    assert over_cost(make([spent(3)]).cases[0], 2, Fraction(1)) and not over_cost(make([spent(2)]).cases[0], 2, Fraction(1))


def test_a_threshold_of_the_ratio_is_used_exactly() -> None:
    record = make([spent(11), spent(1), spent(1)], budget=10)
    assert cost_alarm(record, T).state == "no"  # 1.1x
    assert cost_alarm(record, replace(T, cost_ratio=Fraction("1.05"))).state == "fires"


def test_a_user_approved_of_zero_is_skipped_by_name_as_budget_0() -> None:
    record = make([spent(5), spent(5), spent(5)], budget=0)
    alarm = cost_alarm(record, T)
    assert (alarm.state, alarm.compared) == ("n/a", 0) and alarm.skipped == tuple((c.id, "budget 0") for c in record.cases)
    below = make([spent(5), spent(5), spent(5)], budget=-3)
    assert cost_alarm(below, T).skipped == tuple((c.id, "budget 0") for c in below.cases)
    raised = make([spent(5, user_ceiling=7), spent(5), spent(5)], budget=0)  # a ceiling the user's hand-downs set approves runs all the same
    assert cost_alarm(raised, T).skipped == tuple((c.id, "budget 0") for c in raised.cases[1:]) and cost_alarm(raised, T).compared == 1


def test_runs_not_counted_are_skipped_by_name() -> None:
    record = make([spent(5), spent(40, runs_unknown="no run log in its window"), spent(5), spent(5)])
    alarm = cost_alarm(record, T)
    assert (alarm.state, alarm.compared) == ("no", 3) and alarm.skipped == ((record.cases[1].id, "runs not counted"),)


def test_three_judged_cases_whose_runs_are_all_not_counted_read_n_a_0_of_0_compared() -> None:
    record = make([spent(0, runs_unknown="no run log in its window") for _ in range(3)])
    alarm = cost_alarm(record, T)
    assert (alarm.state, alarm.judged, alarm.compared, alarm.cases) == ("n/a", 3, 0, ())  # never "no": nothing was compared
    assert [reason for _, reason in alarm.skipped] == ["runs not counted"] * 3


def test_skipped_cases_are_listed_under_every_state() -> None:
    skipped = spent(9, runs_unknown="assignee retired")
    below = cost_alarm(make([skipped, spent(5)]), T)
    assert below.state == "n/a" and below.skipped == ((make([skipped, spent(5)]).cases[0].id, "runs not counted"),)
    fires = make([skipped, spent(40), spent(5), spent(5)])
    alarm = cost_alarm(fires, T)
    assert alarm.state == "fires" and alarm.skipped == ((fires.cases[0].id, "runs not counted"),)
    no = cost_alarm(make([skipped, spent(5), spent(5), spent(5)]), T)
    assert no.state == "no" and len(no.skipped) == 1


def test_open_and_blocked_cases_include_the_users_runs_still_out() -> None:
    # an open case: 6 runs used and 4 of the 10 handed down still out -> the user's runs are 10, the contract's 10 per request approved
    held = Spec("accept", state="open", runs=6, handed=10)
    record = make([held, Spec("accept"), Spec("accept"), Spec("accept")], budget=10)
    case = record.cases[0]
    assert case.state == "open" and user_cost(case) == 10 == case_spend(case)
    assert cost_alarm(record, T).state == "no"
    # a blocked case: 14 used and 6 of the 20 handed down still out -> 20 against 10 approved, 2.00x
    blocked = make([replace(held, state="blocked", runs=14, handed=20), Spec("accept"), Spec("accept"), Spec("accept")], budget=10)
    alarm = cost_alarm(blocked, T)
    assert alarm.state == "fires" and alarm.cases == (CostCase(blocked.cases[0].id, 20, 10, 0, 20),)


def test_cost_compares_the_users_runs_with_the_users_approved_runs_and_shows_relayed_apart() -> None:
    # 30 runs in all, 16 of them the assistant's relayed reworks: the user's 14 are below the 1.25 x 12 = 15 they approved
    relayed = {"relayed_runs": 16, "relayed_reworks": 2}
    record = make([spent(30, **relayed), spent(2), spent(2)], budget=12)
    assert cost_alarm(record, T).state == "no"
    fires = make([spent(30, relayed_runs=10, relayed_reworks=1), spent(2), spent(2)], budget=12)  # the user's 20 are above 15
    alarm = cost_alarm(fires, T)
    assert alarm.state == "fires" and alarm.cases == (CostCase(fires.cases[0].id, 20, 12, 10, 30),)
    raised = make([spent(30, relayed_runs=10, user_ceiling=20), spent(2), spent(2)], budget=12)  # the user's hand-downs raised the approval to 20
    assert user_approved(raised.cases[0], 12) == 20 and cost_alarm(raised, T).state == "no"  # 20 is below 1.25 x 20


def test_the_alarm_and_case_total_read_one_user_spend_and_one_approved_rule(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from hirearchy.reflection.testing import memory_world

    from ._support import SERVICE, ask, define, deliver, populated, rate, rework

    # the contract's 10 per request: 13 runs are the user's cost, 10 the approval
    plain = tmp_path / "plain"
    plain.mkdir()
    w = populated(memory_world(plain))
    define(w)
    first = ask(w)
    deliver(w, first, runs=13)
    w.s.d.clock.advance(1)
    rate(w, first, "accept", "fine")
    record = w.records.records(SERVICE)[0]
    (case,) = record.cases
    alarm = cost_alarm(record, QualityThresholds(min_judged=1))
    (entry,) = alarm.cases
    assert alarm.state == "fires" and (entry.user_cost, entry.user_approved) == (user_cost(case), user_approved(case, record.budget)) == (13, 10)
    assert f"{entry.user_cost} runs used" in w.reports.case_total(first) and f"per-request budget of {entry.user_approved}" in w.reports.case_total(first)

    # the user's own rework raised the approval to 20: 27 runs are the cost, and case_total warns of the same two figures
    raised = tmp_path / "raised"
    raised.mkdir()
    v = populated(memory_world(raised))
    define(v)
    head = ask(v)
    deliver(v, head, runs=2)
    v.s.d.clock.advance(1)
    rate(v, head, "reject", "again please")
    again = rework(v, head, budget=10)
    deliver(v, again, runs=25)
    v.s.d.clock.advance(1)
    rate(v, again, "accept", "fine")
    record = v.records.records(SERVICE)[0]
    (case,) = record.cases
    (entry,) = cost_alarm(record, QualityThresholds(min_judged=1)).cases
    assert (entry.user_cost, entry.user_approved) == (27, 20) == (user_cost(case), user_approved(case, record.budget))
    assert f"cost {entry.user_cost} runs, more than the {entry.user_approved} the user approved" in v.reports.case_total(again)


def test_an_agent_clients_case_never_alarms() -> None:
    record = make([Spec(None, runs=90) for _ in range(4)], client_kind="agent")  # an agent client's verdicts are hypotheses: none is judged
    assert repeat_alarm(record, T) == RepeatAlarm("n/a", 0)
    assert cost_alarm(record, T).state == "n/a" and cost_alarm(record, T).cases == ()
