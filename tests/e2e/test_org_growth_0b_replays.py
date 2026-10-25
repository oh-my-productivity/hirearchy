# mypy: ignore-errors
"""Phase 0b, the exit-check replays (design 19, plan FEAT-009): the quality view and health, read by the product's own code over the files the studies
kept. No scheduler, no LLM, no network, no git: ``testkit.org_replay.materialize`` builds the organization of a corpus from its kept files (design 19.1)
and ``Org`` opens it.

One test per expectation id of design 19.3, each written from the design's text before it ran. **An expectation is never edited to match the product**:
if a replay computes another value, the FEAT stops and the manager is told (19.3, "When an expectation fails"). A listed file that is missing, or a
message that does not parse, fails the test; nothing here skips.

This module holds E (E-1..E-5), E2 (E2-1..E2-6), A5 (A5-1..A5-4) and E3 (E3-1..E3-7 and the constructed variant of E3-9). A5-4 is also the golden ``quality/a5_one_off_block.txt``, E3-5 the
golden ``quality/e3.txt``, E3-8 the golden ``quality/e3.json`` with the schema and figure checks (``tests/golden/test_golden_quality.py``). E4 s1r, s2r and
s3 are the last block (S1R-1..S1R-6, S2R-1..S2R-3, S3-1..S3-5, E4-all).
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, NamedTuple

import pytest
from testkit import REPO
from testkit.e4_replay import EV, evidence
from testkit.org_replay import materialize

from hirearchy.core import ROOT, Org
from hirearchy.mail import moved_past
from hirearchy.reflection import QualityThresholds, repeat_alarm, user_cost, user_spend

NOW = datetime(2026, 10, 25, tzinfo=timezone.utc)  # health reads the clock: pinned, after every corpus
THRESHOLDS = "Thresholds: the defaults (tunable): alarms need 3 judged cases; repeat: one id failing in 2 of the last 3 judged cases; cost: a case above 1.25x its approved runs."
NO_HISTORY = "charter edits and model changes: unknown (no org history: the organization is not a git repository, or git is missing)"
NO_ADMISSION = "no admission recorded (written before the evidence gate)"
NO_RUN_LOG = "no run log in its window"


class Replay(NamedTuple):
    org: Org
    text: str
    data: dict[str, Any]  # quality_data, through json (what `quality --json` prints)
    records: list[Any]  # CaseRecords.records(): service records, then the one-off record
    lines: list[str]
    root_health: str  # root's reading of health (causes shown)
    agent_health: str  # an agent's reading
    agents: dict[str, Any]  # AgentHealth by address


@pytest.fixture(scope="module")
def replays(tmp_path_factory):
    """``replays(corpus, variant=None)``: the corpus materialized once per module, with everything the tests read from it."""
    patch = pytest.MonkeyPatch()
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        patch.delenv(var, raising=False)
    patch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path_factory.getbasetemp()))
    made: dict[tuple[str, str | None], Replay] = {}

    def get(corpus: str, variant: str | None = None) -> Replay:
        if (corpus, variant) not in made:
            org = Org(materialize(corpus, tmp_path_factory.mktemp(f"{corpus}-{variant or 'base'}"), variant))
            quality = org.runtime.quality_report
            text = quality.quality_text()
            health = org.runtime.health_analyzer.org_health(ROOT, NOW)
            made[(corpus, variant)] = Replay(
                org, text, json.loads(json.dumps(quality.quality_data())), org.runtime.case_records.records(), text.splitlines(),
                org.runtime.health_renderer.render_text(health, causes=True), org.runtime.health_renderer.render_text(health),
                {a.addr: a for a in health.agents},
            )
        return made[(corpus, variant)]

    yield get
    patch.undo()


def service(replay: Replay) -> dict[str, Any]:
    (record,) = replay.data["services"]
    return record


def case(record: dict[str, Any], short: str) -> dict[str, Any]:
    (found,) = [c for c in record["cases"] if c["id"].endswith(f"-root-{short}")]
    return found


def service_record(replay: Replay) -> Any:
    (record,) = [r for r in replay.records if r.service]
    return record


def one_off_record(replay: Replay) -> Any:
    (record,) = [r for r in replay.records if not r.service]
    return record


def deliveries(record: Any) -> list[tuple[str, str]]:
    """``(the delivered task, the result that delivered it)`` of every delivery, sorted."""
    return sorted((d.task.id, d.result.id) for d in record.deliveries)


def marks(record: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [m for m in record["timeline"] if m["kind"] == kind]


def sent_to(replay: Replay, sender: str, to: str, after: str) -> list[str]:
    """The ids of the tasks ``sender`` sent to ``to`` after the message ``after``, read from the organization's own sent box."""
    return [m.id for m in replay.org.sent(sender) if m.type == "task" and m.to == to and m.id > after]


# ------------------------------------------------------------------------------------------------------------------ E


def test_e_1(replays):
    """E-1: the record, the cases, the deliveries and what the user judged, on E's sent boxes. No tier was ever recorded (`source` absent): every verdict
    is legacy and read as the user's (0a 3.1)."""
    replay = replays("E")
    record = service(replay)
    assert (record["service"], record["owner"], record["client"], record["client_kind"]) == ("weekly-memo", "lead", "root", "human")
    assert replay.data["one_off"] is None and replay.data["nested"] == []
    b495, c686, c2c75 = "20261018T021644679563-root-b495", "20261018T022344643603-root-c686", "20261018T024234965290-root-2c75"
    assert [c["id"] for c in record["cases"]] == [b495, c686, c2c75]
    assert deliveries(service_record(replay)) == [
        (b495, "20261018T022217503550-lead-e6b8"),
        (c686, "20261018T022759360021-lead-52d5"),
        ("20261018T022845034488-root-5bae", "20261018T024337814874-lead-e73a"),
    ]
    assert (record["deliveries"]["total"], record["deliveries"]["judged"]) == (3, 1)
    (judged,) = [d for d in service_record(replay).deliveries if d.judged]
    assert judged.task.id == b495 and [(v.verdict, v.message.id) for v in judged.counted] == [("accept", "20261018T022310913851-root-f538")]
    assert record["first_deliveries"] == {"accepted": 1, "rejected": 0, "no_verdict": 1, "superseded": 1, "neither": 0, "never_delivered": 1}
    assert case(record, "b495")["first"]["outcome"] == "accepted"
    assert case(record, "c686")["first"] == {
        "task": c686, "outcome": "none", "superseded_by": "20261018T022845034488-root-5bae", "superseded_source": "unrecorded",
    }  # without a verdict: superseded by rework 5bae, whose tier was not recorded
    assert case(record, "2c75")["first"] is None  # never delivered (blocked)
    assert record["deliveries"]["unjudged_cases"] == [c686]  # its latest delivery e73a has no verdict after it
    (latest,) = [d for d in service_record(replay).deliveries if d.result.id.endswith("-lead-e73a")]
    assert latest.verdicts == ()
    assert record["deliveries"]["not_on_a_delivery"] == ["20261018T024152961586-root-550c", "20261018T025414374460-root-86de"]
    # 550c, 02:41:52, was given on 5bae's blocked result ...-lead-4b37: it is not the accept of e73a (02:43:37)
    assert any(m.id.endswith("-lead-4b37") and m.status == "blocked" for m in replay.org.sent("lead"))
    assert record["escapes"] == [] and record["deliveries"]["legacy_verdicts"] == 3
    assert "  escapes (the team reported done, then the user rejected it): none (judged: 1 of 3)" in replay.lines
    assert [c["id"] for c in record["cases"] if c["cut"]] == [c686]  # c686's window is cut by 2c75
    assert "  run attribution is by time window (08 3.3): 1 case(s) had their window cut by a later request; their later runs count for that request." in replay.lines


