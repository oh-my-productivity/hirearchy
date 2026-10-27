"""The JSON of the quality view (0b 9.4): every key present with its type and null rule, the two-decimal ratios, no text limits."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest
from testkit.quality_schema import problems

from hirearchy.kernel import ROOT, Message
from hirearchy.progress._quality_facts import HeldTask, MovedPast, QualityView, RecordView
from hirearchy.progress._quality_render import quality_data
from hirearchy.reflection import (
    Assertion, BarChanges, Case, Cause, CharterMark, ContractMark, Delivery, ItemWatch, ModelMark, PlaybookMark, QualityThresholds, ServiceRecord, TopUpMark,
)

from ._quality_records import case, delivery, mid, record, request, top_ups, verdict

T = QualityThresholds()


def at(minute: int) -> datetime:
    return datetime(2026, 10, 21, 15, minute, tzinfo=timezone.utc)


def one(n: int, kind: str | None = None, words: str = "", **more: Any) -> tuple[Case, Delivery]:
    t = request(n)
    v = verdict(t, n + 2, kind, words) if kind else None
    c = case([t], verdicts=[v] if v else [], **more)
    return c, delivery(c, 0, result_n=n + 1, verdicts=(v,) if v else ())


def view(*records: ServiceRecord, moved_past: tuple[MovedPast, ...] = (), service: str | None = None, **views: Any) -> QualityView:
    return QualityView(T, ("a note",), tuple(RecordView(r, **views) for r in records), moved_past, service)


def rich() -> QualityView:
    """A service with every kind of mark, an escape, a relayed rework, a case never delivered and one whose runs are not counted; a nested service; a
    one-off record with an escape; the moved-past section."""
    first, rework = request(3), request(9, source="relayed", revises=mid(3), budget=4)
    v = verdict(first, 5, "reject", "Not right.", confirmed=("C1",), links=("C1",), links_tier="human")
    c1 = case([first, rework], verdicts=[v], runs=15, relayed_runs=10, ceiling=15, credited=1, top_ups=top_ups(("T9", "relayed", 4)), cut=True)
    d1 = delivery(c1, 0, result_n=4, signer="lead/reviewer", verdicts=(v,))
    d2 = delivery(c1, 1, result_n=10, edited=True, edited_at=1)
    c2 = case([request(30)], state="blocked")
    c3, d3 = one(36, runs_unknown="no run log in its window", cut=False)
    cause = Cause("reviewer-miss", "link", ("L1", "C1"), ("link",), version=1)
    marks = (
        ContractMark(1, at(1), ROOT, ("C1", "C2"), (), "first"),
        ContractMark(2, at(2), ROOT, ("C3",), ("C2",), "answers", "R1", (("C3", "LINK"), ("C2", ""))),
        PlaybookMark(2, at(3), "lead", "c", evidence=("C1",), evidence_other=1, changed=1, own_words=1, beyond=0, cited=(("C1", "At most 5"),), lines=(("a line", True),)),
        CharterMark("lead", "a" * 40, at(4)), ModelMark("lead", "model", "", "claude", "b" * 40, at(5)), TopUpMark(at(6), c1.id, "T9", "relayed", 4),
    )
    svc = record(
        cases=[c1, c2, c3], deliveries=(d1, d2, d3), escapes=((d1, cause),), assertions=(Assertion("R1", c1.id, v, ("C1",), "confirmed"),), timeline=marks,
        history=BarChanges(known=True, marks=(marks[3], marks[4]), skipped=1),
    )
    nested = record(owner="lead/writer", service="draft", client="lead", client_kind="agent", budget=3)
    off_task = request(40, service=None, to="ops")
    off_v = verdict(off_task, 42, "reject", "No.")
    off_c = case([off_task], owner="ops", service="", verdicts=[off_v], runs=2)
    off_d = delivery(off_c, 0, result_n=41, signer="ops", verdicts=(off_v,))
    off = record(owner="", service="", contract=0, playbook=0, budget=0, cases=[off_c], deliveries=(off_d,), escapes=((off_d, Cause("untyped", "none")),))
    held = HeldTask(request(50, to="lead"), Message(id=mid(51, "lead"), sender="lead", to=ROOT, type="result", status="blocked", body="b", title="r", reply_to=mid(50)), 2)
    theirs = HeldTask(Message(id=mid(52, "lead"), sender="lead", to="lead/writer", type="task", title="AGENT TITLE", body="b"), held.blocked, 0)
    moved = (MovedPast("lead", 7, tasks=(held, theirs)), MovedPast("ops", None, "no budget"), MovedPast("eng", None, error="gone"))
    return QualityView(
        QualityThresholds(source="ORG.md"), ("a note",),
        (
            RecordView(svc, stalled={c2.id: False}, left_blocked=frozenset({c2.tasks[-1].id}), fails={"lead/reviewer": (2, 3)}),
            RecordView(nested), RecordView(off, fails_errors={}),
        ), moved,
    )


def data(v: QualityView) -> dict[str, Any]:
    out: dict[str, Any] = quality_data(v)
    assert json.loads(json.dumps(out)) == out  # plain JSON values only
    return out


def test_schema_is_1() -> None:
    assert data(view())["schema"] == 1


def test_every_key_is_present_with_its_type() -> None:
    assert problems(data(rich())) == []
    assert problems(data(view())) == []  # an empty organization too


def test_the_schema_check_reports_a_missing_key_a_wrong_type_and_an_extra_key() -> None:
    broken = data(rich())
    del broken["notes"]
    broken["services"][0]["budget"] = "15"
    broken["services"][0]["surprise"] = 1
    broken["services"][0]["timeline"][0]["kind"] = "other"
    found = problems(broken)
    assert "$.notes: missing" in found
    assert any(p.startswith("$.services[0].budget: expected int") for p in found)
    assert "$.services[0].surprise: not in the schema" in found
    assert any(p.startswith("$.services[0].timeline[0].kind") for p in found)


def test_the_top_level_and_the_thresholds() -> None:
    out = data(rich())
    assert out["thresholds"] == {"min_judged": 3, "repeat_window": 3, "repeat_failures": 2, "cost_ratio": "1.25", "source": "ORG.md"}
    assert out["notes"] == ["a note"] and [s["service"] for s in out["services"]] == ["weekly-memo"]
    assert out["one_off"]["service"] == "" and out["one_off"]["budget"] is None and out["one_off"]["owner"] == ""
    assert out["nested"] == [{"owner": "lead/writer", "service": "draft", "client": "lead", "cases": 0, "delivered": 0, "agent_verdicts": 0, "error": ""}]


def test_ratio_is_the_two_decimal_string() -> None:
    cases = {c["id"]: c for c in data(rich())["services"][0]["cases"]}
    first = next(c for c in cases.values() if c["tasks"] == 2)
    assert first["user_cost"] == 5 and first["user_approved"] == 15 and first["ratio"] == "0.33"
    over, d = one(42, runs=26, ceiling=20)
    cost = data(view(record(cases=[over], deliveries=(d,), budget=20)))["services"][0]["alarms"]["cost"]
    assert cost["state"] == "n/a"  # one judged case or fewer: no verdict was given
    judged = [one(n, "accept", "ok", runs=26, ceiling=20) for n in (3, 9, 15)]
    full = record(cases=[c for c, _ in judged], deliveries=tuple(d for _, d in judged), budget=20)
    cost = data(view(full))["services"][0]["alarms"]["cost"]
    assert cost["state"] == "fires" and cost["cases"][0] == {"case": judged[0][0].id, "user_cost": 26, "user_approved": 20, "ratio": "1.30", "relayed_runs": 0, "total": 26}


def test_the_user_spend_and_user_approved_keys() -> None:
    c = data(rich())["services"][0]["cases"][0]
    assert {"budget", "user_approved", "user_cost", "spend", "runs", "relayed_runs", "credited"} <= set(c)
    assert not {"approved", "user_spend"} & set(c)
    assert (c["budget"], c["user_approved"], c["runs"], c["relayed_runs"], c["spend"], c["user_cost"], c["credited"]) == (15, 15, 15, 10, 15, 5, 1)


def test_the_json_has_no_text_limits() -> None:
    cases, deliveries = zip(*(one(n, "accept", "ok") for n in range(3, 39, 3)), strict=True)  # 12 cases
    marks = tuple(ContractMark(v, at(v), ROOT, (f"C{v}",), (), "legacy") for v in range(1, 18))
    long = request(50, title="T" * 100)
    longcase = case([long], verdicts=[verdict(long, 52, "reject", "w" * 300)])
    out = data(view(record(cases=[*cases, longcase], deliveries=(*deliveries, delivery(longcase, 0, result_n=51)), timeline=marks)))["services"][0]
    assert len(out["cases"]) == 13 and len(out["timeline"]) == 17 and out["cases"][-1]["title"] == "T" * 100
    assert len(out["deliveries"]["unjudged_cases"]) == 1


def test_null_rules_of_9_4() -> None:
    out = data(rich())
    svc = out["services"][0]
    by_state = {c["state"]: c for c in svc["cases"]}
    never = by_state["blocked"]
    assert never["first"] is None and never["stalled"] is False
    blind = next(c for c in svc["cases"] if c["runs_unknown"])
    assert blind["runs_unknown"] == "no run log in its window"
    assert all(blind[k] is None for k in ("runs", "credited", "relayed_runs", "spend", "user_cost", "ratio"))
    assert svc["verifiers"][0]["rechecks"] == 2 and svc["verifiers"][0]["rework_runs"] == 3 and svc["verifiers"][0]["fails_error"] == ""
    assert svc["escapes"][0]["assertion"] == "R1" and out["one_off"]["escapes"][0]["assertion"] is None
    assert svc["escapes"][0]["class"] == "off_spec" and out["one_off"]["escapes"][0]["class"] is None
    marks = {m["kind"]: m for m in svc["timeline"]}
    first_contract = svc["timeline"][0]
    assert first_contract["basis"] == "first" and first_contract["answers"] is None and marks["playbook"]["restores"] is None
    answered = next(m for m in svc["timeline"] if m["kind"] == "contract" and m["basis"] == "answers")
    assert answered["answers"] == "R1" and answered["confirmed"] == [{"id": "C3", "link": "LINK"}] and answered["not_confirmed"] == ["C2"]
    playbook = marks["playbook"]
    assert (playbook["own_words"], playbook["beyond"], playbook["tagged"], playbook["untagged"]) == (1, 0, None, None)
    moved = {m["addr"]: m for m in out["moved_past"]}
    assert moved["lead"]["held"] == 7 and moved["ops"]["held"] is None and moved["ops"]["held_error"] == "no budget" and moved["eng"]["error"] == "gone"
    titles = {t["id"]: t["title"] for t in moved["lead"]["tasks"]}
    assert [t for t in titles.values() if t is None] and "AGENT TITLE" not in json.dumps(out)  # an agent's task title is never in the JSON
    assert view().records == () and data(view())["one_off"] is None
    assert data(view(record(), service="weekly-memo"))["one_off"] is None


def test_playbook_marks_always_have_op_item_and_item_kind() -> None:
    """Design 14.4: the three keys are always there, `""` for a legacy version (and for `first`/`migrate`, which change no one item), and `basis` takes
    `migrate`, `exempt` and `watch`; the mark's own `kind` key still reads `playbook`."""
    legacy = next(m for m in data(rich())["services"][0]["timeline"] if m["kind"] == "playbook")
    assert (legacy["kind"], legacy["op"], legacy["item"], legacy["item_kind"]) == ("playbook", "", "", "")
    marks = (
        PlaybookMark(2, at(3), "lead", "b", evidence=("R1", "R2"), changed=1, tagged=1, untagged=0, op="add", item="P4", item_kind="rule"),
        PlaybookMark(3, at(4), "runtime (watch)", "watch", restores=1, changed=1, op="watch", item="P4", item_kind="rule", related=("R4", "R6")),
        PlaybookMark(4, at(5), "runtime (migration)", "migrate", op="migrate"),
        PlaybookMark(5, at(6), "lead", "exempt", removed=1, op="retire", item="P2", item_kind="step", acknowledged="LINK"),
    )
    out = data(view(record(timeline=marks)))
    assert problems(out) == []
    assert [(m["op"], m["item"], m["item_kind"], m["basis"]) for m in out["services"][0]["timeline"]] == [
        ("add", "P4", "rule", "b"), ("watch", "P4", "rule", "watch"), ("migrate", "", "", "migrate"), ("retire", "P2", "step", "exempt"),
    ]
    assert set(out["services"][0]["timeline"][0]) == set(legacy)  # one shape for every version


