"""The text of the quality view (0b 9.2), over records put together by hand: ``ratio``, the service block line by line, and the nested line."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from hirearchy.kernel import ROOT
from hirearchy.progress._quality_facts import RecordView
from hirearchy.progress._quality_render import nested_line, ratio, service_block
from hirearchy.reflection import (
    Assertion, BarChanges, Case, Cause, CharterMark, ContractMark, Delivery, ModelMark, PlaybookMark, QualityThresholds, ServiceRecord, TopUpMark,
    shown_name,
)

from ._quality_records import (
    OWNER, case, delivery, mid, record, request, top_ups, verdict,
)

T = QualityThresholds()
EMPTY = "  judged by the user: n/a (0 of 0) deliveries; without a verdict: 0 case(s); not as delivered: 0"


def block(r: ServiceRecord, t: QualityThresholds = T, **view: Any) -> list[str]:
    return service_block(RecordView(r, **view), t)


def made(n: int, kind: str | None = None, words: str = "", *, state: str = "done", signer: str = OWNER, **more: Any) -> tuple[Case, Delivery]:
    """A case of one request (minute ``n``), delivered at ``n + 1`` and, when ``kind`` is given, judged at ``n + 2``."""
    t = request(n)
    v = verdict(t, n + 2, kind, words) if kind else None
    c = case([t], state=state, verdicts=[v] if v else [], **more)
    return c, delivery(c, 0, result_n=n + 1, signer=signer, verdicts=(v,) if v else ())


def line(lines: list[str], start: str) -> str:
    return next(x for x in lines if x.startswith(start))


def row(lines: list[str]) -> str:
    """The first escape row of a block."""
    return next(x for x in lines if x.startswith("    R1 case"))


# ------------------------------------------------------------------------------------------------------------------------ ratio


def test_ratio_of_zero_is_n_a_never_a_pass() -> None:
    assert ratio(0, 0) == "n/a (0 of 0)"
    assert ratio(3, 6) == "3 of 6"
    assert ratio(0, 5) == "0 of 5"


@pytest.mark.parametrize("which", ["judged coverage", "escapes", "verifier escapes", "pass precision"])
def test_every_rate_with_a_zero_denominator_reads_n_a(which: str) -> None:
    empty = block(record())
    if which == "judged coverage":
        assert line(empty, "  judged by the user:") == EMPTY
    elif which == "escapes":
        assert line(empty, "  escapes") == "  escapes (the team reported done, then the user rejected it): none (judged: n/a (0 of 0))"
    else:  # a signer none of whose deliveries was judged
        c, d = made(3, signer="lead/reviewer")
        out = block(record(cases=[c], deliveries=(d,)))
        assert "    lead/reviewer: escapes n/a (0 of 0) judged; PASS precision n/a (0 of 0); its FAILs before delivery: 0 re-check(s), 0 author rework run(s)" in out


# ------------------------------------------------------------------------------------------------------------------------ the heading and the cases


def test_the_heading_line() -> None:
    head = "weekly-memo (offered by lead; client: you, human; unit: case; contract v3, playbook v1; approved 15 runs per request)"
    assert block(record())[0] == head
    assert block(record(playbook=0))[0] == head.replace("playbook v1", "no playbook")


def test_the_cases_line_partitions_the_states_with_stalled_inside_open() -> None:
    cases = [made(3)[0], made(6, state="failed")[0], made(9, state="blocked")[0], made(12, state="open")[0], made(15, state="open")[0]]
    out = block(record(cases=cases), stalled={cases[3].id: True, cases[4].id: False})
    assert out[1] == "  cases: 5 (done 1, failed 1, blocked 1, open 2 (stalled 1))"
    assert block(record(cases=cases), stalled_error="boom")[1] == "  cases: 5 (done 1, failed 1, blocked 1, open 2 (stalled: unknown (boom)))"
    left = block(record(cases=cases), left_blocked=frozenset({cases[2].tasks[-1].id, "somebody-else"}))
    assert left[1] == "  cases: 5 (done 1, failed 1, blocked 1, open 2 (stalled 0)); 1 blocked and moved past without a verdict"


# ------------------------------------------------------------------------------------------------------------------------ first deliveries


def test_the_first_deliveries_line_and_one_line_per_case() -> None:
    a, da = made(3, "reject", "Not right.")
    b, db = made(9, "accept", "Good.")
    c, dc = made(15, "accept", "")
    first, second = request(21), request(25, source="relayed", revises=mid(21))
    d = case([first, second])
    dd = delivery(d, 0, result_n=22, superseded=second.id)
    e = case([request(31)], state="blocked")
    f, df = made(37, "accept", "Late.")
    df = delivery(f, 0, result_n=38, verdicts=df.verdicts, edited_at=1, edited=True)  # the file changed before the verdict: the verdict is voided
    out = block(record(cases=[a, b, c, d, e, f], deliveries=(da, db, dc, dd, df)))
    assert out[2:10] == [
        "  first deliveries: 2 accepted, 1 rejected, 1 without a verdict (1 superseded by a rework before a verdict), 1 judged after the file changed (neither)"
        "; 1 never delivered",
        f'    {a.id}: rejected: "Not right."',
        f'    {b.id}: accepted: "Good."',
        f"    {c.id}: accepted (no words)",
        f"    {d.id}: no verdict (superseded by your relayed rework {second.id})",
        f"    {e.id}: never delivered (blocked)",
        f"    {f.id}: judged after the file changed (neither): the user's verdict came after the file was changed",
        "  judged by the user: 3 of 5 deliveries; without a verdict: 1 case(s) (" + d.id + "): never counted as accepted; not as delivered: 1 (" + df.task.id + "); "
        "1 judged after the file changed: neither pass nor escape (" + df.task.id + ") (compared with the team's current files: no org history)",
    ]


@pytest.mark.parametrize(
    ("source", "tail"),
    [("human", "human rework"), ("relayed", "your relayed rework"), (None, "rework")],
)
def test_a_superseded_first_delivery_names_the_tier_of_the_rework(source: str | None, tail: str) -> None:
    first, second = request(3), request(9, source=source, revises=mid(3))
    c = case([first, second])
    out = block(record(cases=[c], deliveries=(delivery(c, 0, result_n=4, superseded=second.id),)))
    suffix = " (tier not recorded)" if source is None else ""
    assert f"    {c.id}: no verdict (superseded by {tail} {second.id}{suffix})" in out


def test_the_first_delivery_is_the_lowest_step_delivery_of_the_case() -> None:
    first, second = request(3), request(9, revises=mid(3), source="human")
    c = case([first, second], verdicts=[verdict(second, 11, "reject", "Still wrong.", step=1)])
    head_blocked = delivery(c, 1, result_n=10, verdicts=(c.verdicts[0],))  # the head was blocked: only the rework was delivered
    out = block(record(cases=[c], deliveries=(head_blocked,)))
    assert out[2].startswith("  first deliveries: 0 accepted, 1 rejected, 0 without a verdict") and "never" not in out[2]
    assert out[3] == f'    {c.id}: rejected: "Still wrong."'
    both = case([first, second], verdicts=[verdict(first, 5, "accept", "First.", step=0), verdict(second, 11, "reject", "Second.", step=1)])
    later = delivery(both, 1, result_n=10, verdicts=(both.verdicts[1],))
    earlier = delivery(both, 0, result_n=4, verdicts=(both.verdicts[0],))
    out = block(record(cases=[both], deliveries=(later, earlier)))  # listed the wrong way round: the lowest step still wins
    assert out[3] == f'    {both.id}: accepted: "First."'


def test_never_delivered_only_when_no_task_was_delivered() -> None:
    blocked, failed, open_ = (case([request(n)], state=s) for n, s in ((3, "blocked"), (6, "failed"), (9, "open")))
    out = block(record(cases=[blocked, failed, open_]))
    assert out[2].endswith("; 3 never delivered")
    assert out[3:6] == [f"    {blocked.id}: never delivered (blocked)", f"    {failed.id}: never delivered (failed)", f"    {open_.id}: never delivered (open)"]
    delivered, d = made(12)
    assert "never delivered" not in block(record(cases=[delivered], deliveries=(d,)))[2]


# ------------------------------------------------------------------------------------------------------------------------ the judged line


def test_the_judged_line_with_unjudged_relayed_only_and_not_as_delivered_parts() -> None:
    plain, dp = made(3)
    relayed, dr = made(9)
    dr = Delivery(dr.case, dr.task, dr.result, 0, OWNER, (verdict(relayed.tasks[0], 11, "accept", "ok", source="relayed"),), "", 0, False, False)
    given_task, rework = request(15), request(21, source="relayed", revises=mid(15))
    seen = case([given_task, rework])
    d_seen, d_later = delivery(seen, 0, result_n=16, given=True), delivery(seen, 1, result_n=22)
    judged, dj = made(27, "accept", "yes")
    out = block(record(cases=[plain, relayed, seen, judged], deliveries=(dp, dr, d_seen, d_later, dj), history=BarChanges(known=True)))
    text = (
        f"  judged by the user: 1 of 5 deliveries; without a verdict: 3 case(s) ({plain.id}, {relayed.id}, {seen.id}): never counted as accepted"
        f" (1 with only your own relayed verdict); 1 later relayed delivery(ies) the user was not given ({seen.id}); not as delivered: 0"
    )
    assert line(out, "  judged by the user:") == text


def test_the_no_history_remark_only_when_a_not_as_delivered_file_is_counted() -> None:
    c, d = made(3, "accept", "ok")
    edited = delivery(c, 0, result_n=4, verdicts=d.verdicts, edited=True)  # not as delivered, and nothing voided (its time is not known)
    unknown = BarChanges()
    known = BarChanges(known=True)
    remark = " (compared with the team's current files: no org history)"
    assert block(record(cases=[c], deliveries=(edited,), history=unknown))[4].endswith(f"not as delivered: 1 ({c.id}){remark}")
    assert block(record(cases=[c], deliveries=(edited,), history=known))[4].endswith(f"not as delivered: 1 ({c.id})")
    assert block(record(cases=[c], deliveries=(d,), history=unknown))[4].endswith("not as delivered: 0")
    broken = block(record(cases=[c], deliveries=(edited,), files_error="the deliverable folders: boom", history=known))
    assert broken[4].endswith("not as delivered: unknown (the deliverable folders: boom)")


def test_the_legacy_and_not_on_a_delivery_line() -> None:
    task = request(3)
    legacy = verdict(task, 5, "accept", "old")
    legacy.message.source = None  # written before sources existed
    stray = verdict(task, 2, "reject", "too early", source="human")  # given before the done result at minute 4
    c = case([task], verdicts=[stray, legacy])
    d = delivery(c, 0, result_n=4, verdicts=(legacy,))
    out = block(record(cases=[c], deliveries=(d,)))
    legacy_part = "legacy verdicts (no source: read as the user's, the 0a rule): 1"
    stray_part = f"verdicts not on a delivery (on a blocked or failed result, or before the done result): 1 ({stray.message.id})"
    assert out[5] == f"  {legacy_part}; {stray_part}"
    only_stray = block(record(cases=[case([task], verdicts=[stray])], deliveries=()))
    assert f"  {stray_part}" in only_stray and not any("legacy verdicts" in x for x in only_stray)
    assert not any("verdicts not on a delivery" in x or "legacy verdicts" in x for x in block(record()))


# ------------------------------------------------------------------------------------------------------------------------ escapes and causes


def escape(n: int, cause: Cause, *, signer: str = OWNER, words: str = "No.", **more: Any) -> tuple[Case, Delivery, tuple[Delivery, Cause]]:
    c, d = made(n, "reject", words, signer=signer, **more)
    return c, d, (d, cause)


CAUSES = [
    (Cause("relayed-error", "relayed task", ("TASK",)), "relayed-error (the rejected delivery is your relayed rework TASK)"),
    (
        Cause("relayed-carry-over", "carry-over", ("R1", "a/b.md")),
        'relayed-carry-over (your relayed rework R1 delivered "a/b.md" after the delivery the user judged, and the rejected delivery lists it too)',
    ),
    (
        Cause("reviewer-miss", "link", ("LINK", "C2", "C5"), version=2),
        "reviewer-miss (the user's confirmed link LINK names C2, C5, which contract v2 of the task had; the team reported done)",
    ),
    (
        Cause("contract-gap", "answer", ("LINK", "C9"), version=1, answering=2),
        "contract-gap (the user's answer, link LINK, names C9, which contract v1 of the task did not have)",
    ),
    (
        Cause("contract-gap", "answer", ("LINK", "C6"), version=1, answering=3, removes=("C6",)),
        "contract-gap (the user's answer, link LINK, names C6, which the answering contract v3 removes)",
    ),
    (Cause("contract-gap", "words", ("always",)), "contract-gap (the user's words say \"always\")"),
    (Cause("untyped", "none"), "untyped (no rule matched)"),
    (Cause("untyped", "none", ("the user said it is no lasting rule",)), "untyped (the user said it is no lasting rule)"),
    (Cause("untyped", "unreadable", ("contract v4 is not stored",)), "untyped (the contract could not be read: contract v4 is not stored)"),
    (Cause("untyped", "unreadable", ("weekly-memo: does not parse (ScannerError)",)), "untyped (the contract could not be read: weekly-memo: does not parse (ScannerError))"),
]


@pytest.mark.parametrize(("cause", "words"), CAUSES, ids=[f"{c.type}-{c.rule}-{i}" for i, (c, _) in enumerate(CAUSES)])
def test_each_cause_text_of_5_3(cause: Cause, words: str) -> None:
    c, d, pair = escape(3, cause)
    v = d.verdicts[0]
    a = Assertion("R1", c.id, v, (), "")
    out = block(record(cases=[c], deliveries=(d,), escapes=(pair,), assertions=(a,)))
    assert f"    R1 case {c.id}, signed off by lead: {words}" in out
    assert out[out.index("  escapes (the team reported done, then the user rejected it): 1") + 1].endswith(words)


def test_the_also_and_before_verdict_tails() -> None:
    cause = Cause("reviewer-miss", "link", ("LINK", "C2"), also=("contract-gap", "relayed-error"), before_verdict="RELAYED", version=1)
    c, d, pair = escape(3, cause)
    a = Assertion("R1", c.id, d.verdicts[0], (), "")
    out = block(record(cases=[c], deliveries=(d,), escapes=(pair,), assertions=(a,)))
    tail = "; also contract-gap, relayed-error; your relayed rework RELAYED delivered after it and before the verdict: the user may have judged that version"
    assert row(out).endswith(f"which contract v1 of the task had; the team reported done){tail}")


def test_a_contract_gap_by_answer_splits_its_ids_between_the_two_clauses() -> None:
    cause = Cause("contract-gap", "answer", ("LINK", "C9", "C6", "C10"), version=1, answering=2, removes=("C6",))
    c, d, pair = escape(3, cause)
    out = block(record(cases=[c], deliveries=(d,), escapes=(pair,), assertions=(Assertion("R1", c.id, d.verdicts[0], (), ""),)))
    assert row(out).endswith(
        "contract-gap (the user's answer, link LINK, names C9, C10, which contract v1 of the task did not have, and C6, which the answering contract v2 removes)"
    )


# ------------------------------------------------------------------------------------------------------------------------ verifiers


def test_a_record_without_a_delivery_reads_no_delivery_yet() -> None:
    assert "  verifiers: none (no delivery yet)" in block(record())


def test_every_delivery_signed_by_the_owner_reads_itself() -> None:
    c, d = made(3, "accept", "ok")
    assert "  verifiers: none (every delivery was signed off by lead itself)" in block(record(cases=[c], deliveries=(d,)))


def test_a_signer_without_a_judged_delivery_reads_n_a() -> None:
    c, d = made(3, signer="lead/checker")
    out = block(record(cases=[c], deliveries=(d,)), fails={"lead/checker": (1, 2)})
    assert out[out.index("  verifiers:") + 1] == (
        "    lead/checker: escapes n/a (0 of 0) judged; PASS precision n/a (0 of 0); its FAILs before delivery: 1 re-check(s), 2 author rework run(s)"
    )


def test_a_signers_fails_that_cannot_be_read_read_unknown() -> None:
    c, d = made(3, "accept", "ok", signer="lead/checker")
    out = block(record(cases=[c], deliveries=(d,)), fails_errors={"lead/checker": "no mailbox"})
    assert out[out.index("  verifiers:") + 1].endswith("PASS precision 1 of 1; its FAILs before delivery: unknown (no mailbox)")


def test_counted_and_not_its_parts() -> None:
    reviewer = "lead/reviewer"
    causes = [
        Cause("reviewer-miss", "link", ("L", "C1"), version=1), Cause("untyped", "none"), Cause("contract-gap", "words", ("always",)),
        Cause("contract-gap", "words", ("never",)), Cause("relayed-error", "relayed task", ("T",)), Cause("relayed-carry-over", "carry-over", ("R", "p")),
    ]
    made_ = [escape(n, cause, signer=reviewer) for n, cause in zip(range(3, 21, 3), causes, strict=True)]
    accepted = [made(n, "accept", "ok", signer=reviewer) for n in (30, 33)]
    cases = [m[0] for m in made_] + [a[0] for a in accepted]
    deliveries = tuple(m[1] for m in made_) + tuple(a[1] for a in accepted)
    out = block(record(cases=cases, deliveries=deliveries, escapes=tuple(m[2] for m in made_)), fails={reviewer: (2, 3)})
    assert out[out.index("  verifiers:") + 1] == (
        "    lead/reviewer: escapes 2 of 8 judged (1 reviewer-miss, 1 untyped); not its: 2 contract-gap, 1 relayed-error, 1 relayed-carry-over;"
        " PASS precision 6 of 8; its FAILs before delivery: 2 re-check(s), 3 author rework run(s)"
    )


# ------------------------------------------------------------------------------------------------------------------------ DR3-6: the brace rule


def test_an_alternative_group_always_shows_one_alternative_with_its_zeros() -> None:
    out = block(record())
    assert out[1] == "  cases: 0 (done 0, failed 0, blocked 0, open 0 (stalled 0))"
    assert out[2] == "  first deliveries: 0 accepted, 0 rejected, 0 without a verdict"
    assert "  escapes (the team reported done, then the user rejected it): none (judged: n/a (0 of 0))" in out
    assert "  verifiers: none (no delivery yet)" in out


def test_a_zero_part_inside_a_shown_group_is_left_out() -> None:
    c, d, pair = escape(3, Cause("untyped", "none"), signer="lead/checker")
    out = block(record(cases=[c], deliveries=(d,), escapes=(pair,)))
    assert out[out.index("  verifiers:") + 1].startswith("    lead/checker: escapes 1 of 1 judged (1 untyped); PASS precision 0 of 1")  # no "0 reviewer-miss"


def test_a_group_whose_parts_are_all_zero_is_not_shown() -> None:
    c, d, pair = escape(3, Cause("contract-gap", "words", ("always",)), signer="lead/checker")
    out = block(record(cases=[c], deliveries=(d,), escapes=(pair,)))
    assert out[out.index("  verifiers:") + 1].startswith("    lead/checker: escapes 0 of 1 judged; not its: 1 contract-gap; PASS precision 1 of 1")
    ok, dok = made(9, "accept", "ok", signer="lead/checker")
    clean = block(record(cases=[ok], deliveries=(dok,)))
    assert clean[clean.index("  verifiers:") + 1].startswith("    lead/checker: escapes 0 of 1 judged; PASS precision 1 of 1")


# ------------------------------------------------------------------------------------------------------------------------ runs per case (D-E5-6)

RUNS_HEAD = (
    "  runs per case (the user's runs: runs used outside your relayed reworks, plus runs still out while a case is open or blocked; approved: the contract's 15 per "
    "request, or more where your hand-downs raised it (runs used + held + new, at that moment)):"
)


def test_the_runs_header_ends_with_none_when_no_case() -> None:
    assert RUNS_HEAD + " none" in block(record())


def test_a_case_line_shows_the_users_runs_against_the_users_approved_runs() -> None:
    c, d = made(3, "accept", "ok", runs=12, ceiling=15, top_ups=top_ups(("D995", "human", 6)))
    out = block(record(cases=[c], deliveries=(d,)))
    assert out[out.index(RUNS_HEAD) + 1] == f'    {c.id} "Memo for the meeting": 12 of 15 approved (0.80x); top-ups: +6 human rework D995'
    raised, dr = made(6, "accept", "ok", runs=14, ceiling=20)  # the hand-downs raised the approval above the contract's 15
    out = block(record(cases=[raised], deliveries=(dr,)))
    assert out[out.index(RUNS_HEAD) + 1] == f'    {raised.id} "Memo for the meeting": 14 of 20 approved (0.70x); top-ups: none'


def test_the_ratio_rounds_half_up_to_two_decimals() -> None:
    for runs, approved, shown in ((1, 8, "0.13"), (1, 16, "0.06"), (7, 15, "0.47"), (26, 20, "1.30"), (5, 3, "1.67"), (1, 200, "0.01"), (0, 15, "0.00")):
        c, d = made(3, "accept", "ok", runs=runs, ceiling=approved)
        out = block(record(cases=[c], deliveries=(d,), budget=1))
        assert out[out.index(RUNS_HEAD.replace("15", "1")) + 1] == f'    {c.id} "Memo for the meeting": {runs} of {approved} approved ({shown}x); top-ups: none'


def test_the_relayed_and_total_line_appears_only_with_relayed_runs() -> None:
    c, d = made(3, runs=15, relayed_runs=10, ceiling=15, top_ups=top_ups(("A", "relayed", 5), ("B", "relayed", 5)))
    out = block(record(cases=[c], deliveries=(d,)))
    at = out.index(RUNS_HEAD)
    assert out[at + 1] == f'    {c.id} "Memo for the meeting": 5 of 15 approved (0.33x); top-ups: +5 your relayed rework A, +5 your relayed rework B'
    assert out[at + 2] == "      your relayed reworks: 10 run(s), your own spend; total 15"
    plain, dp = made(9, runs=4, ceiling=15)
    assert not any("your relayed reworks:" in x for x in block(record(cases=[plain], deliveries=(dp,))))


def test_a_case_line_with_budget_0_reads_n_a_budget_0() -> None:
    c, d = made(3, runs=4)
    out = block(record(cases=[c], deliveries=(d,), budget=0))
    assert any(x.endswith(': 4 of 0 approved n/a (budget 0); top-ups: none') for x in out)


def test_a_case_whose_runs_are_not_counted_reads_its_reason_and_has_no_ratio() -> None:
    c, d = made(3, runs_unknown="no run log in its window", top_ups=top_ups(("X", "unrecorded", 4), ("G", "granted", 3)), cut=True)
    out = block(record(cases=[c], deliveries=(d,)))
    expected = (
        f'    {c.id} "Memo for the meeting": runs not counted (no run log in its window); top-ups: +4 rework X (tier not recorded), +3 your grant G'
        "; window cut by a later request"
    )
    assert out[out.index(RUNS_HEAD) + 1] == expected


def test_top_ups_and_the_cut_window() -> None:
    c, d = made(3, runs=10, credited=2, ceiling=15, cut=True)
    out = block(record(cases=[c], deliveries=(d,)))
    assert out[out.index(RUNS_HEAD) + 1] == (
        f'    {c.id} "Memo for the meeting": 10 of 15 approved (0.67x), 2 not charged (model-service throttle); top-ups: none; window cut by a later request'
    )


# ------------------------------------------------------------------------------------------------------------------------ alarms


def alarms(r: ServiceRecord, t: QualityThresholds = T) -> tuple[str, str]:
    out = block(r, t)
    at = out.index("  alarms:")
    return out[at + 1], out[at + 2]


def test_the_alarm_lines_in_each_state() -> None:
    few = QualityThresholds(min_judged=1)
    assert alarms(record()) == ("    repeat: n/a (0 of 3 judged cases)", "    cost: n/a (0 of 3 judged cases)")
    # cost: fires (26 of 20 = 1.30x, with relayed runs apart), no, skipped by name, nothing compared
    over, do = made(3, "accept", "ok", runs=31, relayed_runs=5, ceiling=20)
    fine, df = made(9, "accept", "ok", runs=5, ceiling=20)
    blind, db = made(15, "accept", "ok", runs_unknown="no run log in its window")
    assert alarms(record(cases=[over, fine], deliveries=(do, df), budget=20), few)[1] == (
        f"    cost: FIRES: case {over.id} 26 of 20 approved (1.30x); your relayed reworks 5, total 31"
    )
    assert alarms(record(cases=[fine], deliveries=(df,), budget=20), few)[1] == "    cost: no (0 of 1 cases above 1.25x)"
    skipping = alarms(record(cases=[fine, blind], deliveries=(df, db), budget=20), few)[1]
    assert skipping == f"    cost: no (0 of 1 cases above 1.25x); skipped: {blind.id} (runs not counted)"
    assert alarms(record(cases=[blind], deliveries=(db,), budget=20), few)[1] == f"    cost: n/a (0 of 0 cases compared); skipped: {blind.id} (runs not counted)"
    zero, dz = made(21, "accept", "ok", runs=3)
    both = alarms(record(cases=[blind, zero], deliveries=(db, dz), budget=0), few)[1]
    assert both == f"    cost: n/a (0 of 0 cases compared); skipped: {blind.id} (runs not counted), {zero.id} (budget 0)"


def test_the_repeat_alarm_in_each_state() -> None:
    few = QualityThresholds(min_judged=2)
    one, d1 = made(3, "reject", "No.")
    two, d2 = made(9, "reject", "No again.")
    d1.verdicts[0].confirmed = d2.verdicts[0].confirmed = ("C1",)
    a1, a2 = Assertion("R1", one.id, d1.verdicts[0], ("C1",), "confirmed"), Assertion("R2", two.id, d2.verdicts[0], ("C1",), "confirmed")
    both = record(cases=[one, two], deliveries=(d1, d2), assertions=(a1, a2))
    assert alarms(both, few)[0] == f"    repeat: FIRES: C1 failed in 2 of the last 2 judged cases (cases {one.id}, {two.id})"
    d1.verdicts[0].confirmed = d2.verdicts[0].confirmed = ()  # no criterion confirmed: the rejections share nothing
    calm = record(
        cases=[one, two], deliveries=(d1, d2),
        assertions=(Assertion("R1", one.id, d1.verdicts[0], (), "none"), Assertion("R2", two.id, d2.verdicts[0], (), "none")),
    )
    assert alarms(calm, few)[0] == "    repeat: no (2 judged cases; counted: R1, R2)"
    relayed = verdict(request(30), 32, "reject", "Hm.", source="human", links=("C6", "C3"), links_tier="relayed")
    c3 = case([request(30)], verdicts=[relayed])
    d3 = delivery(c3, 0, result_n=31, verdicts=(relayed,))
    below = record(cases=[c3], deliveries=(d3,), assertions=(Assertion("R1", c3.id, relayed, (), "unconfirmed"),))
    assert alarms(below, few)[0] == "    repeat: n/a (1 of 2 judged cases); not counted: R1's reading C6, C3 (not confirmed)"


# ------------------------------------------------------------------------------------------------------------------------ the timeline


def at(minute: int) -> datetime:
    return datetime(2026, 10, 21, 15, minute, tzinfo=timezone.utc)


def mark(version: int, minute: int) -> ContractMark:
    return ContractMark(version, at(minute), ROOT, ("C%d" % version,), (), "legacy")


def test_the_timeline_shows_the_15_newest_then_and_k_earlier() -> None:
    marks = tuple(mark(v, v) for v in range(1, 18))
    out = block(record(timeline=marks))
    heading = out.index("  timeline (bar changes, UTC; marked, never used to split the counts):")
    shown = out[heading + 1:heading + 17]
    assert shown[0] == f"    2026-10-21 15:03 {marks[2].text}" and shown[14] == f"    2026-10-21 15:17 {marks[16].text}"
    assert shown[15] == "    and 2 earlier"
    few = block(record(timeline=marks[:2]))
    assert few[few.index("  timeline (bar changes, UTC; marked, never used to split the counts):") + 1] == f"    2026-10-21 15:01 {marks[0].text}"


def test_the_charter_and_model_line_unknown_none_or_absent() -> None:
    head = "    charter edits and model changes: "
    unknown = block(record())
    assert head + "unknown (no org history: the organization is not a git repository, or git is missing)" in unknown
    assert head + "none" in block(record(history=BarChanges(known=True)))
    listed = CharterMark("lead", "a" * 40, at(40))
    shown = block(record(timeline=(listed,), history=BarChanges(known=True, marks=(listed,))))
    assert f"    2026-10-21 15:40 lead: charter edited (commit {'a' * 12})" in shown and not any(x.startswith(head) for x in shown)
    assert head + "none (2 version(s) not compared: larger than 64 KiB, unreadable or not parseable)" in block(record(history=BarChanges(known=True, skipped=2)))
    assert head + "none (older changes may be missing: only the newest 40 commits are read, within 5 s)" in block(
        record(history=BarChanges(known=True, truncated=True)),
    )
    assert head + "(2 version(s) not compared: larger than 64 KiB, unreadable or not parseable)" in block(
        record(timeline=(listed,), history=BarChanges(known=True, marks=(listed,), skipped=2)),
    )


def test_the_run_attribution_line() -> None:
    one, d1 = made(3, cut=True)
    two, d2 = made(9, cut=True)
    quiet, dq = made(15)
    assert block(record())[-1] == "  run attribution is by time window (08 3.3): 0 case(s) had their window cut by a later request."
    assert block(record(cases=[quiet], deliveries=(dq,)))[-1].endswith("0 case(s) had their window cut by a later request.")
    assert block(record(cases=[one, two, quiet], deliveries=(d1, d2, dq)))[-1] == (
        "  run attribution is by time window (08 3.3): 2 case(s) had their window cut by a later request; their later runs count for that request."
    )


def test_the_timeline_marks_use_their_own_words() -> None:
    marks = (
        TopUpMark(at(5), "CASE", "TASK", "relayed", 5),
        ModelMark("ORG.md", "effort", "", "high", "b" * 40, at(6)),
        PlaybookMark(2, at(7), "lead", "c", evidence=("C1",), evidence_other=1, changed=2, own_words=1, beyond=1),
    )
    out = block(record(timeline=marks))
    assert "    2026-10-21 15:05 top-up +5 run(s) to case CASE: your relayed rework TASK (your own spend)" in out
    assert '    2026-10-21 15:06 ORG.md: effort the org default -> "high"' in out
    assert "    2026-10-21 15:07 playbook v2 (lead): admitted (c) on C1 and 1 other id(s): 2 changed line(s): 1 the cited criteria's own words, 1 beyond them" in out


# ------------------------------------------------------------------------------------------------------------------------ limits, clipping, agent-written text


def test_limits_of_ten_and_and_k_more() -> None:
    cases, deliveries = zip(*(made(n, "reject", f"word {n}") for n in range(3, 39, 3)), strict=True)  # 12 rejected cases
    pairs = tuple((d, Cause("untyped", "none")) for d in deliveries)
    out = block(record(cases=list(cases), deliveries=deliveries, escapes=pairs, assertions=tuple(Assertion(f"R{i + 1}", c.id, d.verdicts[0], (), "") for i, (c, d) in enumerate(zip(cases, deliveries, strict=True)))))
    first = [x for x in out if "rejected: " in x]
    assert len(first) == 10 and first[0].startswith(f"    {cases[2].id}:") and first[-1].startswith(f"    {cases[11].id}:")
    assert "    and 2 earlier case(s), counted above" in out
    assert out.count("    and 2 earlier case(s), counted above") == 2  # the first-delivery lines and the runs lines
    escapes = [x for x in out if x.startswith("    R")]
    assert len(escapes) == 10 and escapes[0].startswith("    R3 ") and "    and 2 earlier escape(s)" in out
    plain = [made(n) for n in range(3, 39, 3)]
    ids = block(record(cases=[c for c, _ in plain], deliveries=tuple(d for _, d in plain)))
    listed = ", ".join(c.id for c, _ in plain[2:])
    assert line(ids, "  judged by the user:").endswith(f"without a verdict: 12 case(s) ({listed}, and 2 more): never counted as accepted; not as delivered: 0")


def test_titles_and_words_are_clipped() -> None:
    long_title = "T" * 100
    t = request(3, title=long_title)
    v = verdict(t, 5, "reject", "w" * 200)
    c = case([t], verdicts=[v], runs=3, ceiling=15)
    d = delivery(c, 0, result_n=4, verdicts=(v,))
    out = block(record(cases=[c], deliveries=(d,)))
    assert f'    {c.id}: rejected: "{"w" * 159}…"' in out
    assert f'    {c.id} "{"T" * 79}…": 3 of 15 approved (0.20x); top-ups: none' in out


def test_no_agent_written_text_in_the_text() -> None:
    t = request(3)
    c = case([t], lessons=["AGENT LESSON"], lesson_ids=["x"])
    d = delivery(c, 0, result_n=4)
    d.result.body = "AGENT RESULT BODY"
    playbook = PlaybookMark(2, at(7), "lead", "c", evidence=("C1",), changed=1, own_words=1, beyond=0, lines=(("AGENT PLAYBOOK LINE", True),), agent_written=True)
    out = "\n".join(block(record(cases=[c], deliveries=(d,), timeline=(playbook,))))
    for needle in ("AGENT LESSON", "AGENT RESULT BODY", "AGENT PLAYBOOK LINE"):
        assert needle not in out


def test_paths_and_model_names_go_through_shown_name() -> None:
    path = 'a/"quoted"\nname.md'
    evil = "evil\nmodel"
    cause = Cause("relayed-carry-over", "carry-over", ("R1", path))
    c, d, pair = escape(3, cause)
    model = ModelMark("lead", "model", evil, "other", "c" * 40, at(9))
    out = block(record(cases=[c], deliveries=(d,), escapes=(pair,), assertions=(Assertion("R1", c.id, d.verdicts[0], (), ""),), timeline=(model,)))
    text = "\n".join(out)
    assert f"delivered {shown_name(path, 200)} after" in text
    assert all("\n" not in x for x in out)
    assert f"model {shown_name(evil, 120)} -> {shown_name('other', 120)}" in text


def test_evidence_ids_that_are_not_ids_are_counted_not_shown() -> None:
    playbook = PlaybookMark(2, at(7), "lead", "b", evidence=(), evidence_other=3, changed=1, tagged=0, untagged=1)
    out = "\n".join(block(record(timeline=(playbook,))))
    assert "admitted (b) on 3 other id(s): 1 changed line(s): 0 tagged with an id, 1 untagged" in out


def test_an_agent_client_service_is_one_line_of_counts() -> None:
    t = request(3, to="lead/writer")
    t.sender = "lead"
    c = case([t], owner="lead/writer", service="draft", verdicts=[verdict(t, 5, "accept", "ok", tier="agent")])
    d = delivery(c, 0, result_n=4, verdicts=(c.verdicts[0],))
    nested = record(owner="lead/writer", service="draft", client="lead", client_kind="agent", cases=[c], deliveries=(d,))
    assert nested_line(RecordView(nested)) == "- draft (offered by lead/writer; client lead): 1 case(s), 1 delivered, 1 agent verdict(s)"
    assert nested_line(RecordView(record(owner="lead/writer", service="draft", client="lead", client_kind="agent"))) == (
        "- draft (offered by lead/writer; client lead): 0 case(s), 0 delivered, 0 agent verdict(s)"
    )