def test_e_2(replays):
    """E-2: E kept no run log (`run-counts.txt` has totals per agent only), so a done case whose window is not cut reads `runs not counted (no run log in
    its window)` and a cut or blocked case reads 0 runs. Corpus note: no run log was kept, in `studies/E-service-reflection/evidence/`."""
    replay = replays("E")
    record = service(replay)
    assert record["alarms"]["repeat"]["state"] == "n/a" and record["alarms"]["repeat"]["judged"] == 1
    assert "    repeat: n/a (1 of 3 judged cases)" in replay.lines
    assert "    cost: n/a (1 of 3 judged cases); skipped: 20261018T021644679563-root-b495 (runs not counted)" in replay.lines
    assert record["alarms"]["cost"]["skipped"] == [{"case": "20261018T021644679563-root-b495", "reason": "runs not counted"}]
    b495 = case(record, "b495")
    assert (b495["state"], b495["cut"], b495["runs_unknown"], b495["runs"]) == ("done", False, NO_RUN_LOG, None)
    assert any(f'-root-b495 "Memo for 2026-10-05 meeting": runs not counted ({NO_RUN_LOG}); top-ups: none' in line for line in replay.lines)
    assert (case(record, "c686")["cut"], case(record, "c686")["runs"], case(record, "c686")["runs_unknown"]) == (True, 0, "")
    assert (case(record, "2c75")["state"], case(record, "2c75")["runs"], case(record, "2c75")["runs_unknown"]) == ("blocked", 0, "")


def test_e_3(replays):
    """E-3: the top-ups of c686: +5 for the rework 5bae (tier not recorded) and the grants +3 and +1 (c1c5, f2a7)."""
    record = service(replays("E"))
    assert case(record, "c686")["top_ups"] == [
        {"id": "20261018T022845034488-root-5bae", "source": "unrecorded", "amount": 5},
        {"id": "20261018T023745038216-root-c1c5", "source": "granted", "amount": 3},
        {"id": "20261018T024011579595-root-f2a7", "source": "granted", "amount": 1},
    ]


def test_e_4(replays):
    """E-4: the timeline of E: contract v2 and v3 not confirmed; playbook v2 and v3 with no admission recorded; charter and model marks unknown (no git)."""
    replay = replays("E")
    record = service(replay)
    contracts = {m["version"]: m for m in marks(record, "contract")}
    assert (contracts[2]["not_confirmed"], contracts[2]["confirmed"]) == (["C8"], []) and (contracts[3]["not_confirmed"], contracts[3]["confirmed"]) == (["C9"], [])
    playbooks = {m["version"]: m for m in marks(record, "playbook")}
    assert (playbooks[2]["basis"], playbooks[2]["by"]) == ("legacy", "lead") and (playbooks[3]["basis"], playbooks[3]["by"]) == ("legacy", "lead")
    assert any(f"playbook v2 (lead): {NO_ADMISSION}" in line for line in replay.lines) and any(f"playbook v3 (lead): {NO_ADMISSION}" in line for line in replay.lines)
    assert "    2026-10-18 02:23 contract v2 (root): adds C8: not confirmed" in replay.lines
    assert "    2026-10-18 02:42 contract v3 (root): adds C9: not confirmed" in replay.lines
    assert [m for m in record["timeline"] if m["kind"] in ("charter", "model")] == [] and record["history"]["known"] is False
    assert f"    {NO_HISTORY}" in replay.lines


def test_e_5(replays):
    """E-5: the writer's task a489 stays blocked and the lead moved on; root's blocked 2c75 is released by the verdict 86de."""
    replay = replays("E")
    (writer,) = replay.data["moved_past"]
    assert writer["addr"] == "lead/writer"
    (task,) = writer["tasks"]  # no other held task of the writer
    assert (task["id"], task["sender"], task["blocked"]) == ("20261018T023352181048-lead-a489", "lead", "2026-10-18T02:34:16Z")
    assert (task["left_blocked"], task["sent_since"]) == (True, 3)
    assert sent_to(replay, "lead", "lead/writer", "20261018T023416488289-lead.writer-f27d") == [
        "20261018T023517240902-lead-5875", "20261018T024351472740-lead-50f8", "20261018T024757632466-lead-b6a7",
    ]
    assert "    task 20261018T023352181048-lead-a489 from lead, blocked 2026-10-18 02:34: left blocked: lead has sent lead/writer 3 task(s) since" in replay.lines
    blocked = next(m for m in replay.org.sent("lead") if m.reply_to == "20261018T024234965290-root-2c75" and m.status == "blocked")
    task_2c75 = next(m for m in replay.org.sent(ROOT) if m.id == "20261018T024234965290-root-2c75")
    assert moved_past(task_2c75, blocked, replay.org.received("lead"))  # the verdict 86de on its chain, after the block
    assert all("2c75" not in line for line in replay.lines if line.startswith("    task "))  # so it is not listed
    # the held figure is not asserted: the derived budget needs the run logs (19.2)


# ------------------------------------------------------------------------------------------------------------------ E2


def test_e2_1(replays):
    """E2-1: one record `meeting-memo`; 3 cases; 6 deliveries; 5 judged; the first deliveries; nothing without a verdict or off a delivery."""
    replay = replays("E2")
    record = service(replay)
    assert (record["service"], record["owner"], record["client_kind"]) == ("meeting-memo", "lead", "human")
    assert [c["id"] for c in record["cases"]] == [
        "20261018T034955412135-root-d22b", "20261018T040120119761-root-55ff", "20261018T040509774983-root-e29b",
    ]
    assert (record["deliveries"]["total"], record["deliveries"]["judged"]) == (6, 5)
    assert record["first_deliveries"] == {"accepted": 1, "rejected": 1, "no_verdict": 1, "superseded": 1, "neither": 0, "never_delivered": 0}
    assert case(record, "55ff")["first"]["outcome"] == "accepted" and case(record, "e29b")["first"]["outcome"] == "rejected"
    assert case(record, "d22b")["first"] == {
        "task": "20261018T034955412135-root-d22b", "outcome": "none", "superseded_by": "20261018T035429740646-root-d90e", "superseded_source": "unrecorded",
    }
    assert record["deliveries"]["unjudged_cases"] == [] and record["deliveries"]["not_on_a_delivery"] == []
    assert record["deliveries"]["legacy_verdicts"] == 5
    assert [c["id"] for c in record["cases"] if c["cut"]] == []
    assert "  run attribution is by time window (08 3.3): 0 case(s) had their window cut by a later request." in replay.lines