def test_the_watch_list_has_every_key() -> None:
    """Design 14.4: `watch` is a list of items with all eleven keys always present, `[]` when there is none (also in an error record)."""
    watch = (
        ItemWatch("P1", "step", "kept", 1),
        ItemWatch("P4", "rule", "warning", 2, watch_start=at(3), k=3, r=(1, 4), clean=0, waiting=0, related=("R4",), pending=("R5",), carried="P9"),
        ItemWatch("P5", "step", "new", 3, watch_start=at(9), k=3, r=(0, 2), clean=1, waiting=2),
    )
    out = data(view(record(watch=watch), record(service="other", watch=()), ServiceRecord("lead", "bad", ROOT, "human", error="the playbook watch: boom")))
    assert problems(out) == []
    first, second, broken = out["services"]
    keys = {"item", "kind", "state", "k", "r", "clean", "waiting", "related", "pending", "since", "carried"}
    assert all(set(entry) == keys for entry in first["watch"])
    assert first["watch"][1] == {
        "item": "P4", "kind": "rule", "state": "warning", "k": 3, "r": [1, 4], "clean": 0, "waiting": 0, "related": ["R4"], "pending": ["R5"],
        "since": "2026-10-21T15:03:00Z", "carried": "P9",
    }
    assert first["watch"][0]["since"] is None and first["watch"][0]["related"] == [] and first["watch"][2]["waiting"] == 2
    assert second["watch"] == [] and broken["watch"] == []