def test_e2_2(replays):
    """E2-2: two escapes, both untyped: R1 on d90e (the assistant's own rework, whose `source` was never recorded, so `relayed-error` cannot fire on these
    files) and R2 on e29b (the Marta row). No link exists and no lasting word occurs."""
    replay = replays("E2")
    record = service(replay)
    first, second = record["escapes"]
    assert (first["assertion"], first["task"], first["case"]) == ("R1", "20261018T035429740646-root-d90e", "20261018T034955412135-root-d22b")
    assert (second["assertion"], second["task"], second["case"]) == ("R2", "20261018T040509774983-root-e29b", "20261018T040509774983-root-e29b")
    for escape in (first, second):
        assert (escape["cause"], escape["rule"], escape["rules"], escape["detail"], escape["also"]) == ("untyped", "none", [], [], [])
        assert (escape["signer"], escape["attribution"]) == ("lead/reviewer", "counted")
    (verifier,) = record["verifiers"]
    assert (verifier["addr"], verifier["judged"], verifier["escapes"], verifier["pass_precision"]) == ("lead/reviewer", 5, {"counted": {"untyped": 2}, "not_its": {}}, [3, 5])
    assert any(line.startswith("    lead/reviewer: escapes 2 of 5 judged (2 untyped); PASS precision 3 of 5; ") for line in replay.lines)


def test_e2_3(replays):
    """E2-3: repeat `no`, counting R1 and R2; the cost alarm compares nothing: the three cases are done, no window is cut and no run log was kept, so each
    reads `runs not counted (no run log in its window)` (4.1 reason 3) and all three are skipped."""
    replay = replays("E2")
    record = service(replay)
    assert "    repeat: no (3 judged cases; counted: R1, R2)" in replay.lines
    assert "    cost: n/a (0 of 0 cases compared); skipped: 20261018T034955412135-root-d22b, 20261018T040120119761-root-55ff, 20261018T040509774983-root-e29b (runs not counted)" in replay.lines
    assert (record["alarms"]["cost"]["state"], record["alarms"]["cost"]["compared"], record["alarms"]["cost"]["judged"]) == ("n/a", 0, 3)
    assert [c["runs_unknown"] for c in record["cases"]] == [NO_RUN_LOG] * 3
    assert sum(f"runs not counted ({NO_RUN_LOG})" in line for line in replay.lines) == 3
    assert record["alarms"]["repeat"]["state"] == "no"


def test_e2_4(replays):
    """E2-4: health on these files: lead/reviewer judged 5, escapes 2 (untyped, counted), not flagged for quality (0.4 is not above 0.5), as 0a 5.5
    predicted; root's text has no `not its` part."""
    replay = replays("E2")
    reviewer = replay.agents["lead/reviewer"]
    assert (reviewer.judged, reviewer.escapes, reviewer.not_its) == (5, 2, {})
    assert "low_quality" not in reviewer.flags
    assert "escapes 2 of 5 judged" in replay.root_health and "not its" not in replay.root_health


def test_e2_5(replays):
    """E2-5: the timeline: contract v2 and v3 not confirmed; playbook v2 (lead) and v3 with no admission recorded."""
    replay = replays("E2")
    record = service(replay)
    contracts = {m["version"]: m for m in marks(record, "contract")}
    assert (contracts[2]["adds"], contracts[2]["not_confirmed"]) == (["C8", "C9"], ["C8", "C9"]) and (contracts[3]["adds"], contracts[3]["not_confirmed"]) == (["C10"], ["C10"])
    assert contracts[2]["confirmed"] == [] and contracts[3]["confirmed"] == []
    playbooks = {m["version"]: m for m in marks(record, "playbook")}
    assert (playbooks[2]["by"], playbooks[2]["basis"], playbooks[3]["basis"]) == ("lead", "legacy", "legacy")
    assert any(f"playbook v2 (lead): {NO_ADMISSION}" in line for line in replay.lines) and any(f"playbook v3 (lead): {NO_ADMISSION}" in line for line in replay.lines)
    assert "    2026-10-18 04:01 contract v2 (root): adds C8, C9: not confirmed" in replay.lines


def test_e2_6(replays):
    """E2-6: moved past: none."""
    replay = replays("E2")
    assert replay.data["moved_past"] == [] and "Blocked tasks moved past without a verdict: none." in replay.lines


# ------------------------------------------------------------------------------------------------------------------ A5


def test_a5_1(replays):
    """A5-1: no service record; the one-off record has 1 case f768 (f768 and its two reworks 00cd and dfe0, both revising f768, tier not recorded); 3
    deliveries by the lead; nothing judged; the first delivery has no verdict, superseded by dfe0; f768 is without a verdict and never counted as accepted;
    no escape; no verdict off a delivery."""
    replay = replays("A5")
    f768 = "20261017T214038108044-root-f768"
    assert replay.data["services"] == [] and replay.data["nested"] == []
    record = replay.data["one_off"]
    assert (record["service"], record["owner"], record["budget"]) == ("", "", None)
    (only,) = record["cases"]
    assert only["id"] == f768 and only["tasks"] == 3 and only["state"] == "done"
    (case_record,) = one_off_record(replay).cases
    assert [(t.id, t.revises) for t in case_record.tasks] == [
        (f768, None), ("20261017T215111184137-root-00cd", f768), ("20261017T215450859628-root-dfe0", f768),
    ]
    assert all(t.source is None for t in case_record.tasks)  # the tier was not recorded
    assert sorted(d.result.id for d in one_off_record(replay).deliveries) == [
        "20261017T215429559499-lead-82b3", "20261017T215432951514-lead-463e", "20261017T215747445161-lead-26db",
    ]
    assert (record["deliveries"]["total"], record["deliveries"]["judged"]) == (3, 0)
    assert only["first"] == {"task": f768, "outcome": "none", "superseded_by": "20261017T215450859628-root-dfe0", "superseded_source": "unrecorded"}
    assert record["first_deliveries"]["no_verdict"] == 1 and record["first_deliveries"]["accepted"] == 0 and record["first_deliveries"]["superseded"] == 1
    assert record["deliveries"]["unjudged_cases"] == [f768]  # one case without a verdict, never counted as accepted
    assert record["escapes"] == [] and record["deliveries"]["not_on_a_delivery"] == []
    assert "  escapes (the team reported done, then the user rejected it): none (judged: 0 of 3)" in replay.lines


def test_a5_2(replays):
    """A5-2: repeat does not apply to one-off tasks; the cost alarm skips f768, which reads `runs not counted (no run log in its window)` (done, uncut, no
    log kept; the lead's charter `created`, 21:40:38, is not after the head task, 21:40:38.108044, so reason 2 does not apply); top-ups +4, +4 (tier not
    recorded) and +3 (the grant 7620)."""
    replay = replays("A5")
    record = replay.data["one_off"]
    assert record["alarms"]["repeat"]["state"] == "does not apply"
    assert "    repeat: does not apply (one-off tasks name no criterion ids)" in replay.lines
    assert "    cost: n/a (0 of 3 judged cases); skipped: 20261017T214038108044-root-f768 (runs not counted)" in replay.lines
    (only,) = record["cases"]
    assert only["runs_unknown"] == NO_RUN_LOG  # reason 3, not reason 2 (the lead was hired before the head task)
    assert only["top_ups"] == [
        {"id": "20261017T215111184137-root-00cd", "source": "unrecorded", "amount": 4},
        {"id": "20261017T215450859628-root-dfe0", "source": "unrecorded", "amount": 4},
        {"id": "20261017T215533405230-root-7620", "source": "granted", "amount": 3},
    ]


def test_a5_3(replays):
    """A5-3: every delivery is signed off by `lead`: the reports' boxes were not kept."""
    deliveries_of_the_case = one_off_record(replays("A5")).deliveries
    assert len(deliveries_of_the_case) == 3 and {d.signer for d in deliveries_of_the_case} == {"lead"}
    assert replays("A5").data["one_off"]["verifiers"] == []
    assert "  verifiers: none (every delivery was signed off by lead itself)" in replays("A5").lines


def test_a5_4(replays):
    """A5-4: the one-off block of 9.3's A5 sample equals the output's block byte for byte (the P golden `quality/a5_one_off_block.txt`, checked by
    `tests/golden/test_golden_quality.py::test_a5_one_off_block`); moved past: none."""
    replay = replays("A5")
    assert replay.data["moved_past"] == [] and "Blocked tasks moved past without a verdict: none." in replay.lines


# ------------------------------------------------------------------------------------------------------------------ E3

E3_DD87, E3_207B, E3_AB46 = "20261021T152347923195-root-dd87", "20261021T153031017749-root-207b", "20261021T153809201054-root-ab46"
E3_CONTRACT_GAP = "lead/reviewer: escapes 0 of 5 judged; not its: 2 contract-gap; PASS precision 5 of 5; its FAILs before delivery: 2 re-check(s), 2 author rework run(s)"


def e3_cases(replay: Replay) -> list[Any]:
    return service_record(replay).cases


def test_e3_1(replays):
    """E3-1: no cost alarm: the user's runs 12, 5 and 14 against 15, 15 and 20 approved (0.80x, 0.33x, 0.70x; the totals 12, 15, 14). The approved runs
    are the contract's 15, raised only at ab46's rework (`...-2ccf`: 9 used + 6 held + 5 = 20); at dd87's rework (`...-d995`: 4 used + 2 held + 6 = 12)
    nothing is raised."""
    replay = replays("E3")
    record = service(replay)
    assert [(c["id"], c["budget"], c["user_cost"], c["user_approved"], c["ratio"], c["spend"]) for c in record["cases"]] == [
        (E3_DD87, 15, 12, 15, "0.80", 12), (E3_207B, 15, 5, 15, "0.33", 15), (E3_AB46, 15, 14, 20, "0.70", 14),
    ]
    assert [c.user_ceiling for c in e3_cases(replay)] == [15, 15, 20]  # the ceiling of dd87's rework is 12, below the contract's 15: no rise
    assert record["alarms"]["cost"] == {"state": "no", "judged": 3, "compared": 3, "cases": [], "skipped": []}
    assert "    cost: no (0 of 3 cases above 1.25x)" in replay.lines
    assert "    20261021T153809201054-root-ab46 \"Memo for the meeting of 2026-10-19\": 14 of 20 approved (0.70x); top-ups: +5 human rework 20261021T154215162562-root-2ccf" in replay.lines


def test_e3_2(replays):
    """E3-2: R1's unconfirmed link (C6, C3, the rejection's own `criterion`) is not counted by the repeat alarm and is listed as `not counted`."""
    replay = replays("E3")
    repeat = service(replay)["alarms"]["repeat"]
    assert repeat["not_counted"] == {"R1": ["C6", "C3"]} and repeat["state"] == "no"
    assert "R1" in repeat["subjects"] and "C6" not in repeat["subjects"] and "C3" not in repeat["subjects"]
    assert "    repeat: no (3 judged cases; counted: R1, R2, C11); not counted: R1's reading C6, C3 (not confirmed)" in replay.lines


def test_e3_3(replays):
    """E3-3: the superseded `...-root-248f` (its result `...-lead-e0d6` is blocked, and rework 52d7 follows) is not counted as a block moved past: the
    section is `none`."""
    replay = replays("E3")
    assert any(m.id == "20261021T153358013532-lead-e0d6" and m.status == "blocked" and m.reply_to.endswith("-root-248f") for m in replay.org.sent("lead"))
    assert replay.data["moved_past"] == []
    assert "Blocked tasks moved past without a verdict: none." in replay.lines


def test_e3_4(replays):
    """E3-4: contract-gap rejects are not shown as the verifier's escapes: R1 `contract-gap` (words, "always"), R2 `contract-gap` (answer, the link
    `...-root-8ca0` names C11, which contract v2 does not have), both attributed `not its`."""
    replay = replays("E3")
    record = service(replay)
    first, second = record["escapes"]
    assert (first["assertion"], first["cause"], first["rule"], first["detail"], first["attribution"]) == ("R1", "contract-gap", "words", ["always"], "not its")
    assert (second["assertion"], second["cause"], second["rule"], second["detail"], second["attribution"]) == (
        "R2", "contract-gap", "answer", ["20261021T154557001479-root-8ca0", "C11"], "not its",
    )
    assert first["signer"] == second["signer"] == "lead/reviewer"
    (verifier,) = record["verifiers"]
    assert (verifier["addr"], verifier["judged"], verifier["escapes"], verifier["pass_precision"]) == (
        "lead/reviewer", 5, {"counted": {}, "not_its": {"contract-gap": 2}}, [5, 5],
    )
    assert f"    {E3_CONTRACT_GAP}" in replay.lines
    assert "escapes 0 of 5 judged (+2 not its: 2 contract-gap)" in replay.root_health  # root's reading of health
    assert "escapes 0 of 5 judged" in replay.agent_health and "not its" not in replay.agent_health  # an agent's
    assert "low_quality" not in replay.agents["lead/reviewer"].flags  # not flagged
    (reviewer,) = [a for a in [replay.agents["lead/reviewer"]]]
    assert (reviewer.judged, reviewer.escapes, reviewer.not_its) == (5, 0, {"contract-gap": 2})