def test_pass_precision_is_zero_zero_without_a_judged_delivery() -> None:
    c, d = one(3)
    d = Delivery(d.case, d.task, d.result, 0, "lead/checker", (), "", 0, False, False)
    out = data(view(record(cases=[c], deliveries=(d,)), fails={"lead/checker": (0, 0)}))["services"][0]["verifiers"]
    assert out == [{"addr": "lead/checker", "judged": 0, "escapes": {"counted": {}, "not_its": {}}, "pass_precision": [0, 0], "rechecks": 0, "rework_runs": 0, "fails_error": ""}]


def test_stalled_fails_and_held_errors_tell_zero_from_unknown() -> None:
    open_case = case([request(3)], state="open")
    done = case([request(9)])
    d = delivery(done, 0, result_n=10, signer="lead/checker")
    r = record(cases=[open_case, done], deliveries=(d,))
    known = data(view(r, stalled={open_case.id: True}))["services"][0]
    assert known["stalled_error"] == "" and [c["stalled"] for c in known["cases"]] == [True, False]
    unknown = data(view(r, stalled_error="boom", fails_errors={"lead/checker": "no mailbox"}))["services"][0]
    assert unknown["stalled_error"] == "boom" and [c["stalled"] for c in unknown["cases"]] == [None, None]
    assert unknown["verifiers"][0]["rechecks"] is None and unknown["verifiers"][0]["rework_runs"] is None and unknown["verifiers"][0]["fails_error"] == "no mailbox"
    off = data(view(record(files_error="the deliverable folders: boom")))["services"][0]
    assert off["files_error"] == "the deliverable folders: boom"
    held = data(rich())["moved_past"]
    assert [m["held"] for m in held] == [7, None, None] and held[1]["held_error"] == "no budget"