def test_e3_5(replays):
    """E3-5: the text of 9.3's E3 sample equals the output byte for byte (the P golden `quality/e3.txt` is the design's sample; `test_golden_quality.py::
    test_e3_text` checks it through `golden_support.check`)."""
    from testkit import TESTS

    sample = (TESTS / "golden" / "expected" / "quality" / "e3.txt").read_text(encoding="utf-8")
    assert replays("E3").text + "\n" == sample


def test_e3_6(replays):
    """E3-6: case 207b has 10 runs in relayed reworks; its user's runs are 5 (total 15), and its relayed line reads `your relayed reworks: 10 run(s), your
    own spend; total 15`."""
    replay = replays("E3")
    c207b = case(service(replay), "207b")
    assert (c207b["relayed_runs"], c207b["user_cost"], c207b["spend"], c207b["runs"]) == (10, 5, 15, 15)
    assert "      your relayed reworks: 10 run(s), your own spend; total 15" in replay.lines
    assert sum("your relayed reworks:" in line for line in replay.lines) == 1  # shown only for a case that has relayed runs


def test_e3_7(replays):
    """E3-7 (the variant `r2-links-r1`, constructed: one more human-tier link, 'same as R1', on R2's rejection): the repeat alarm fires on real files with
    `repeat: FIRES: R1 failed in 2 of the last 3 judged cases (cases ...dd87, ...ab46)`; R2's cause is unchanged (contract-gap by answer: C11 stays in R2's
    `confirmed`); the cost line is unchanged. The unconfirmed reading of R1 stays on the line as `not counted`."""
    replay = replays("E3", "r2-links-r1")
    record = service(replay)
    fires = f"    repeat: FIRES: R1 failed in 2 of the last 3 judged cases (cases {E3_DD87}, {E3_AB46})"
    (line,) = [x for x in replay.lines if x.startswith("    repeat:")]
    assert line == f"{fires}; not counted: R1's reading C6, C3 (not confirmed)"
    assert (record["alarms"]["repeat"]["state"], record["alarms"]["repeat"]["fired"]) == ("fires", ["R1"])
    assert record["alarms"]["repeat"]["window"] == [E3_DD87, E3_207B, E3_AB46]
    (_, second) = service_record(replay).escapes
    delivery, cause = second
    assert (cause.type, cause.rule, cause.detail) == ("contract-gap", "answer", ("20261021T154557001479-root-8ca0", "C11"))
    assert "C11" in delivery.decisive.confirmed
    assert record["escapes"][1]["cause"] == "contract-gap" and record["escapes"][1]["rule"] == "answer"
    assert "    cost: no (0 of 3 cases above 1.25x)" in replay.lines


@pytest.mark.parametrize(
    "count, user_cost, fires, ratio",
    [(12, 26, True, "1.30"), (11, 25, False, "1.25")],
    ids=["N=12 fires at 1.30x", "N=11 is exactly 1.25x and reads no"],
)
def test_e3_9_the_constructed_variant_r3_overspend(replays, count, user_cost, fires, ratio):
    """E3-9 (D-E5-6; **a constructed variant, not an observation**, 19.1): N empty run logs of `lead` are added inside ab46's window, so that the cost
    alarm has a case to fire on: no study corpus fires it under this rule. N=12 gives 26 charged runs, the user's runs 26 against 20 approved (1.30x) and
    `cost: FIRES: case ...-root-ab46 26 of 20 approved (1.30x)`; N=11 gives 25, exactly 1.25 x 20, and `cost: no (0 of 3 cases above 1.25x)`. The two
    replays pin the boundary of `Fraction(user_cost) > cost_ratio * user_approved` on files."""
    replay = replays("E3", f"r3-overspend-{count}")
    record = service(replay)
    ab46 = case(record, "ab46")
    assert (ab46["runs"], ab46["user_cost"], ab46["user_approved"], ab46["ratio"], ab46["relayed_runs"], ab46["spend"]) == (user_cost, user_cost, 20, ratio, 0, user_cost)
    (cost_line,) = [x for x in replay.lines if x.startswith("    cost:")]
    if fires:
        assert cost_line == f"    cost: FIRES: case {E3_AB46} 26 of 20 approved (1.30x)"
        assert record["alarms"]["cost"]["state"] == "fires"
        assert record["alarms"]["cost"]["cases"] == [{"case": E3_AB46, "user_cost": 26, "user_approved": 20, "ratio": "1.30", "relayed_runs": 0, "total": 26}]
    else:
        assert cost_line == "    cost: no (0 of 3 cases above 1.25x)"
        assert record["alarms"]["cost"]["state"] == "no" and record["alarms"]["cost"]["cases"] == []
    assert [c["user_cost"] for c in record["cases"] if not c["id"].endswith("ab46")] == [12, 5]  # the other cases are the observed ones


# ------------------------------------------------------------------------------------------------------------------ E4

DESIGN = REPO / "docs" / "design" / "org-growth-phase-0b.md"
S1R = "E4-s1r"


def s1r_excerpt() -> list[str]:
    """The lines of the code block that follows the heading of 9.3's E4 s1r excerpt in the design."""
    lines = DESIGN.read_text(encoding="utf-8").splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("**E4 s1r's files, excerpt**")), None)
    if start is None:
        pytest.fail(f"{DESIGN} has no `**E4 s1r's files, excerpt**` heading: S1R-6 has nothing to compare with")
    opening = next(i for i in range(start, len(lines)) if lines[i] == "```")
    closing = next(i for i in range(opening + 1, len(lines)) if lines[i] == "```")
    return lines[opening + 1 : closing]


def final_status_line(stream: str, number: int) -> str:
    return (EV / stream / "final-services-progress-status-health.txt").read_text(encoding="utf-8").splitlines()[number - 1]


def test_s2r_1(replays):
    """S2R-1: s2r's playbook v2 is shown with content beyond C9: its mark reads `admitted (c) on R1, C9: 7 changed line(s): 0 the cited criteria's own
    words, 7 beyond them; 4 line(s) removed`, and its `--json` `lines` carry the two vague-deadline lines the gate quotes, next to C9's text in `cited`."""
    replay = replays("E4-s2r")
    record = service(replay)
    (v2,) = [m for m in marks(record, "playbook") if m["version"] == 2]
    assert (v2["basis"], v2["by"], v2["evidence"], v2["changed"], v2["own_words"], v2["beyond"], v2["removed"]) == ("c", "lead", ["R1", "C9"], 7, 0, 7, 4)
    assert "    2026-10-22 21:24 playbook v2 (lead): admitted (c) on R1, C9: 7 changed line(s): 0 the cited criteria's own words, 7 beyond them; 4 line(s) removed" in replay.lines
    texts = [line["text"] for line in v2["lines"]]
    assert "- Flag any vague deadline as `none` and add an Open questions item for it, rather than converting it to a date." in texts
    assert any("Require the writer to leave vague deadlines as `none` and add an Open questions item" in text for text in texts)
    assert v2["agent_written"] is True and not any(line["own_words"] for line in v2["lines"])
    c9, _ = evidence("s2r/service/current-SERVICE.md")  # the kept contract: C9 is the 9th acceptance criterion of v2 and v3
    assert v2["cited"] == [{"id": "C9", "text": c9["acceptance"][8]}]
    assert c9["acceptance"][8].startswith("The memo starts with a one-line summary of the meeting that begins with 'Summary:'")


def test_s1r_1(replays):
    """S1R-1: s1r's four unconfirmed amendments are not counted as client evidence: every criterion v2-v5 added except C9 is marked `not confirmed`; none
    is a repeat subject or a contract-gap answer; C9 is confirmed by the link `...-root-1753` (0a.1's rule for a version without `answers`)."""
    replay = replays(S1R)
    record = service(replay)
    contracts = {m["version"]: m for m in marks(record, "contract")}
    assert [contracts[v]["adds"] for v in (2, 3, 4, 5)] == [["C8", "C9"], ["C10"], ["C11"], ["C12", "C13"]]
    assert [contracts[v]["confirmed"] for v in (2, 3, 4, 5)] == [[{"id": "C9", "link": "20261022T190014222948-root-1753"}], [], [], []]
    assert [contracts[v]["not_confirmed"] for v in (2, 3, 4, 5)] == [["C8"], ["C10"], ["C11"], ["C12", "C13"]]
    assert all(contracts[v]["basis"] == "legacy" and contracts[v]["answers"] is None for v in (2, 3, 4, 5))  # none is an answer to an assertion
    (escape,) = record["escapes"]
    assert escape["detail"] == ["20261022T190014222948-root-1753", "C9"]  # the one contract-gap answer names C9 and no unconfirmed id
    low = QualityThresholds(min_judged=1, repeat_failures=1)  # what the repeat alarm would count if one judged case were enough
    assert set(dict(repeat_alarm(service_record(replay), low).subjects)) == {"R1", "C9"}


def test_s1r_2(replays):
    """S1R-2: s1r's unrecorded rejects 2 and 3 are shown as missing verdicts: cases `...-root-114d` and `...-root-2efa` are without a verdict and never
    counted as accepted; judged 1 of 3."""
    replay = replays(S1R)
    record = service(replay)
    assert record["deliveries"]["unjudged_cases"] == ["20261022T191407596413-root-114d", "20261022T192724706946-root-2efa"]
    assert (record["deliveries"]["judged"], record["deliveries"]["total"]) == (1, 3)
    assert record["first_deliveries"] == {"accepted": 0, "rejected": 1, "no_verdict": 2, "superseded": 0, "neither": 0, "never_delivered": 0}
    assert any(
        line.startswith("  judged by the user: 1 of 3 deliveries; without a verdict: 2 case(s) (20261022T191407596413-root-114d, 20261022T192724706946-root-2efa): never counted as accepted;")
        for line in replay.lines
    )


def test_s1r_3(replays):
    """S1R-3: s1r's 16 runs are shown as held behind blocks the conversation moved past: `lead holds 12 run(s)` with task `...-root-3559` (`left blocked:
    you have sent lead 2 task(s) since`), and `lead/writer holds 4 run(s)` with `...-lead-e679` (`left blocked: lead has sent lead/writer 1 task(s)
    since`) and `...-lead-808c` (`blocked, nothing sent since`); `...-lead-0d54` is not listed (`...-lead-cc98` revises it, so it is released). The replay
    derives 12 and 4 from the materialized files; they must equal s1r's final `status` (lines 31 and 34 of `final-services-progress-status-health.txt`),
    and a difference fails the test and stops the FEAT: the expectation is not adjusted."""
    replay = replays(S1R)
    lead, writer = replay.data["moved_past"]
    assert (lead["addr"], lead["held"], writer["addr"], writer["held"]) == ("lead", 12, "lead/writer", 4)
    assert [(t["id"], t["sender"], t["left_blocked"], t["sent_since"]) for t in lead["tasks"]] == [("20261022T190015448581-root-3559", "root", True, 2)]
    assert [(t["id"], t["sender"], t["left_blocked"], t["sent_since"]) for t in writer["tasks"]] == [
        ("20261022T191728726797-lead-e679", "lead", True, 1), ("20261022T193406984560-lead-808c", "lead", False, 0),
    ]
    assert not any(t["id"].endswith("-lead-0d54") for p in replay.data["moved_past"] for t in p["tasks"])
    assert any(m.id.endswith("-lead-cc98") and m.revises and m.revises.endswith("-lead-0d54") for m in replay.org.sent("lead"))  # so it is released
    for text in (
        "    task 20261022T190015448581-root-3559 from you (\"Rework memo 2026-10-05: Summary line first, Sam's CI due date\"), blocked 2026-10-22 19:11: left blocked: you have sent lead 2 task(s) since",
        "    task 20261022T191728726797-lead-e679 from lead, blocked 2026-10-22 19:18: left blocked: lead has sent lead/writer 1 task(s) since",
        "    task 20261022T193406984560-lead-808c from lead, blocked 2026-10-22 19:35: blocked, nothing sent since",
        "  lead holds 12 run(s):", "  lead/writer holds 4 run(s):",
    ):
        assert text in replay.lines
    status_lead, status_writer = final_status_line("s1r", 31), final_status_line("s1r", 34)  # the recorded `status`: budget = the runs the agent holds
    assert status_lead.startswith("  lead [Manager]") and status_writer.startswith("    writer [Writer]")
    assert (int(re.search(r"budget=(\d+)", status_lead)[1]), int(re.search(r"budget=(\d+)", status_writer)[1])) == (lead["held"], writer["held"])
    checker = final_status_line("s1r", 41)  # the recorded health line of the checker: its FAIL counts
    assert checker.startswith("  checker idle") and "re-checks after a FAIL 1 (author rework runs 1)" in checker
    (verifier,) = service(replay)["verifiers"]
    assert (verifier["addr"], verifier["rechecks"], verifier["rework_runs"]) == ("lead/checker", 1, 1)