@pytest.mark.parametrize("where", ["service", "one_off", "nested"])
def test_an_error_record_has_null_budget_empty_alarms_and_null_history(where: str) -> None:
    broken = ServiceRecord("lead", "weekly-memo", ROOT, "human", error="SERVICE.md: does not parse (ScannerError)")
    bad_off = ServiceRecord("", "", ROOT, "human", error="the cases: boom")
    nested = ServiceRecord("lead/writer", "draft", "lead", "agent", error="the cases: boom")
    out = data(view(broken, nested, bad_off))
    rec = {"service": out["services"][0], "one_off": out["one_off"], "nested": None}[where]
    if where == "nested":
        assert out["nested"] == [{"owner": "lead/writer", "service": "draft", "client": "lead", "cases": 0, "delivered": 0, "agent_verdicts": 0, "error": "the cases: boom"}]
        return
    assert rec["error"] and rec["budget"] is None and rec["alarms"] == {} and rec["history"] is None
    assert (rec["client"], rec["client_kind"], rec["unit"]) == ("root", "human", "case")
    assert rec["cases"] == [] and rec["escapes"] == [] and rec["timeline"] == [] and rec["verifiers"] == [] and rec["contract"] == 0 and rec["playbook"] == 0
    assert rec["first_deliveries"] == {"accepted": 0, "rejected": 0, "no_verdict": 0, "superseded": 0, "neither": 0, "never_delivered": 0}


def test_the_schema_check_accepts_an_error_record() -> None:
    broken = ServiceRecord("lead", "weekly-memo", ROOT, "human", error="SERVICE.md: does not parse (ScannerError)")
    assert problems(data(view(broken, ServiceRecord("", "", ROOT, "human", error="the cases: boom")))) == []


def test_a_carry_over_path_and_a_model_name_appear_as_stored_unclipped() -> None:
    path, model = "a/" + "p" * 300 + '"x".md', "m" * 300 + "\nnl"
    c, d = one(3, "reject", "No.")
    cause = Cause("relayed-carry-over", "carry-over", ("R1", path))
    marks = (ModelMark("lead", "model", model, "other", "c" * 40, at(9)),)
    out = data(view(record(cases=[c], deliveries=(d,), escapes=((d, cause),), timeline=marks)))["services"][0]
    assert out["escapes"][0]["detail"] == ["R1", path]
    assert out["timeline"][0]["before"] == model and out["timeline"][0]["after"] == "other"


def test_playbook_lines_are_json_only_and_marked_agent_written() -> None:
    mark = PlaybookMark(2, at(7), "lead", "c", evidence=("C1",), changed=2, own_words=1, beyond=1, lines=(("AGENT LINE ONE", True), ("AGENT LINE TWO", False)), lines_more=3)
    out = data(view(record(timeline=(mark,))))["services"][0]["timeline"][0]
    assert out["lines"] == [{"text": "AGENT LINE ONE", "own_words": True}, {"text": "AGENT LINE TWO", "own_words": False}] and out["lines_more"] == 3
    assert out["agent_written"] is True and out["evidence"] == ["C1"]