def test_s1r_4(replays):
    """S1R-4: the three final memos are not as delivered (they differ from the team's current files; no `relayed` finding exists, since the corpus
    predates 0a.3), with the no-history remark; R1 (recorded 18:59:00) predates the last write of `memo-2026-10-05.md` (19:12:45.031, pinned in the
    manifest), so it is counted and stays an escape (D20); the deliveries of `...-114d` and `...-2efa` have no verdict, so they count as neither pass nor
    escape; 0 deliveries judged after an edit."""
    replay = replays(S1R)
    record = service(replay)
    ed94, c114d, c2efa = "20261022T182945409755-root-ed94", "20261022T191407596413-root-114d", "20261022T192724706946-root-2efa"
    assert record["deliveries"]["not_as_delivered"] == [{"case": c, "task": c} for c in (ed94, c114d, c2efa)]
    assert (record["deliveries"]["relayed_only"], record["deliveries"]["unseen_relayed"], record["deliveries"]["neither"]) == ([], [], [])
    assert record["files_error"] == ""
    assert f"not as delivered: 3 ({ed94}, {c114d}, {c2efa}) (compared with the team's current files: no org history)" in " ".join(replay.lines)
    deliveries_of_the_case = {d.task.id: d for d in service_record(replay).deliveries}
    first = deliveries_of_the_case[ed94]
    assert first.edited and first.edited_at == 1792696365031000  # 19:12:45.031Z, the manifest's pin
    assert first.voided == () and first.escape and first.judged  # R1 (18:59:00) is before the edit: counted, an escape
    for task in (c114d, c2efa):
        assert deliveries_of_the_case[task].edited and not deliveries_of_the_case[task].judged and not deliveries_of_the_case[task].escape
    assert not [d for d in service_record(replay).deliveries if d.voided]  # 0 deliveries judged after an edit
    assert len(record["escapes"]) == 1 and record["escapes"][0]["assertion"] == "R1"
    assert record["verifiers"][0]["judged"] == 1 and record["verifiers"][0]["pass_precision"] == [1, 1]


def test_s1r_5(replays):
    """S1R-5: R1 is `contract-gap` (answer: the link `...-root-1753` names C9, which contract v1 does not have), signed off by lead/checker, with no `also`
    (rule 5 matches "always" too, the same type; `rules` = `["answer", "words"]`); case `...-root-ed94`: the user's runs 18 of 19 approved (0.95x)
    (`user_spend` is 19; one relayed run may lie in a later request, so `user_cost` leaves it out), 5 of its 23 runs in the relayed rework `...-9ce9`, its
    window cut; repeat and cost `n/a (1 of 3 judged cases)`."""
    replay = replays(S1R)
    record = service(replay)
    (escape,) = record["escapes"]
    assert (escape["assertion"], escape["cause"], escape["rule"], escape["rules"], escape["also"], escape["signer"]) == (
        "R1", "contract-gap", "answer", ["answer", "words"], [], "lead/checker",
    )
    assert escape["detail"] == ["20261022T190014222948-root-1753", "C9"] and escape["attribution"] == "not its"
    ed94 = case(record, "ed94")
    assert (ed94["user_cost"], ed94["user_approved"], ed94["ratio"], ed94["runs"], ed94["relayed_runs"], ed94["spend"], ed94["cut"]) == (18, 19, "0.95", 23, 5, 25, True)
    (case_ed94,) = [c for c in service_record(replay).cases if c.id.endswith("-root-ed94")]
    assert user_spend(case_ed94) == 19 and case_ed94.relayed_overlap == 1 and user_cost(case_ed94) == 18  # one relayed run may lie in a later request
    assert [t["id"] for t in ed94["top_ups"] if t["source"] == "relayed"] == ["20261022T184712524029-root-9ce9"]
    assert any(line.startswith("    repeat: n/a (1 of 3 judged cases)") for line in replay.lines) and "    cost: n/a (1 of 3 judged cases)" in replay.lines
    assert (record["alarms"]["repeat"]["state"], record["alarms"]["cost"]["state"]) == ("n/a", "n/a")
    assert "(0.95x)" in next(line for line in replay.lines if "-root-ed94 " in line and "approved" in line)


def test_s1r_6(replays):
    """S1R-6: every line of 9.3's s1r excerpt that has no angle brackets equals the output's line byte for byte (in the excerpt's order)."""
    replay = replays(S1R)
    excerpt = s1r_excerpt()
    plain = [line for line in excerpt if "<" not in line and ">" not in line]
    assert len(excerpt) > 25 and len(plain) > 20
    position = 0
    for line in plain:
        found = next((i for i in range(position, len(replay.lines)) if replay.lines[i] == line), None)
        assert found is not None, f"the line of the excerpt is not in the output, in order: {line!r}"
        position = found + 1


def test_s2r_2(replays):
    """S2R-2: s2r's Marta escape is typed as a relayed carry-over: R2 (`...-root-f6dc` on `...-root-342a`) is `relayed-carry-over` through `...-root-43b8`
    and `lead/writer/work/2026-10-05-memo.md`, `also contract-gap` (the link `...-root-d23a` names C10, which contract v1 of 342a lacks); `rules` starts
    `["carry-over", "answer"]`."""
    replay = replays("E4-s2r")
    _, r2 = service(replay)["escapes"]
    assert r2["assertion"] == "R2" and r2["verdict"].endswith("-root-f6dc") and r2["task"] == "20261022T212050615269-root-342a"
    assert (r2["cause"], r2["rule"], r2["detail"], r2["also"]) == (
        "relayed-carry-over", "carry-over", ["20261022T211157827631-root-43b8", "lead/writer/work/2026-10-05-memo.md"], ["contract-gap"],
    )
    assert r2["rules"][:2] == ["carry-over", "answer"] and r2["attribution"] == "not its"
    (_, cause) = service_record(replay).escapes[1]
    assert cause.version == 1  # contract v1 of 342a: it lacks C10, which the link d23a names
    assert any(m.id.endswith("-root-d23a") and m.criterion == "C10" for m in replay.org.sent(ROOT))


def test_s2r_3(replays):
    """S2R-3: R1 (`...-root-a9fd`) is `contract-gap` (answer: the link `...-root-b255` names C9), with no `also`, and `before_verdict` `...-root-43b8`; case
    `...-root-f230`: the user's runs 14 of 24 approved (0.58x), 5 in relayed rework 43b8, total 19; judged 2 of 3 deliveries (43b8's delivery is superseded
    by the human rework 342a); alarms `n/a (1 of 3 judged cases)`; not as delivered 0; the view's verifier line `lead/reviewer: escapes 0 of 2 judged; not its:
    1 contract-gap, 1 relayed-carry-over; PASS precision 2 of 2; ...`; health for root `escapes 0 of 2 judged (+2 not its: 1 contract-gap, 1
    relayed-carry-over)`; moved past: none."""
    replay = replays("E4-s2r")
    record = service(replay)
    r1, _ = record["escapes"]
    assert r1["assertion"] == "R1" and r1["verdict"].endswith("-root-a9fd")
    assert (r1["cause"], r1["rule"], r1["also"], r1["before_verdict"]) == ("contract-gap", "answer", [], "20261022T211157827631-root-43b8")
    assert r1["detail"][0].endswith("-root-b255") and r1["detail"][1:] == ["C9"]
    f230 = case(record, "f230")
    assert (f230["user_cost"], f230["user_approved"], f230["ratio"], f230["relayed_runs"], f230["spend"]) == (14, 24, "0.58", 5, 19)
    assert [t["id"] for t in f230["top_ups"] if t["source"] == "relayed"] == ["20261022T211157827631-root-43b8"]
    assert (record["deliveries"]["judged"], record["deliveries"]["total"]) == (2, 3)
    superseded = {d.task.id: d.superseded for d in service_record(replay).deliveries}
    assert superseded["20261022T211157827631-root-43b8"] == "20261022T212050615269-root-342a"
    assert (record["alarms"]["repeat"]["state"], record["alarms"]["cost"]["state"]) == ("n/a", "n/a")
    assert any(line.startswith("    repeat: n/a (1 of 3 judged cases)") for line in replay.lines) and "    cost: n/a (1 of 3 judged cases)" in replay.lines
    assert record["deliveries"]["not_as_delivered"] == []
    assert any(line.startswith("    lead/reviewer: escapes 0 of 2 judged; not its: 1 contract-gap, 1 relayed-carry-over; PASS precision 2 of 2; ") for line in replay.lines)
    assert "escapes 0 of 2 judged (+2 not its: 1 contract-gap, 1 relayed-carry-over)" in replay.root_health
    assert replay.data["moved_past"] == []


def test_s3_1(replays):
    """S3-1: no cost alarm fires (this was a firing expectation before D-E5-6): `...-root-88b2` the user's runs 16 of 25 approved (0.64x), 5 in relayed
    rework `...-root-fe20`, total 21; `...-root-cdef` 5 of 15 (0.33x), 5 relayed, total 10; `...-root-6947` 15 of 18 (0.83x); the alarm reads `no (0 of 3
    cases above 1.25x)`."""
    replay = replays("E4-s3")
    record = service(replay)
    assert [(c["id"][-4:], c["user_cost"], c["user_approved"], c["ratio"], c["relayed_runs"], c["spend"]) for c in record["cases"]] == [
        ("88b2", 16, 25, "0.64", 5, 21), ("cdef", 5, 15, "0.33", 5, 10), ("6947", 15, 18, "0.83", 0, 15),
    ]
    assert [t["id"] for t in case(record, "88b2")["top_ups"] if t["source"] == "relayed"] == ["20261022T215128895860-root-fe20"]
    assert record["alarms"]["cost"] == {"state": "no", "judged": 3, "compared": 3, "cases": [], "skipped": []}
    assert "    cost: no (0 of 3 cases above 1.25x)" in replay.lines


def test_s3_2(replays):
    """S3-2: R1 (`...-root-ac19` on `...-root-4510`) is `contract-gap` (answer: the link `...-root-1fb7` names C8, which contract v1 does not have), with no
    `also`, and `before_verdict` `...-root-fe20`; repeat `no (3 judged cases; counted: R1, C8)`."""
    replay = replays("E4-s3")
    (r1,) = service(replay)["escapes"]
    assert r1["assertion"] == "R1" and r1["verdict"].endswith("-root-ac19") and r1["task"] == "20261022T214612649634-root-4510"
    assert (r1["cause"], r1["rule"], r1["also"], r1["before_verdict"]) == ("contract-gap", "answer", [], "20261022T215128895860-root-fe20")
    assert r1["detail"] == ["20261022T215837117856-root-1fb7", "C8"]
    assert "    repeat: no (3 judged cases; counted: R1, C8)" in replay.lines


def test_s3_3(replays):
    """S3-3: first deliveries 0 accepted, 0 rejected, 3 without a verdict, all superseded (`...-88b2` by the human rework `...-4510`, `...-cdef` by the
    relayed rework `...-116b`, `...-6947` by the human rework `...-3286`); judged 4 of 8 deliveries; not as delivered 0."""
    replay = replays("E4-s3")
    record = service(replay)
    assert record["first_deliveries"] == {"accepted": 0, "rejected": 0, "no_verdict": 3, "superseded": 3, "neither": 0, "never_delivered": 0}
    assert [(c["id"][-4:], c["first"]["superseded_by"][-4:], c["first"]["superseded_source"]) for c in record["cases"]] == [
        ("88b2", "4510", "human"), ("cdef", "116b", "relayed"), ("6947", "3286", "human"),
    ]
    assert (record["deliveries"]["judged"], record["deliveries"]["total"]) == (4, 8)
    assert record["deliveries"]["not_as_delivered"] == []


def test_s3_4(replays):
    """S3-4: the user's accept on the relayed rework `...-root-116b` counts as a judged delivery (F-E3-10); the view's verifier line `lead/reviewer: escapes
    0 of 4 judged; not its: 1 contract-gap; PASS precision 4 of 4; ...`; health for root `escapes 0 of 4 judged (+1 not its: 1 contract-gap)`."""
    replay = replays("E4-s3")
    (delivery,) = [d for d in service_record(replay).deliveries if d.task.id.endswith("-root-116b")]
    assert delivery.task.source == "relayed" and delivery.judged and [(v.verdict, v.tier) for v in delivery.counted] == [("accept", "human")]
    assert any(line.startswith("    lead/reviewer: escapes 0 of 4 judged; not its: 1 contract-gap; PASS precision 4 of 4; ") for line in replay.lines)
    assert "escapes 0 of 4 judged (+1 not its: 1 contract-gap)" in replay.root_health


def test_s3_5(replays):
    """S3-5: moved past: none (the reviewer's blocked `...-lead-2133` is released by `...-lead-00e8`, which revises it)."""
    replay = replays("E4-s3")
    assert replay.data["moved_past"] == []
    lead_sent = {m.id[-4:]: m for m in replay.org.sent("lead")}
    assert lead_sent["00e8"].revises is not None and lead_sent["00e8"].revises.endswith("-lead-2133")
    assert any(m.status == "blocked" and m.reply_to.endswith("-lead-2133") for m in replay.org.sent("lead/reviewer"))


@pytest.mark.parametrize("corpus", ["E4-s1r", "E4-s2r", "E4-s3"])
def test_e4_all(replays, corpus):
    """E4-all: no charter or model mark (the organization is not a git repository): the unknown line in every block."""
    replay = replays(corpus)
    assert [m for m in service(replay)["timeline"] if m["kind"] in ("charter", "model")] == []
    assert service(replay)["history"] == {"known": False, "truncated": False, "skipped": 0}
    blocks = len(replay.data["services"]) + (replay.data["one_off"] is not None)
    assert replay.lines.count(f"    {NO_HISTORY}") == blocks == 1
