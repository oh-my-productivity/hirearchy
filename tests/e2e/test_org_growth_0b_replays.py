# mypy: ignore-errors
"""Phase 0b, the exit-check replays (design 19, plan FEAT-009): the quality view and health, read by the product's own code over the files the studies
kept. No scheduler, no LLM, no network, no git: ``testkit.org_replay.materialize`` builds the organization of a corpus from its kept files (design 19.1)
and ``Org`` opens it.

One test per expectation id of design 19.3, each written from the design's text before it ran. **An expectation is never edited to match the product**:
if a replay computes another value, the FEAT stops and the manager is told (19.3, "When an expectation fails"). A listed file that is missing, or a
message that does not parse, fails the test; nothing here skips.

This module holds E (E-1..E-5), E2 (E2-1..E2-6), A5 (A5-1..A5-4) and E3 (E3-1..E3-7 and the constructed variant of E3-9). A5-4 is also the golden ``quality/a5_one_off_block.txt``, E3-5 the
golden ``quality/e3.txt``, E3-8 the golden ``quality/e3.json`` with the schema and figure checks (``tests/golden/test_golden_quality.py``). E4 s1r, s2r and
s3 are the next block (S1R-1..S1R-6, S2R-1..S2R-3, S3-1..S3-5, E4-all); E5's three streams follow (E5S1-1..E5S3-7, E5-all; design 19.3 "E5"), then E6's (E6S1-1..E6S3-7, E6-all; 19.3 "E6", each with its own kit limit).

**Kit limit (E5).** The replay has no org git history, so OQ-2's given-delivery path and P3's `relayed` finding cannot run; with history the evidence shows
s1 and s2 relayed (no hand edit) and s3 differs (the md5 facts of E5S1-6, E5S2-6 and E5S3-6). Those two paths run on a real git history in
`test_org_growth_0b_given.py`. Every E5 test below says so in its docstring.
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, NamedTuple

import pytest
from testkit import REPO
from testkit.e4_replay import EV, evidence
from testkit.e5_replay import EV5
from testkit.org_replay import index_entries, materialize, md5_of, utc_us

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


# ------------------------------------------------------------------------------------------------------------------ E5 (design 19.3 "E5")

KIT_LIMIT = (
    "\n\n    Kit limit: the replay has no org git history, so OQ-2's given-delivery path and P3's `relayed` finding cannot run; with history the evidence shows\n"
    "    s1 and s2 relayed (no hand edit) and s3 differs (the md5 facts of E5S<n>-6). Both paths run on a real git history in test_org_growth_0b_given.py.\n    "
)


def kit_limit(test):
    """Appends the kit limit to a test's docstring (the manager's condition for the E5, E6 and E7 replays)."""
    test.__doc__ = (test.__doc__ or "") + KIT_LIMIT
    return test


WEEKLY = "weekly-meeting-memo"
GAP = "contract-gap"
C1_C7 = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
JUDGED_LINE = "  judged by the user: {j} of {n} deliveries; without a verdict: {u} case(s) ({ids}): never counted as accepted ({r} with only your own relayed verdict); not as delivered: 1"
NO_HISTORY_REMARK = "(compared with the team's current files: no org history)"
CASES_LINE = "  cases: 3 (done 3, failed 0, blocked 0, open 0 (stalled 0))"
NO_CUT = "  run attribution is by time window (08 3.3): 0 case(s) had their window cut by a later request."


def recorded_fails(stream: str) -> tuple[int, int]:
    """The reviewer's re-checks after a FAIL and author rework runs on the recorded health line of the stream (0a's `MailEscapeCounter`, unchanged)."""
    lines = (EV5 / stream / "final-services-progress-status-health.txt").read_text(encoding="utf-8").splitlines()
    (line,) = [x for x in lines if x.startswith("  reviewer idle")]
    found = re.search(r"re-checks after a FAIL (\d+) \(author rework runs (\d+)\)", line)
    return int(found[1]), int(found[2])


def mark_times(record: dict[str, Any], kind: str) -> list[tuple[str, int]]:
    return [(m["when"][:16], m["version"]) for m in marks(record, kind)]


def top_ups(record: dict[str, Any]) -> list[tuple[str, str, str, int]]:
    """``(minute, short task id, source, amount)`` of the top-up marks."""
    return [(m["when"][:16], m["id"][-4:], m["source"], m["amount"]) for m in marks(record, "top-up")]


def case_figures(record: dict[str, Any]) -> list[tuple[str, int, int, str, int, int, int, int, bool, str, int]]:
    return [
        (c["id"][-4:], c["user_cost"], c["user_approved"], c["ratio"], c["relayed_runs"], c["spend"], c["runs"], c["credited"], c["cut"], c["runs_unknown"], c["budget"])
        for c in record["cases"]
    ]


def evidence_versions(stream: str, memo: str) -> tuple[Any, dict[int, dict[str, object]]]:
    """The delivered file of the stream and the versions INDEX.txt lists for the team's file of that name."""
    index = EV5 / stream / "memos" / "versions" / "INDEX.txt"
    return EV5 / stream / "memos" / memo, {int(v["k"]): v for v in index_entries(index)[f"lead/writer/work/{memo}"]}


def check_common(replay: Replay, stream: str) -> None:
    """What every E5 stream shares (E5-all, per stream): the record, the thresholds, the unknown history, no one-off record, no nested service."""
    record = service(replay)
    assert (record["service"], record["owner"], record["client"], record["client_kind"], record["unit"]) == (WEEKLY, "lead", "root", "human", "case")
    assert (record["contract"], record["playbook"], record["budget"]) == (2, 2, 12)
    assert replay.data["one_off"] is None and replay.data["nested"] == [] and replay.data["notes"] == []
    assert replay.data["thresholds"]["source"] == "defaults" and THRESHOLDS in replay.lines
    assert CASES_LINE in replay.lines and NO_CUT in replay.lines and "One-off tasks you gave: none." in replay.lines
    assert [c["state"] for c in record["cases"]] == ["done"] * 3 and [c["cut"] for c in record["cases"]] == [False] * 3
    assert [c["credited"] for c in record["cases"]] == [0, 0, 0] and [c["stalled"] for c in record["cases"]] == [False] * 3
    assert record["history"] == {"known": False, "truncated": False, "skipped": 0} and f"    {NO_HISTORY}" in replay.lines
    assert [m for m in record["timeline"] if m["kind"] in ("charter", "model")] == []
    assert record["error"] == record["files_error"] == record["stalled_error"] == ""


# ---------------------------------------------------------------------------------------------------------------------- s1

F07A, AAE2, R963A = "20261024T030644000395-root-f07a", "20261024T031013210098-root-aae2", "20261024T031317713451-root-963a"
F549, A312, EE21 = "20261024T031843932122-root-f549", "20261024T032246939392-root-312a", "20261024T032536636989-root-ee21"
S1_LINK = "20261024T031733594650-root-8376"


@kit_limit
def test_e5s1_1(replays):
    """E5S1-1: s1's record, cases, deliveries and what the user judged: 6 deliveries, 3 judged (the human rework aae2 rejected, f549 and the human rework
    ee21 accepted); memo 1's case f07a is without a verdict because its latest delivery is the relayed rework 963a, which carries only the assistant's
    relayed reject (`relayed only`); 0 verdicts not on a delivery."""
    replay = replays("E5-s1")
    check_common(replay, "s1")
    record = service(replay)
    assert [c["id"] for c in record["cases"]] == [F07A, F549, A312] and [c["tasks"] for c in record["cases"]] == [3, 1, 2]
    assert deliveries(service_record(replay)) == [
        (F07A, "20261024T030905425682-lead-bb5a"), (AAE2, "20261024T031227292670-lead-5cbe"), (R963A, "20261024T031535111416-lead-592f"),
        (F549, "20261024T032121583165-lead-9525"), (A312, "20261024T032454611999-lead-8fdf"), (EE21, "20261024T032800275791-lead-1757"),
    ]
    assert (record["deliveries"]["total"], record["deliveries"]["judged"]) == (6, 3)
    by_task = {d.task.id: d for d in service_record(replay).deliveries}
    assert {t: [(v.verdict, v.message.id) for v in d.counted] for t, d in by_task.items() if d.judged} == {
        AAE2: [("reject", "20261024T031628904053-root-99d4")], F549: [("accept", "20261024T032246934196-root-4265")],
        EE21: [("accept", "20261024T032840970281-root-359a")],
    }
    assert [(v.verdict, v.tier) for v in by_task[R963A].verdicts] == [("reject", "relayed")] and by_task[R963A].counted == ()
    assert record["first_deliveries"] == {"accepted": 1, "rejected": 0, "no_verdict": 2, "superseded": 2, "neither": 0, "never_delivered": 0}
    assert case(record, "f07a")["first"] == {"task": F07A, "outcome": "none", "superseded_by": AAE2, "superseded_source": "human"}
    assert case(record, "f549")["first"]["outcome"] == "accepted"
    assert case(record, "312a")["first"] == {"task": A312, "outcome": "none", "superseded_by": EE21, "superseded_source": "human"}
    assert "  first deliveries: 1 accepted, 0 rejected, 2 without a verdict (2 superseded by a rework before a verdict)" in replay.lines
    assert f'    {F549}: accepted: "That one is right, all the items are there - keep it."' in replay.lines
    assert f"    {F07A}: no verdict (superseded by human rework {AAE2})" in replay.lines
    deliveries_ = record["deliveries"]
    assert (deliveries_["unjudged_cases"], deliveries_["relayed_only"], deliveries_["unseen_relayed"]) == ([F07A], [F07A], [])
    assert (deliveries_["not_on_a_delivery"], deliveries_["legacy_verdicts"], deliveries_["neither"]) == ([], 0, [])
    (judged_line,) = [x for x in replay.lines if x.startswith("  judged by the user:")]
    assert judged_line.startswith(JUDGED_LINE.format(j=3, n=6, u=1, ids=F07A, r=1))
    assert not any("verdicts not on a delivery" in x for x in replay.lines)


@kit_limit
def test_e5s1_2(replays):
    """E5S1-2: the one escape, R1 on aae2: contract-gap by the user's answer (the link names C8, which contract v1 lacks), signed off by lead/reviewer, not
    its; the relayed rework 963a was delivered between the delivery and the verdict. Health reads it as a gap, not a miss."""
    replay = replays("E5-s1")
    record = service(replay)
    (escape,) = record["escapes"]
    assert (escape["assertion"], escape["case"], escape["task"], escape["verdict"], escape["signer"]) == (
        "R1", F07A, AAE2, "20261024T031628904053-root-99d4", "lead/reviewer",
    )
    assert (escape["cause"], escape["rule"], escape["rules"], escape["detail"], escape["also"], escape["attribution"], escape["class"]) == (
        GAP, "answer", ["answer", "words"], [S1_LINK, "C8"], [], "not its", None,
    )
    assert escape["before_verdict"] == R963A
    assert (
        f"    R1 case {F07A}, signed off by lead/reviewer: contract-gap (the user's answer, link {S1_LINK}, names C8, which contract v1 of the task did not have); "
        f"your relayed rework {R963A} delivered after it and before the verdict: the user may have judged that version"
    ) in replay.lines
    (_, cause) = service_record(replay).escapes[0]
    assert cause.version == 1  # the rejected task carried contract v1, which lacks C8
    assert not any(m.source == "human" and m.revises and m.revises.endswith("-root-963a") for m in replay.org.sent(ROOT))  # no human rework followed the injection
    rechecks, rework = recorded_fails("s1")
    (verifier,) = record["verifiers"]
    assert (verifier["addr"], verifier["judged"], verifier["escapes"], verifier["pass_precision"], verifier["fails_error"]) == (
        "lead/reviewer", 3, {"counted": {}, "not_its": {GAP: 1}}, [3, 3], "",
    )
    assert (verifier["rechecks"], verifier["rework_runs"]) == (rechecks, rework) == (0, 0)
    assert "    lead/reviewer: escapes 0 of 3 judged; not its: 1 contract-gap; PASS precision 3 of 3; its FAILs before delivery: 0 re-check(s), 0 author rework run(s)" in replay.lines
    assert "escapes 0 of 3 judged (+1 not its: 1 contract-gap)" in replay.root_health
    assert "escapes 0 of 3 judged" in replay.agent_health and "not its" not in replay.agent_health
    reviewer = replay.agents["lead/reviewer"]
    assert (reviewer.judged, reviewer.escapes, reviewer.not_its) == (3, 0, {GAP: 1})


@kit_limit
def test_e5s1_3(replays):
    """E5S1-3: the timeline: the contract v2 answers R1 and is confirmed by the link (DR3-1's form), the playbook v2 adds C8's own words, the top-ups of
    the human reworks and of the relayed rework; no charter or model mark."""
    replay = replays("E5-s1")
    record = service(replay)
    contracts = {m["version"]: m for m in marks(record, "contract")}
    assert (contracts[1]["adds"], contracts[1]["basis"]) == (C1_C7, "first")
    assert (contracts[2]["by"], contracts[2]["adds"], contracts[2]["removes"], contracts[2]["basis"], contracts[2]["answers"]) == ("root", ["C8"], [], "answers", "R1")
    assert (contracts[2]["confirmed"], contracts[2]["not_confirmed"]) == ([{"id": "C8", "link": S1_LINK}], [])
    playbooks = {m["version"]: m for m in marks(record, "playbook")}
    assert (playbooks[1]["by"], playbooks[1]["basis"]) == ("root", "client")
    v2 = playbooks[2]
    assert (v2["by"], v2["basis"], v2["evidence"], v2["changed"], v2["own_words"], v2["beyond"], v2["removed"]) == ("lead", "c", ["C8", "R1", S1_LINK], 1, 1, 0, 0)
    assert mark_times(record, "contract") == [("2026-10-24T03:06", 1), ("2026-10-24T03:17", 2)]
    assert mark_times(record, "playbook") == [("2026-10-24T03:06", 1), ("2026-10-24T03:19", 2)]
    assert top_ups(record) == [
        ("2026-10-24T03:10", "aae2", "human", 12), ("2026-10-24T03:13", "963a", "relayed", 6), ("2026-10-24T03:25", "ee21", "human", 12),
    ]
    for line in (
        "    2026-10-24 03:06 contract v1 (C1, C2, C3, C4, C5, C6, C7)",
        "    2026-10-24 03:06 playbook v1 (root): written by the client (no admission needed)",
        f"    2026-10-24 03:17 contract v2 (root): adds C8: the user's answer to R1: C8 confirmed (link {S1_LINK})",
        f"    2026-10-24 03:19 playbook v2 (lead): admitted (c) on C8, R1, {S1_LINK}: 1 changed line(s): 1 the cited criteria's own words, 0 beyond them",
        f"    2026-10-24 03:10 top-up +12 run(s) to case {F07A}: human rework {AAE2}",
        f"    2026-10-24 03:13 top-up +6 run(s) to case {F07A}: your relayed rework {R963A} (your own spend)",
        f"    2026-10-24 03:25 top-up +12 run(s) to case {A312}: human rework {EE21}",
    ):
        assert line in replay.lines


@kit_limit
def test_e5s1_4(replays):
    """E5S1-4: runs per case under 0a.5 A2: memo 1 used 10 of the user's runs against 17 approved (5 + the rework's 12), the injected rework's 5 runs are
    the assistant's own spend (total 15); memo 3 likewise 10 of 17; memo 2 5 of 12."""
    replay = replays("E5-s1")
    record = service(replay)
    assert case_figures(record) == [
        ("f07a", 10, 17, "0.59", 5, 15, 15, 0, False, "", 12), ("f549", 5, 12, "0.42", 0, 5, 5, 0, False, "", 12),
        ("312a", 10, 17, "0.59", 0, 10, 10, 0, False, "", 12),
    ]
    assert [c["top_ups"] for c in record["cases"]] == [
        [{"id": AAE2, "source": "human", "amount": 12}, {"id": R963A, "source": "relayed", "amount": 6}], [], [{"id": EE21, "source": "human", "amount": 12}],
    ]
    for line in (
        f'    {F07A} "Memo for meeting 2026-10-05": 10 of 17 approved (0.59x); top-ups: +12 human rework {AAE2}, +6 your relayed rework {R963A}',
        f'    {F549} "Memo for meeting 2026-10-12": 5 of 12 approved (0.42x); top-ups: none',
        f'    {A312} "Memo for meeting 2026-10-19": 10 of 17 approved (0.59x); top-ups: +12 human rework {EE21}',
        "      your relayed reworks: 5 run(s), your own spend; total 15",
    ):
        assert line in replay.lines
    assert sum("your relayed reworks:" in x for x in replay.lines) == 1


@kit_limit
def test_e5s1_5(replays):
    """E5S1-5: three judged cases, so both alarms are evaluated: repeat `no` (R1 and C8 each failed once), cost `no` (the user's runs are far under 1.25x
    of the approved runs); R1's own reading C3, which the human link C8 does not confirm, is listed as not counted."""
    replay = replays("E5-s1")
    alarms = service(replay)["alarms"]
    assert alarms["repeat"] == {
        "state": "no", "judged": 3, "window": [F07A, F549, A312], "subjects": {"R1": 1, "C8": 1}, "fired": [], "not_counted": {"R1": ["C3"]},
    }
    assert alarms["cost"] == {"state": "no", "judged": 3, "compared": 3, "cases": [], "skipped": []}
    assert "    repeat: no (3 judged cases; counted: R1, C8); not counted: R1's reading C3 (not confirmed)" in replay.lines
    assert "    cost: no (0 of 3 cases above 1.25x)" in replay.lines


@kit_limit
def test_e5s1_6(replays):
    """E5S1-6: files not as delivered. Evidence fact: the delivered memo 1 is v2 of the team's file, the checked artifact of aae2's delivery, so nobody
    edited it; the team's current file is v3 (the relayed rework's). On the replay (no history) it is `not as delivered` against the injected delivery 963a,
    with nothing voided; memos 2 and 3 equal the current files and give no finding."""
    replay = replays("E5-s1")
    delivered, versions = evidence_versions("s1", "memo-2026-10-05.md")
    assert md5_of(delivered) == versions[2]["md5"] == "9b0c922458c56a01709a32ed01b48857" and versions[3]["md5"] != versions[2]["md5"]
    for memo in ("memo-2026-10-12.md", "memo-2026-10-19.md"):
        file, listed = evidence_versions("s1", memo)
        assert md5_of(file) == listed[max(listed)]["md5"]
    record = service(replay)
    assert record["deliveries"]["not_as_delivered"] == [{"case": F07A, "task": R963A}] and record["deliveries"]["neither"] == []
    assert record["files_error"] == ""
    by_task = {d.task.id: d for d in service_record(replay).deliveries}
    assert by_task[R963A].edited and by_task[R963A].edited_at == utc_us("2026-10-24T03:12:35.854Z")
    assert not [d for d in service_record(replay).deliveries if d.voided]
    (judged_line,) = [x for x in replay.lines if x.startswith("  judged by the user:")]
    assert judged_line.endswith(NO_HISTORY_REMARK) and "not as delivered: 1 (" in judged_line


@kit_limit
def test_e5s1_7(replays):
    """E5S1-7: moved past: none; no task of s1 was blocked."""
    replay = replays("E5-s1")
    assert replay.data["moved_past"] == [] and "Blocked tasks moved past without a verdict: none." in replay.lines
    assert {m.status for m in replay.org.received(ROOT) if m.type == "result"} == {"done"}


# ---------------------------------------------------------------------------------------------------------------------- s2

EBE2, S6C4F, F3DF = "20261024T033732488726-root-ebe2", "20261024T034308207974-root-6c4f", "20261024T034559745842-root-f3df"
BFA8, D367, E9EE = "20261024T035108035115-root-bfa8", "20261024T035511749327-root-367d", "20261024T035805054975-root-e9ee"
S2_LINK = "20261024T035002043490-root-6162"


@kit_limit
def test_e5s2_1(replays):
    """E5S2-1: s2's record and deliveries: 6 deliveries (memo 3's, e9ee, is the team's done result that the assistant never copied), 2 judged (the human
    rework 6c4f rejected, the human rework 367d accepted); memo 1 and memo 3 are without a verdict (memo 1's latest delivery f3df carries only the
    relayed reject)."""
    replay = replays("E5-s2")
    check_common(replay, "s2")
    record = service(replay)
    assert [c["id"] for c in record["cases"]] == [EBE2, BFA8, E9EE] and [c["tasks"] for c in record["cases"]] == [3, 2, 1]
    assert deliveries(service_record(replay)) == [
        (EBE2, "20261024T034151220778-lead-f023"), (S6C4F, "20261024T034511890889-lead-35b2"), (F3DF, "20261024T034825233641-lead-0cc8"),
        (BFA8, "20261024T035340880335-lead-4e2a"), (D367, "20261024T035727794165-lead-a65c"), (E9EE, "20261024T040033674800-lead-75c7"),
    ]
    assert (record["deliveries"]["total"], record["deliveries"]["judged"]) == (6, 2)
    by_task = {d.task.id: d for d in service_record(replay).deliveries}
    assert {t: [(v.verdict, v.message.id) for v in d.counted] for t, d in by_task.items() if d.judged} == {
        S6C4F: [("reject", "20261024T034910526824-root-ec12")], D367: [("accept", "20261024T035805031447-root-a539")],
    }
    assert [(v.verdict, v.tier) for v in by_task[F3DF].verdicts] == [("reject", "relayed")] and by_task[F3DF].counted == ()
    assert record["first_deliveries"] == {"accepted": 0, "rejected": 0, "no_verdict": 3, "superseded": 2, "neither": 0, "never_delivered": 0}
    assert case(record, "ebe2")["first"] == {"task": EBE2, "outcome": "none", "superseded_by": S6C4F, "superseded_source": "human"}
    assert case(record, "bfa8")["first"] == {"task": BFA8, "outcome": "none", "superseded_by": D367, "superseded_source": "human"}
    assert case(record, "e9ee")["first"] == {"task": E9EE, "outcome": "none", "superseded_by": None, "superseded_source": None}
    assert "  first deliveries: 0 accepted, 0 rejected, 3 without a verdict (2 superseded by a rework before a verdict)" in replay.lines
    deliveries_ = record["deliveries"]
    assert (deliveries_["unjudged_cases"], deliveries_["relayed_only"], deliveries_["unseen_relayed"]) == ([EBE2, E9EE], [EBE2], [])
    assert (deliveries_["not_on_a_delivery"], deliveries_["legacy_verdicts"], deliveries_["neither"]) == ([], 0, [])
    (judged_line,) = [x for x in replay.lines if x.startswith("  judged by the user:")]
    assert judged_line.startswith(f"  judged by the user: 2 of 6 deliveries; without a verdict: 2 case(s) ({EBE2}, {E9EE}): never counted as accepted (1 with only your own relayed verdict); not as delivered: 1")


@kit_limit
def test_e5s2_2(replays):
    """E5S2-2: the one escape, R1 on 6c4f: contract-gap by the user's answer (the link names C8), signed off by lead/reviewer, not its; the relayed rework
    f3df was delivered between the delivery and the verdict."""
    replay = replays("E5-s2")
    record = service(replay)
    (escape,) = record["escapes"]
    assert (escape["assertion"], escape["case"], escape["task"], escape["verdict"], escape["signer"]) == (
        "R1", EBE2, S6C4F, "20261024T034910526824-root-ec12", "lead/reviewer",
    )
    assert (escape["cause"], escape["rule"], escape["rules"], escape["detail"], escape["also"], escape["attribution"]) == (
        GAP, "answer", ["answer", "words"], [S2_LINK, "C8"], [], "not its",
    )
    assert escape["before_verdict"] == F3DF
    assert (
        f"    R1 case {EBE2}, signed off by lead/reviewer: contract-gap (the user's answer, link {S2_LINK}, names C8, which contract v1 of the task did not have); "
        f"your relayed rework {F3DF} delivered after it and before the verdict: the user may have judged that version"
    ) in replay.lines
    rechecks, rework = recorded_fails("s2")
    (verifier,) = record["verifiers"]
    assert (verifier["addr"], verifier["judged"], verifier["escapes"], verifier["pass_precision"]) == ("lead/reviewer", 2, {"counted": {}, "not_its": {GAP: 1}}, [2, 2])
    assert (verifier["rechecks"], verifier["rework_runs"]) == (rechecks, rework) == (1, 1)
    assert "    lead/reviewer: escapes 0 of 2 judged; not its: 1 contract-gap; PASS precision 2 of 2; its FAILs before delivery: 1 re-check(s), 1 author rework run(s)" in replay.lines
    assert "escapes 0 of 2 judged (+1 not its: 1 contract-gap)" in replay.root_health
    assert "escapes 0 of 2 judged" in replay.agent_health and "not its" not in replay.agent_health
    reviewer = replay.agents["lead/reviewer"]
    assert (reviewer.judged, reviewer.escapes, reviewer.not_its) == (2, 0, {GAP: 1})


@kit_limit
def test_e5s2_3(replays):
    """E5S2-3: the timeline: contract v2 answers R1 and is confirmed by the link, playbook v2 adds C8's own words, the top-ups of the two human reworks and
    of the relayed rework; no charter or model mark."""
    replay = replays("E5-s2")
    record = service(replay)
    contracts = {m["version"]: m for m in marks(record, "contract")}
    assert (contracts[1]["adds"], contracts[1]["basis"]) == (C1_C7, "first")
    assert (contracts[2]["adds"], contracts[2]["removes"], contracts[2]["basis"], contracts[2]["answers"]) == (["C8"], [], "answers", "R1")
    assert (contracts[2]["confirmed"], contracts[2]["not_confirmed"]) == ([{"id": "C8", "link": S2_LINK}], [])
    v2 = {m["version"]: m for m in marks(record, "playbook")}[2]
    assert (v2["by"], v2["basis"], v2["evidence"], v2["changed"], v2["own_words"], v2["beyond"], v2["removed"]) == ("lead", "c", ["C8", "R1", S2_LINK], 1, 1, 0, 0)
    assert mark_times(record, "contract") == [("2026-10-24T03:37", 1), ("2026-10-24T03:50", 2)]
    assert mark_times(record, "playbook") == [("2026-10-24T03:37", 1), ("2026-10-24T03:51", 2)]
    assert top_ups(record) == [
        ("2026-10-24T03:43", "6c4f", "human", 5), ("2026-10-24T03:45", "f3df", "relayed", 6), ("2026-10-24T03:55", "367d", "human", 5),
    ]
    for line in (
        "    2026-10-24 03:37 contract v1 (C1, C2, C3, C4, C5, C6, C7)",
        "    2026-10-24 03:37 playbook v1 (root): written by the client (no admission needed)",
        f"    2026-10-24 03:50 contract v2 (root): adds C8: the user's answer to R1: C8 confirmed (link {S2_LINK})",
        f"    2026-10-24 03:51 playbook v2 (lead): admitted (c) on C8, R1, {S2_LINK}: 1 changed line(s): 1 the cited criteria's own words, 0 beyond them",
        f"    2026-10-24 03:43 top-up +5 run(s) to case {EBE2}: human rework {S6C4F}",
        f"    2026-10-24 03:45 top-up +6 run(s) to case {EBE2}: your relayed rework {F3DF} (your own spend)",
        f"    2026-10-24 03:55 top-up +5 run(s) to case {BFA8}: human rework {D367}",
    ):
        assert line in replay.lines


@kit_limit
def test_e5s2_4(replays):
    """E5S2-4: runs per case: memo 1 used 14 of the user's runs against 14 approved (9 + the rework's 5; 1.00x, not over), the injected rework's 5 runs
    are the assistant's own (total 19); memo 2 10 of 12; memo 3 5 of 12."""
    replay = replays("E5-s2")
    record = service(replay)
    assert case_figures(record) == [
        ("ebe2", 14, 14, "1.00", 5, 19, 19, 0, False, "", 12), ("bfa8", 10, 12, "0.83", 0, 10, 10, 0, False, "", 12),
        ("e9ee", 5, 12, "0.42", 0, 5, 5, 0, False, "", 12),
    ]
    assert [c["top_ups"] for c in record["cases"]] == [
        [{"id": S6C4F, "source": "human", "amount": 5}, {"id": F3DF, "source": "relayed", "amount": 6}], [{"id": D367, "source": "human", "amount": 5}], [],
    ]
    for line in (
        f'    {EBE2} "Memo for the 2026-10-05 team meeting": 14 of 14 approved (1.00x); top-ups: +5 human rework {S6C4F}, +6 your relayed rework {F3DF}',
        f'    {BFA8} "Memo for the 2026-10-12 team meeting": 10 of 12 approved (0.83x); top-ups: +5 human rework {D367}',
        f'    {E9EE} "Memo for the 2026-10-19 team meeting": 5 of 12 approved (0.42x); top-ups: none',
        "      your relayed reworks: 5 run(s), your own spend; total 19",
    ):
        assert line in replay.lines
    assert sum("your relayed reworks:" in x for x in replay.lines) == 1


@kit_limit
def test_e5s2_5(replays):
    """E5S2-5: two judged cases, below the minimum: both alarms read `n/a (2 of 3 judged cases)`; R1's reading C3 is listed as not counted."""
    replay = replays("E5-s2")
    alarms = service(replay)["alarms"]
    assert alarms["repeat"] == {"state": "n/a", "judged": 2, "window": [], "subjects": {}, "fired": [], "not_counted": {"R1": ["C3"]}}
    assert alarms["cost"] == {"state": "n/a", "judged": 2, "compared": 3, "cases": [], "skipped": []}
    assert "    repeat: n/a (2 of 3 judged cases); not counted: R1's reading C3 (not confirmed)" in replay.lines
    assert "    cost: n/a (2 of 3 judged cases)" in replay.lines


@kit_limit
def test_e5s2_6(replays):
    """E5S2-6: files not as delivered. Evidence fact: the delivered memo 1 is v3 of the team's file, the checked artifact of 6c4f's delivery; the current file
    is v4 (the relayed rework f3df's). On the replay (no history) it is `not as delivered` against the injected delivery f3df; memo 2 equals the current file."""
    replay = replays("E5-s2")
    delivered, versions = evidence_versions("s2", "memo-2026-10-05.md")
    assert md5_of(delivered) == versions[3]["md5"] == "e988abb443ca3d4ee60114243c68ce77" and versions[4]["md5"] == "55c23e3980eac289550e03050bc765df"
    file, listed = evidence_versions("s2", "memo-2026-10-12.md")
    assert md5_of(file) == listed[max(listed)]["md5"]
    record = service(replay)
    assert record["deliveries"]["not_as_delivered"] == [{"case": EBE2, "task": F3DF}] and record["deliveries"]["neither"] == [] and record["files_error"] == ""
    by_task = {d.task.id: d for d in service_record(replay).deliveries}
    assert by_task[F3DF].edited and by_task[F3DF].edited_at == utc_us("2026-10-24T03:45:21.122Z")
    assert not [d for d in service_record(replay).deliveries if d.voided]
    (judged_line,) = [x for x in replay.lines if x.startswith("  judged by the user:")]
    assert judged_line.endswith(NO_HISTORY_REMARK) and "not as delivered: 1 (" in judged_line


@kit_limit
def test_e5s2_7(replays):
    """E5S2-7: moved past: none. The writer's one blocked task d3a1 is released by lead's 7713, which revises it."""
    replay = replays("E5-s2")
    assert replay.data["moved_past"] == [] and "Blocked tasks moved past without a verdict: none." in replay.lines
    task = next(m for m in replay.org.sent("lead") if m.id.endswith("-lead-d3a1"))
    blocked = [m for m in replay.org.sent("lead/writer") if m.reply_to == task.id and m.status == "blocked"]
    assert len(blocked) == 1 and moved_past(task, blocked[0], replay.org.received("lead/writer"))
    assert any(m.id.endswith("-lead-7713") and m.revises == task.id for m in replay.org.sent("lead"))
    assert [m.status for m in replay.org.sent("lead/writer") if m.type == "result"].count("blocked") == 1


# ---------------------------------------------------------------------------------------------------------------------- s3

E268, C209, DAFF = "20261024T040852855822-root-e268", "20261024T041412342994-root-c209", "20261024T041932216940-root-daff"
DD39, B57B3, E0C8 = "20261024T042728475839-root-dd39", "20261024T043106950333-root-57b3", "20261024T043420692975-root-e0c8"
GRANT, S3_LINK, A6FE = "20261024T041550995741-root-595d", "20261024T042515118836-root-d735", "20261024T042421215723-root-a6fe"


@kit_limit
def test_e5s3_1(replays):
    """E5S3-1: s3's record and deliveries: 5 deliveries (c209 is no delivery: both its results are `blocked`), 1 judged (the human rework 57b3 accepted);
    memo 1 (case e268) is not a judged case: its only human reject, R1 `a6fe`, is a verdict not on a delivery, and its latest delivery daff carries only
    the relayed reject; memo 3 is without a verdict."""
    replay = replays("E5-s3")
    check_common(replay, "s3")
    record = service(replay)
    assert [c["id"] for c in record["cases"]] == [E268, DD39, E0C8] and [c["tasks"] for c in record["cases"]] == [3, 2, 1]
    assert deliveries(service_record(replay)) == [
        (E268, "20261024T041304738049-lead-30ba"), (DAFF, "20261024T042204607622-lead-1a15"), (DD39, "20261024T043014402277-lead-9037"),
        (B57B3, "20261024T043337138383-lead-15b2"), (E0C8, "20261024T043647137647-lead-462b"),
    ]
    results = {m.reply_to: m for m in sorted(replay.org.received(ROOT), key=lambda m: m.id) if m.type == "result"}
    assert results[C209].id.endswith("-lead-d32d") and results[C209].status == "blocked"  # both results of c209 are blocked: d8cc, then d32d
    assert sum(m.reply_to == C209 and m.status == "blocked" for m in replay.org.received(ROOT)) == 2
    assert (record["deliveries"]["total"], record["deliveries"]["judged"]) == (5, 1)
    by_task = {d.task.id: d for d in service_record(replay).deliveries}
    assert {t: [(v.verdict, v.message.id) for v in d.counted] for t, d in by_task.items() if d.judged} == {B57B3: [("accept", "20261024T043420685025-root-33b9")]}
    assert [(v.verdict, v.tier) for v in by_task[DAFF].verdicts] == [("reject", "relayed")] and by_task[DAFF].counted == ()
    assert record["first_deliveries"] == {"accepted": 0, "rejected": 0, "no_verdict": 3, "superseded": 2, "neither": 0, "never_delivered": 0}
    assert case(record, "e268")["first"] == {"task": E268, "outcome": "none", "superseded_by": C209, "superseded_source": "human"}
    assert case(record, "dd39")["first"] == {"task": DD39, "outcome": "none", "superseded_by": B57B3, "superseded_source": "human"}
    deliveries_ = record["deliveries"]
    assert (deliveries_["unjudged_cases"], deliveries_["relayed_only"], deliveries_["unseen_relayed"]) == ([E268, E0C8], [E268], [])
    assert (deliveries_["not_on_a_delivery"], deliveries_["legacy_verdicts"], deliveries_["neither"]) == ([A6FE], 0, [])
    assert E268 not in record["alarms"]["repeat"]["window"] and not [d for d in service_record(replay).deliveries if d.task.id == E268 and d.judged]
    assert f"  verdicts not on a delivery (on a blocked or failed result, or before the done result): 1 ({A6FE})" in replay.lines
    (judged_line,) = [x for x in replay.lines if x.startswith("  judged by the user:")]
    assert judged_line.startswith(f"  judged by the user: 1 of 5 deliveries; without a verdict: 2 case(s) ({E268}, {E0C8}): never counted as accepted (1 with only your own relayed verdict); not as delivered: 1")


@kit_limit
def test_e5s3_2(replays):
    """E5S3-2: no escape: the user's only reject is not on a delivery (the team did not report `done`, so the re-check never ran, e5-gate 4 item 3). The
    verifier line carries no `not its` part and health no `not its` for the reviewer."""
    replay = replays("E5-s3")
    record = service(replay)
    assert record["escapes"] == [] and record["deliveries"]["not_on_a_delivery"] == [A6FE]
    assert "  escapes (the team reported done, then the user rejected it): none (judged: 1 of 5)" in replay.lines
    rechecks, rework = recorded_fails("s3")
    (verifier,) = record["verifiers"]
    assert (verifier["addr"], verifier["judged"], verifier["escapes"], verifier["pass_precision"]) == ("lead/reviewer", 1, {"counted": {}, "not_its": {}}, [1, 1])
    assert (verifier["rechecks"], verifier["rework_runs"]) == (rechecks, rework) == (1, 1)
    assert "    lead/reviewer: escapes 0 of 1 judged; PASS precision 1 of 1; its FAILs before delivery: 1 re-check(s), 1 author rework run(s)" in replay.lines
    assert "escapes 0 of 1 judged" in replay.root_health and "not its" not in replay.root_health
    reviewer = replay.agents["lead/reviewer"]
    assert (reviewer.judged, reviewer.escapes, reviewer.not_its) == (1, 0, {})
    assert record["alarms"]["repeat"]["subjects"] == {}  # a rejection not on a delivery gives no subject


@kit_limit
def test_e5s3_3(replays):
    """E5S3-3: the timeline: contract v2 answers R1 (the rejection that is no escape) and is confirmed by the link, playbook v2 adds C9's own words; the
    top-ups include root's grant after the user's yes; no charter or model mark. v1 has 8 criteria in s3."""
    replay = replays("E5-s3")
    record = service(replay)
    contracts = {m["version"]: m for m in marks(record, "contract")}
    assert (contracts[1]["adds"], contracts[1]["basis"]) == ([*C1_C7, "C8"], "first")
    assert (contracts[2]["adds"], contracts[2]["removes"], contracts[2]["basis"], contracts[2]["answers"]) == (["C9"], [], "answers", "R1")
    assert (contracts[2]["confirmed"], contracts[2]["not_confirmed"]) == ([{"id": "C9", "link": S3_LINK}], [])
    v2 = {m["version"]: m for m in marks(record, "playbook")}[2]
    assert (v2["by"], v2["basis"], v2["evidence"], v2["changed"], v2["own_words"], v2["beyond"], v2["removed"]) == ("lead", "c", ["C9", "R1", S3_LINK], 1, 1, 0, 0)
    assert mark_times(record, "contract") == [("2026-10-24T04:08", 1), ("2026-10-24T04:25", 2)]
    assert mark_times(record, "playbook") == [("2026-10-24T04:08", 1), ("2026-10-24T04:27", 2)]
    assert top_ups(record) == [
        ("2026-10-24T04:14", "c209", "human", 3), ("2026-10-24T04:15", "595d", "granted", 2), ("2026-10-24T04:19", "daff", "relayed", 6),
        ("2026-10-24T04:31", "57b3", "human", 5),
    ]
    for line in (
        "    2026-10-24 04:08 contract v1 (C1, C2, C3, C4, C5, C6, C7, C8)",
        "    2026-10-24 04:08 playbook v1 (root): written by the client (no admission needed)",
        f"    2026-10-24 04:25 contract v2 (root): adds C9: the user's answer to R1: C9 confirmed (link {S3_LINK})",
        f"    2026-10-24 04:27 playbook v2 (lead): admitted (c) on C9, R1, {S3_LINK}: 1 changed line(s): 1 the cited criteria's own words, 0 beyond them",
        f"    2026-10-24 04:14 top-up +3 run(s) to case {E268}: human rework {C209}",
        f"    2026-10-24 04:15 top-up +2 run(s) to case {E268}: your grant {GRANT}",
        f"    2026-10-24 04:19 top-up +6 run(s) to case {E268}: your relayed rework {DAFF} (your own spend)",
        f"    2026-10-24 04:31 top-up +5 run(s) to case {DD39}: human rework {B57B3}",
    ):
        assert line in replay.lines


@kit_limit
def test_e5s3_4(replays):
    """E5S3-4: runs per case: memo 1 used 13 of the user's runs against 14 approved (9 + 3, then the grant after the user's yes: 11 used + 1 held + 2),
    the injected rework's 5 runs are the assistant's own (total 18); the killed writer run is one of the 18 charged runs and `credited` is 0."""
    replay = replays("E5-s3")
    record = service(replay)
    assert case_figures(record) == [
        ("e268", 13, 14, "0.93", 5, 18, 18, 0, False, "", 12), ("dd39", 10, 12, "0.83", 0, 10, 10, 0, False, "", 12),
        ("e0c8", 5, 12, "0.42", 0, 5, 5, 0, False, "", 12),
    ]
    assert [c["top_ups"] for c in record["cases"]] == [
        [{"id": C209, "source": "human", "amount": 3}, {"id": GRANT, "source": "granted", "amount": 2}, {"id": DAFF, "source": "relayed", "amount": 6}],
        [{"id": B57B3, "source": "human", "amount": 5}], [],
    ]
    assert (replay.org.root / "lead" / "writer" / "runs" / "20261024T041458746130.log").is_file()  # the writer run killed at the end of turn 4
    for line in (
        f'    {E268} "Memo for the 5 October 2026 weekly": 13 of 14 approved (0.93x); top-ups: +3 human rework {C209}, +2 your grant {GRANT}, +6 your relayed rework {DAFF}',
        f'    {DD39} "Memo for the 12 October 2026 weekly": 10 of 12 approved (0.83x); top-ups: +5 human rework {B57B3}',
        f'    {E0C8} "Memo for the 19 October 2026 weekly": 5 of 12 approved (0.42x); top-ups: none',
        "      your relayed reworks: 5 run(s), your own spend; total 18",
    ):
        assert line in replay.lines
    assert sum("your relayed reworks:" in x for x in replay.lines) == 1


@kit_limit
def test_e5s3_5(replays):
    """E5S3-5: one judged case, below the minimum: both alarms read `n/a (1 of 3 judged cases)`, and the repeat line has no `not counted` part (the
    rejection a6fe belongs to no judged case)."""
    replay = replays("E5-s3")
    alarms = service(replay)["alarms"]
    assert alarms["repeat"] == {"state": "n/a", "judged": 1, "window": [], "subjects": {}, "fired": [], "not_counted": {}}
    assert alarms["cost"] == {"state": "n/a", "judged": 1, "compared": 3, "cases": [], "skipped": []}
    assert "    repeat: n/a (1 of 3 judged cases)" in replay.lines and "    cost: n/a (1 of 3 judged cases)" in replay.lines


@kit_limit
def test_e5s3_6(replays):
    """E5S3-6: files not as delivered. Evidence fact: the delivered memo 1 is v3 of the team's file, the writer's own rework of c209 that no reviewer
    checked: it is the checked artifact of no done delivery (e268's is v2, daff's is v4, the current file), and nobody edited it by hand. On the replay
    (no history) it is `not as delivered` against the injected delivery daff (with history too: it equals no checked version); memo 2 equals the
    current file."""
    replay = replays("E5-s3")
    delivered, versions = evidence_versions("s3", "memo-2026-10-05.md")
    assert md5_of(delivered) == versions[3]["md5"] == "0e54cf01763effec9cdffd0dc78fb8da" and versions[4]["md5"] == "8c5df76116067327ef79e4d9880240ea"
    assert md5_of(delivered) not in (versions[2]["md5"], versions[4]["md5"])
    file, listed = evidence_versions("s3", "memo-2026-10-12.md")
    assert md5_of(file) == listed[max(listed)]["md5"]
    record = service(replay)
    assert record["deliveries"]["not_as_delivered"] == [{"case": E268, "task": DAFF}] and record["deliveries"]["neither"] == [] and record["files_error"] == ""
    by_task = {d.task.id: d for d in service_record(replay).deliveries}
    assert by_task[DAFF].edited and by_task[DAFF].edited_at == utc_us("2026-10-24T04:18:31.904Z")
    assert not [d for d in service_record(replay).deliveries if d.voided]
    (judged_line,) = [x for x in replay.lines if x.startswith("  judged by the user:")]
    assert judged_line.endswith(NO_HISTORY_REMARK) and "not as delivered: 1 (" in judged_line


@kit_limit
def test_e5s3_7(replays):
    """E5S3-7: moved past: none. FINDING for the manager (OQ-4, decided: no): the writer holds 2 runs (the recorded `status`, `budget=2`) behind its blocked
    task 4a85 (memo 3), which `moved_past` does not release and after which nothing was sent to the writer, so no task is left blocked and the section
    lists no agent. Its other blocked tasks are released by the tasks that revise them, and so is root's blocked c209."""
    replay = replays("E5-s3")
    assert replay.data["moved_past"] == [] and "Blocked tasks moved past without a verdict: none." in replay.lines
    assert "budget=2" in (EV5 / "s3" / "final-services-progress-status-health.txt").read_text(encoding="utf-8").split("    writer [Writer]")[1].splitlines()[0]
    received = replay.org.received("lead/writer")
    sent = {m.id[-4:]: m for m in replay.org.sent("lead")}
    blocked = {m.reply_to[-4:]: m for m in replay.org.sent("lead/writer") if m.type == "result" and m.status == "blocked"}
    assert set(blocked) == {"0a56", "bed1", "4a85"}
    released = {short: moved_past(sent[short], blocked[short], received) for short in blocked}
    assert released == {"0a56": True, "bed1": True, "4a85": False}
    assert sent_to(replay, "lead", "lead/writer", blocked["4a85"].id) == []  # nothing sent to the writer since: not left blocked
    assert sent["df89"].revises == sent["0a56"].id and sent["711a"].revises == sent["bed1"].id
    root_task = next(m for m in replay.org.sent(ROOT) if m.id == C209)
    latest = max((m for m in replay.org.received(ROOT) if m.reply_to == C209), key=lambda m: m.id)
    assert latest.status == "blocked" and moved_past(root_task, latest, replay.org.received("lead"))  # daff revises c209


# ---------------------------------------------------------------------------------------------------------------------- all

@pytest.mark.parametrize("corpus", ["E5-s1", "E5-s2", "E5-s3"])
@kit_limit
def test_e5_all(replays, corpus):
    """E5-all: no charter or model mark and the unknown history line once; `credited` 0 in every case; no one-off record and no nested service; the JSON
    conforms to 9.4 (the schema test of tests/golden also covers the three manifests)."""
    from testkit.quality_schema import problems

    replay = replays(corpus)
    check_common(replay, corpus)
    assert replay.lines.count(f"    {NO_HISTORY}") == 1
    assert problems(replay.data) == []


# ------------------------------------------------------------------------------------------------------------------ E6 (design 19.3 "E6")
# E6S1-1..E6S3-7 and E6-all, pre-registered by the commit "docs(design): E6's expectations" (manager approval of 2026-10-25) before this block was written.
# The approved runs of memo 1 are 19, 15 and 16 (0a.5 A2); Lena's own 17 and 20 are findings (F-E6-5), not expectations; s3's accepts were recorded a turn
# before Lena saw the versions (F-E6-6) and are counted (4.3).

KIT_LIMIT_E6 = (
    "\n\n    Kit limit: the replay has no org git history, so OQ-2's given-delivery path and P3's `relayed` finding cannot run; with history the evidence shows\n"
    "    s2 relayed (no hand edit) and s1 and s3 equal to the team's current files (the md5 facts of E6S<n>-6). Both paths run on a real git history in\n"
    "    test_org_growth_0b_given.py.\n    "
)


def kit_limit_e6(test):
    """Appends the kit limit of the E6 replays to a test's docstring (the manager's condition, section 9 of the build overrides)."""
    test.__doc__ = (test.__doc__ or "") + KIT_LIMIT_E6
    return test


EV6_ROOT = REPO / "studies" / "E6-org-growth-0a3-recheck" / "evidence"
WEEKLY_MEMO = "weekly-memo"


def recorded_fails_e6(stream: str) -> tuple[int, int]:
    """The reviewer's re-checks after a FAIL and author rework runs on the recorded health line of the E6 stream."""
    lines = (EV6_ROOT / stream / "final-services-progress-status-health.txt").read_text(encoding="utf-8").splitlines()
    (line,) = [x for x in lines if x.startswith("  reviewer idle")]
    found = re.search(r"re-checks after a FAIL (\d+) \(author rework runs (\d+)\)", line)
    return int(found[1]), int(found[2])


def recorded_writer_budget(stream: str) -> int:
    """The writer's `budget=` on the recorded `status` of the E6 stream: the runs it holds."""
    text = (EV6_ROOT / stream / "final-services-progress-status-health.txt").read_text(encoding="utf-8")
    (line,) = [x for x in text.splitlines() if x.startswith("    writer [Writer]")]
    return int(re.search(r"budget=(\d+)", line)[1])


def evidence_versions_e6(stream: str, memo: str) -> tuple[Any, dict[int, dict[str, object]]]:
    index = EV6_ROOT / stream / "memos" / "versions" / "INDEX.txt"
    return EV6_ROOT / stream / "memos" / memo, {int(v["k"]): v for v in index_entries(index)[f"lead/writer/work/{memo}"]}


def check_common_e6(replay: Replay, cases: int, budget: int) -> None:
    """What every E6 stream shares (E6-all, per stream)."""
    record = service(replay)
    assert (record["service"], record["owner"], record["client"], record["client_kind"], record["unit"]) == (WEEKLY_MEMO, "lead", "root", "human", "case")
    assert (record["contract"], record["playbook"], record["budget"]) == (2, 2, budget)
    assert replay.data["one_off"] is None and replay.data["nested"] == [] and replay.data["notes"] == []
    assert replay.data["thresholds"]["source"] == "defaults" and THRESHOLDS in replay.lines
    assert f"  cases: {cases} (done {cases}, failed 0, blocked 0, open 0 (stalled 0))" in replay.lines and NO_CUT in replay.lines
    assert "One-off tasks you gave: none." in replay.lines
    assert [c["state"] for c in record["cases"]] == ["done"] * cases and [c["cut"] for c in record["cases"]] == [False] * cases
    assert [c["credited"] for c in record["cases"]] == [0] * cases and [c["stalled"] for c in record["cases"]] == [False] * cases
    assert record["history"] == {"known": False, "truncated": False, "skipped": 0} and f"    {NO_HISTORY}" in replay.lines
    assert [m for m in record["timeline"] if m["kind"] in ("charter", "model")] == []
    assert record["error"] == record["files_error"] == record["stalled_error"] == ""


def check_escape_e6(replay: Replay, stream: str, case_id: str, task: str, verdict: str, link: str, criterion: str, before: str, judged: int, rechecks: tuple[int, int]) -> None:
    """The one escape of an E6 stream: R1, contract-gap by the user's answer (the link names a criterion contract v1 lacks), not its."""
    record = service(replay)
    (escape,) = record["escapes"]
    assert (escape["assertion"], escape["case"], escape["task"], escape["verdict"], escape["signer"]) == ("R1", case_id, task, verdict, "lead/reviewer")
    assert (escape["cause"], escape["rule"], escape["rules"], escape["detail"], escape["also"], escape["attribution"], escape["class"]) == (
        GAP, "answer", ["answer", "words"], [link, criterion], [], "not its", None,
    )
    assert escape["before_verdict"] == before
    assert (
        f"    R1 case {case_id}, signed off by lead/reviewer: contract-gap (the user's answer, link {link}, names {criterion}, which contract v1 of the task did not have); "
        f"your relayed rework {before} delivered after it and before the verdict: the user may have judged that version"
    ) in replay.lines
    (_, cause) = service_record(replay).escapes[0]
    assert cause.version == 1  # the rejected task carried contract v1, which lacks the criterion
    recorded = recorded_fails_e6(stream)
    (verifier,) = record["verifiers"]
    assert (verifier["addr"], verifier["judged"], verifier["escapes"], verifier["pass_precision"], verifier["fails_error"]) == (
        "lead/reviewer", judged, {"counted": {}, "not_its": {GAP: 1}}, [judged, judged], "",
    )
    assert (verifier["rechecks"], verifier["rework_runs"]) == recorded == rechecks
    assert (
        f"    lead/reviewer: escapes 0 of {judged} judged; not its: 1 contract-gap; PASS precision {judged} of {judged}; "
        f"its FAILs before delivery: {rechecks[0]} re-check(s), {rechecks[1]} author rework run(s)"
    ) in replay.lines
    assert f"escapes 0 of {judged} judged (+1 not its: 1 contract-gap)" in replay.root_health
    assert f"escapes 0 of {judged} judged" in replay.agent_health and "not its" not in replay.agent_health
    reviewer = replay.agents["lead/reviewer"]
    assert (reviewer.judged, reviewer.escapes, reviewer.not_its) == (judged, 0, {GAP: 1})


def check_marks_e6(replay: Replay, criteria: int, new: str, link: str, minutes: dict[str, str], lines: list[str], ups: list[tuple[str, str, str, int]]) -> None:
    record = service(replay)
    contracts = {m["version"]: m for m in marks(record, "contract")}
    assert (contracts[1]["adds"], contracts[1]["basis"]) == ([f"C{k}" for k in range(1, criteria + 1)], "first")
    assert (contracts[2]["by"], contracts[2]["adds"], contracts[2]["removes"], contracts[2]["basis"], contracts[2]["answers"]) == ("root", [new], [], "answers", "R1")
    assert (contracts[2]["confirmed"], contracts[2]["not_confirmed"]) == ([{"id": new, "link": link}], [])
    playbooks = {m["version"]: m for m in marks(record, "playbook")}
    assert (playbooks[1]["by"], playbooks[1]["basis"]) == ("root", "client")
    v2 = playbooks[2]
    assert (v2["by"], v2["basis"], v2["evidence"], v2["changed"], v2["own_words"], v2["beyond"], v2["removed"]) == ("lead", "c", [new, "R1", link], 1, 1, 0, 0)
    assert mark_times(record, "contract") == [(minutes["c1"], 1), (minutes["c2"], 2)]
    assert mark_times(record, "playbook") == [(minutes["p1"], 1), (minutes["p2"], 2)]
    assert top_ups(record) == ups
    for line in lines:
        assert line in replay.lines


# ---------------------------------------------------------------------------------------------------------------------- s1

D7DCD, F06D, R3A54 = "20261024T153617209573-root-7dcd", "20261024T154227019921-root-f06d", "20261024T154651259477-root-3a54"
B5B1, CBC2, B0FE = "20261024T155319707505-root-b5b1", "20261024T160024219229-root-cbc2", "20261024T160535424081-root-b0fe"
C285B, D675 = "20261024T161027082339-root-285b", "20261024T161442312966-root-d675"
S1E6_LINK, S1E6_R1 = "20261024T155254011781-root-c18e", "20261024T155127864889-root-07a0"


@kit_limit_e6
def test_e6s1_1(replays):
    """E6S1-1: s1's record, cases and deliveries: 8 deliveries, 3 judged (the human rework f06d rejected, the human rework b5b1 and b0fe accepted); the
    injected relayed rework 3a54's delivery carries only the assistant's relayed reject and is superseded by b5b1; only memo 3's case 285b is without a
    verdict (its rework d675 was never judged); memo 1 is judged through its latest delivery b5b1."""
    replay = replays("E6-s1")
    check_common_e6(replay, 3, 16)
    record = service(replay)
    assert [c["id"] for c in record["cases"]] == [D7DCD, CBC2, C285B] and [c["tasks"] for c in record["cases"]] == [4, 2, 2]
    assert deliveries(service_record(replay)) == [
        (D7DCD, "20261024T154128433635-lead-6c73"), (F06D, "20261024T154518315044-lead-d80f"), (R3A54, "20261024T154959991979-lead-3f72"),
        (B5B1, "20261024T155753564935-lead-9260"), (CBC2, "20261024T160315038409-lead-64ff"), (B0FE, "20261024T160846733258-lead-8613"),
        (C285B, "20261024T161334148365-lead-b0f4"), (D675, "20261024T161926673282-lead-762f"),
    ]
    assert (record["deliveries"]["total"], record["deliveries"]["judged"]) == (8, 3)
    by_task = {d.task.id: d for d in service_record(replay).deliveries}
    assert {t: [(v.verdict, v.message.id) for v in d.counted] for t, d in by_task.items() if d.judged} == {
        F06D: [("reject", S1E6_R1)], B5B1: [("accept", "20261024T160024213259-root-47b9")], B0FE: [("accept", "20261024T161027073666-root-def9")],
    }
    assert [(v.verdict, v.tier) for v in by_task[R3A54].verdicts] == [("reject", "relayed")] and by_task[R3A54].counted == ()
    assert by_task[R3A54].superseded == B5B1
    assert record["first_deliveries"] == {"accepted": 0, "rejected": 0, "no_verdict": 3, "superseded": 3, "neither": 0, "never_delivered": 0}
    for short, task, by in (("7dcd", D7DCD, F06D), ("cbc2", CBC2, B0FE), ("285b", C285B, D675)):
        assert case(record, short)["first"] == {"task": task, "outcome": "none", "superseded_by": by, "superseded_source": "human"}
        assert f"    {task}: no verdict (superseded by human rework {by})" in replay.lines
    assert "  first deliveries: 0 accepted, 0 rejected, 3 without a verdict (3 superseded by a rework before a verdict)" in replay.lines
    deliveries_ = record["deliveries"]
    assert (deliveries_["unjudged_cases"], deliveries_["relayed_only"], deliveries_["unseen_relayed"]) == ([C285B], [], [])
    assert (deliveries_["not_on_a_delivery"], deliveries_["legacy_verdicts"], deliveries_["neither"]) == ([], 0, [])
    assert f"  judged by the user: 3 of 8 deliveries; without a verdict: 1 case(s) ({C285B}): never counted as accepted; not as delivered: 0" in replay.lines
    assert "## Base: the version the client judged" in next(m for m in replay.org.sent(ROOT) if m.id == B5B1).body


@kit_limit_e6
def test_e6s1_2(replays):
    """E6S1-2: the one escape, R1 on f06d (its own criterion is `none`): contract-gap by the user's answer (the link names C8, which contract v1 lacks),
    signed off by lead/reviewer, not its; the relayed rework 3a54 was delivered between the delivery and the verdict. No escape reads the base clause."""
    replay = replays("E6-s1")
    check_escape_e6(replay, "s1", D7DCD, F06D, S1E6_R1, S1E6_LINK, "C8", R3A54, 3, (1, 1))
    assert not any(m.source == "human" and m.revises and m.revises.endswith("-root-3a54") and m.id < S1E6_R1 for m in replay.org.sent(ROOT))


@kit_limit_e6
def test_e6s1_3(replays):
    """E6S1-3: the timeline: contract v2 answers R1 and is confirmed by the link (DR3-1's form), playbook v2 adds C8's own words, the top-ups of the human
    reworks and of the relayed rework; no charter or model mark."""
    replay = replays("E6-s1")
    check_marks_e6(
        replay, 7, "C8", S1E6_LINK, {"c1": "2026-10-24T15:36", "c2": "2026-10-24T15:52", "p1": "2026-10-24T15:36", "p2": "2026-10-24T15:54"},
        [
            "    2026-10-24 15:36 contract v1 (C1, C2, C3, C4, C5, C6, C7)",
            "    2026-10-24 15:36 playbook v1 (root): written by the client (no admission needed)",
            f"    2026-10-24 15:52 contract v2 (root): adds C8: the user's answer to R1: C8 confirmed (link {S1E6_LINK})",
            f"    2026-10-24 15:54 playbook v2 (lead): admitted (c) on C8, R1, {S1E6_LINK}: 1 changed line(s): 1 the cited criteria's own words, 0 beyond them",
            f"    2026-10-24 15:42 top-up +7 run(s) to case {D7DCD}: human rework {F06D}",
            f"    2026-10-24 15:46 top-up +6 run(s) to case {D7DCD}: your relayed rework {R3A54} (your own spend)",
            f"    2026-10-24 15:53 top-up +5 run(s) to case {D7DCD}: human rework {B5B1}",
            f"    2026-10-24 16:05 top-up +5 run(s) to case {CBC2}: human rework {B0FE}",
            f"    2026-10-24 16:14 top-up +5 run(s) to case {C285B}: human rework {D675}",
        ],
        [
            ("2026-10-24T15:42", "f06d", "human", 7), ("2026-10-24T15:46", "3a54", "relayed", 6), ("2026-10-24T15:53", "b5b1", "human", 5),
            ("2026-10-24T16:05", "b0fe", "human", 5), ("2026-10-24T16:14", "d675", "human", 5),
        ],
    )


@kit_limit_e6
def test_e6s1_4(replays):
    """E6S1-4: runs per case under 0a.5 A2: memo 1 used 19 of the user's runs against 19 approved (14 used before b5b1 + its 5; Lena's own approval was 17:
    a finding, F-E6-5), the injected rework's 5 runs are the assistant's own (total 24); memos 2 and 3 used 10 of 16."""
    replay = replays("E6-s1")
    record = service(replay)
    assert case_figures(record) == [
        ("7dcd", 19, 19, "1.00", 5, 24, 24, 0, False, "", 16), ("cbc2", 10, 16, "0.63", 0, 10, 10, 0, False, "", 16),
        ("285b", 10, 16, "0.63", 0, 10, 10, 0, False, "", 16),
    ]
    assert [c["top_ups"] for c in record["cases"]] == [
        [{"id": F06D, "source": "human", "amount": 7}, {"id": R3A54, "source": "relayed", "amount": 6}, {"id": B5B1, "source": "human", "amount": 5}],
        [{"id": B0FE, "source": "human", "amount": 5}], [{"id": D675, "source": "human", "amount": 5}],
    ]
    for line in (
        f'    {D7DCD} "Memo for 2026-10-05 weekly": 19 of 19 approved (1.00x); top-ups: +7 human rework {F06D}, +6 your relayed rework {R3A54}, +5 human rework {B5B1}',
        f'    {CBC2} "Memo for 2026-10-12 weekly": 10 of 16 approved (0.63x); top-ups: +5 human rework {B0FE}',
        f'    {C285B} "Memo for 2026-10-19 weekly": 10 of 16 approved (0.63x); top-ups: +5 human rework {D675}',
        "      your relayed reworks: 5 run(s), your own spend; total 24",
    ):
        assert line in replay.lines
    assert sum("your relayed reworks:" in x for x in replay.lines) == 1


@kit_limit_e6
def test_e6s1_5(replays):
    """E6S1-5: two judged cases, below the minimum: both alarms read `n/a (2 of 3 judged cases)`; R1's own reading is `none`, which is no id, so nothing is
    listed as not counted."""
    replay = replays("E6-s1")
    alarms = service(replay)["alarms"]
    assert alarms["repeat"] == {"state": "n/a", "judged": 2, "window": [], "subjects": {}, "fired": [], "not_counted": {}}
    assert alarms["cost"] == {"state": "n/a", "judged": 2, "compared": 3, "cases": [], "skipped": []}
    assert "    repeat: n/a (2 of 3 judged cases)" in replay.lines and "    cost: n/a (2 of 3 judged cases)" in replay.lines


@kit_limit_e6
def test_e6s1_6(replays):
    """E6S1-6: files not as delivered. Evidence fact: the three delivered memos equal the team's current files (v5, v3, v2 by md5); no finding on the replay."""
    replay = replays("E6-s1")
    for memo, current, md5 in (
        ("memo-2026-10-05.md", 5, "970196fc0da4bfe36f5f5c20beaadf17"), ("memo-2026-10-12.md", 3, "1b7541202526ab25ee3f8be9c6afa8ee"),
        ("memo-2026-10-19.md", 2, "8d5ae0769dfedfdc2db2bbe7edcb8bf8"),
    ):
        delivered, versions = evidence_versions_e6("s1", memo)
        assert md5_of(delivered) == versions[current]["md5"] == md5 and max(versions) == current
    record = service(replay)
    assert record["deliveries"]["not_as_delivered"] == [] and record["deliveries"]["neither"] == [] and record["files_error"] == ""
    assert not [d for d in service_record(replay).deliveries if d.voided or d.edited]
    (judged_line,) = [x for x in replay.lines if x.startswith("  judged by the user:")]
    assert judged_line.endswith("not as delivered: 0") and NO_HISTORY_REMARK not in judged_line


@kit_limit_e6
def test_e6s1_7(replays):
    """E6S1-7: moved past: none. The writer's blocked tasks dfec and a7f6 are released by lead's b986 and 340c, which revise them; every agent's recorded
    `status` budget is 0."""
    replay = replays("E6-s1")
    assert replay.data["moved_past"] == [] and "Blocked tasks moved past without a verdict: none." in replay.lines
    sent = {m.id[-4:]: m for m in replay.org.sent("lead")}
    blocked = {m.reply_to[-4:]: m for m in replay.org.sent("lead/writer") if m.type == "result" and m.status == "blocked"}
    assert set(blocked) == {"dfec", "a7f6"}
    assert all(moved_past(sent[short], blocked[short], replay.org.received("lead/writer")) for short in blocked)
    assert sent["b986"].revises == sent["dfec"].id and sent["340c"].revises == sent["a7f6"].id
    assert recorded_writer_budget("s1") == 0


# ---------------------------------------------------------------------------------------------------------------------- s2

D1D33, F99F6, E4ECB = "20261024T163213630553-root-1d33", "20261024T163832084175-root-99f6", "20261024T164233848320-root-4ecb"
R4CCC, A0AFF, F40F3 = "20261024T164609285022-root-4ccc", "20261024T165226023852-root-0aff", "20261024T165622122673-root-40f3"
S2E6_LINK, S2E6_R1, S2E6_ACCEPT = "20261024T165100357598-root-8211", "20261024T165003119224-root-7682", "20261024T165226015428-root-6271"
FF9D = "20261024T165305744776-lead-ff9d"


@kit_limit_e6
def test_e6s2_1(replays):
    """E6S2-1: s2's record and deliveries: 6 deliveries, 1 judged (the human rework 4ecb: Lena's reject, then her accept of the same version, both counted,
    still an escape); memo 1 (1d33) is without a verdict because its latest delivery is the injected relayed rework 4ccc (relayed only); memo 2 was
    delivered in turn 12 and never judged; memo 3 was never requested (2 cases)."""
    replay = replays("E6-s2")
    check_common_e6(replay, 2, 12)
    record = service(replay)
    assert [c["id"] for c in record["cases"]] == [D1D33, A0AFF] and [c["tasks"] for c in record["cases"]] == [4, 2]
    assert deliveries(service_record(replay)) == [
        (D1D33, "20261024T163735280308-lead-12d1"), (F99F6, "20261024T164118938770-lead-831f"), (E4ECB, "20261024T164505104303-lead-b322"),
        (R4CCC, "20261024T164827382688-lead-3e7e"), (A0AFF, "20261024T165521289942-lead-2e4f"), (F40F3, "20261024T165855100260-lead-5ff1"),
    ]
    assert (record["deliveries"]["total"], record["deliveries"]["judged"]) == (6, 1)
    by_task = {d.task.id: d for d in service_record(replay).deliveries}
    assert {t: [(v.verdict, v.message.id) for v in d.counted] for t, d in by_task.items() if d.judged} == {
        E4ECB: [("reject", S2E6_R1), ("accept", S2E6_ACCEPT)],
    }
    assert by_task[E4ECB].escape and by_task[E4ECB].decisive.message.id == S2E6_R1
    assert [(v.verdict, v.tier) for v in by_task[R4CCC].verdicts] == [("reject", "relayed")] and by_task[R4CCC].counted == ()
    assert record["first_deliveries"] == {"accepted": 0, "rejected": 0, "no_verdict": 2, "superseded": 2, "neither": 0, "never_delivered": 0}
    assert case(record, "1d33")["first"] == {"task": D1D33, "outcome": "none", "superseded_by": F99F6, "superseded_source": "human"}
    assert case(record, "0aff")["first"] == {"task": A0AFF, "outcome": "none", "superseded_by": F40F3, "superseded_source": "human"}
    deliveries_ = record["deliveries"]
    assert (deliveries_["unjudged_cases"], deliveries_["relayed_only"], deliveries_["unseen_relayed"]) == ([D1D33, A0AFF], [D1D33], [])
    assert (deliveries_["not_on_a_delivery"], deliveries_["legacy_verdicts"], deliveries_["neither"]) == ([], 0, [])
    (judged_line,) = [x for x in replay.lines if x.startswith("  judged by the user:")]
    assert judged_line.startswith(
        f"  judged by the user: 1 of 6 deliveries; without a verdict: 2 case(s) ({D1D33}, {A0AFF}): never counted as accepted (1 with only your own relayed verdict); not as delivered: 1",
    )


@kit_limit_e6
def test_e6s2_2(replays):
    """E6S2-2: the one escape, R1 on 4ecb (its own reading is C3): contract-gap by the user's answer (the link names C11, which contract v1 lacks), signed
    off by lead/reviewer, not its; the decisive verdict is the reject, not her later accept; the relayed rework 4ccc was delivered between the delivery and
    the verdict."""
    replay = replays("E6-s2")
    check_escape_e6(replay, "s2", D1D33, E4ECB, S2E6_R1, S2E6_LINK, "C11", R4CCC, 1, (0, 0))


@kit_limit_e6
def test_e6s2_3(replays):
    """E6S2-3: the timeline: contract v2 answers R1 and is confirmed by the link, playbook v2 adds C11's own words, the top-ups of the human reworks and of
    the relayed rework; no charter or model mark. v1 has 10 criteria in s2."""
    replay = replays("E6-s2")
    check_marks_e6(
        replay, 10, "C11", S2E6_LINK, {"c1": "2026-10-24T16:31", "c2": "2026-10-24T16:51", "p1": "2026-10-24T16:31", "p2": "2026-10-24T16:52"},
        [
            "    2026-10-24 16:31 contract v1 (C1, C2, C3, C4, C5, C6, C7, C8, C9, C10)",
            "    2026-10-24 16:31 playbook v1 (root): written by the client (no admission needed)",
            f"    2026-10-24 16:51 contract v2 (root): adds C11: the user's answer to R1: C11 confirmed (link {S2E6_LINK})",
            f"    2026-10-24 16:52 playbook v2 (lead): admitted (c) on C11, R1, {S2E6_LINK}: 1 changed line(s): 1 the cited criteria's own words, 0 beyond them",
            f"    2026-10-24 16:38 top-up +5 run(s) to case {D1D33}: human rework {F99F6}",
            f"    2026-10-24 16:42 top-up +5 run(s) to case {D1D33}: human rework {E4ECB}",
            f"    2026-10-24 16:46 top-up +6 run(s) to case {D1D33}: your relayed rework {R4CCC} (your own spend)",
            f"    2026-10-24 16:56 top-up +5 run(s) to case {A0AFF}: human rework {F40F3}",
        ],
        [
            ("2026-10-24T16:38", "99f6", "human", 5), ("2026-10-24T16:42", "4ecb", "human", 5), ("2026-10-24T16:46", "4ccc", "relayed", 6),
            ("2026-10-24T16:56", "40f3", "human", 5),
        ],
    )


@kit_limit_e6
def test_e6s2_4(replays):
    """E6S2-4: runs per case: memo 1 used 15 of the user's runs against 15 approved (10 used before 4ecb + its 5; Lena's own approval was 17: a finding),
    the injected rework's 5 runs are the assistant's own (total 20); memo 2 10 of 12."""
    replay = replays("E6-s2")
    record = service(replay)
    assert case_figures(record) == [
        ("1d33", 15, 15, "1.00", 5, 20, 20, 0, False, "", 12), ("0aff", 10, 12, "0.83", 0, 10, 10, 0, False, "", 12),
    ]
    assert [c["top_ups"] for c in record["cases"]] == [
        [{"id": F99F6, "source": "human", "amount": 5}, {"id": E4ECB, "source": "human", "amount": 5}, {"id": R4CCC, "source": "relayed", "amount": 6}],
        [{"id": F40F3, "source": "human", "amount": 5}],
    ]
    for line in (
        f'    {D1D33} "Memo for 2026-10-05 weekly": 15 of 15 approved (1.00x); top-ups: +5 human rework {F99F6}, +5 human rework {E4ECB}, +6 your relayed rework {R4CCC}',
        f'    {A0AFF} "Memo for 2026-10-12 weekly": 10 of 12 approved (0.83x); top-ups: +5 human rework {F40F3}',
        "      your relayed reworks: 5 run(s), your own spend; total 20",
    ):
        assert line in replay.lines
    assert sum("your relayed reworks:" in x for x in replay.lines) == 1


@kit_limit_e6
def test_e6s2_5(replays):
    """E6S2-5: one judged case, below the minimum: both alarms read `n/a (1 of 3 judged cases)`; R1's own reading C3, which the human link C11 does not
    confirm, is listed as not counted."""
    replay = replays("E6-s2")
    alarms = service(replay)["alarms"]
    assert alarms["repeat"] == {"state": "n/a", "judged": 1, "window": [], "subjects": {}, "fired": [], "not_counted": {"R1": ["C3"]}}
    assert alarms["cost"] == {"state": "n/a", "judged": 1, "compared": 2, "cases": [], "skipped": []}
    assert "    repeat: n/a (1 of 3 judged cases); not counted: R1's reading C3 (not confirmed)" in replay.lines
    assert "    cost: n/a (1 of 3 judged cases)" in replay.lines


@kit_limit_e6
def test_e6s2_6(replays):
    """E6S2-6: files not as delivered. Evidence fact: the delivered memo 1 is v3 of the team's file, the checked artifact of 4ecb's delivery; the current
    file is v4 (the relayed rework 4ccc's). On the replay (no history) it is `not as delivered` against the injected delivery 4ccc, with nothing voided;
    with history it would be a `relayed` finding naming 4ecb. Memo 2 equals the current file."""
    replay = replays("E6-s2")
    delivered, versions = evidence_versions_e6("s2", "memo-2026-10-05.md")
    assert md5_of(delivered) == versions[3]["md5"] == "fa17fa9470b5bafb1ebb9bf7fad3ad94" and versions[4]["md5"] == "3f7789f5261e97783cd71134a664c251"
    file, listed = evidence_versions_e6("s2", "memo-2026-10-12.md")
    assert md5_of(file) == listed[max(listed)]["md5"] == "fd27870dd5d248aa33d528a013459658"
    record = service(replay)
    assert record["deliveries"]["not_as_delivered"] == [{"case": D1D33, "task": R4CCC}] and record["deliveries"]["neither"] == [] and record["files_error"] == ""
    by_task = {d.task.id: d for d in service_record(replay).deliveries}
    assert by_task[R4CCC].edited and by_task[R4CCC].edited_at == utc_us("2026-10-24T16:45:22.100Z")
    assert not [d for d in service_record(replay).deliveries if d.voided]
    (judged_line,) = [x for x in replay.lines if x.startswith("  judged by the user:")]
    assert judged_line.endswith(NO_HISTORY_REMARK) and "not as delivered: 1 (" in judged_line


@kit_limit_e6
def test_e6s2_7(replays):
    """E6S2-7: moved past: the lead's writer holds 2 runs (the recorded `status`, `budget=2`) behind its blocked task ff9d (memo 2), which lead's next task
    f667 does not revise, so `moved_past` does not release it and the lead has sent the writer 1 task since: it is left blocked and 4.5 lists it (the
    first positive case outside E4)."""
    replay = replays("E6-s2")
    (writer,) = replay.data["moved_past"]
    assert (writer["addr"], writer["held"]) == ("lead/writer", 2)
    assert [(t["id"], t["sender"], t["left_blocked"], t["sent_since"]) for t in writer["tasks"]] == [(FF9D, "lead", True, 1)]
    assert "  lead/writer holds 2 run(s):" in replay.lines
    assert f"    task {FF9D} from lead, blocked 2026-10-24 16:53: left blocked: lead has sent lead/writer 1 task(s) since" in replay.lines
    assert recorded_writer_budget("s2") == writer["held"]
    task = next(m for m in replay.org.sent("lead") if m.id == FF9D)
    (blocked,) = [m for m in replay.org.sent("lead/writer") if m.reply_to == FF9D and m.status == "blocked"]
    assert not moved_past(task, blocked, replay.org.received("lead/writer"))
    later = sent_to(replay, "lead", "lead/writer", blocked.id)
    assert len(later) == 1 and later[0].endswith("-lead-f667") and not any(m.revises == FF9D for m in replay.org.sent("lead"))


# ---------------------------------------------------------------------------------------------------------------------- s3

D4A3E, BC02, R5D4A = "20261024T170957358424-root-4a3e", "20261024T171425096624-root-bc02", "20261024T171909790362-root-5d4a"
N9A5B, G833B, H430A = "20261024T172453163611-root-9a5b", "20261024T173000620797-root-833b", "20261024T173452118977-root-430a"
S3E6_LINK, S3E6_R1, S3E6_GRANT = "20261024T172448264286-root-1dcf", "20261024T172344353441-root-dd70", "20261024T172552093831-root-1362"
ECE1 = "20261024T173027536738-lead-ece1"


@kit_limit_e6
def test_e6s3_1(replays):
    """E6S3-1: s3's record and deliveries: 6 deliveries (4a3e's first result 11cc is `blocked`, its later result 74fa is `done` and decides), 3 judged
    (bc02 rejected, 9a5b and 833b accepted: the accepts were recorded a turn before Lena saw the versions, F-E6-6, and 4.3 counts them); 4a3e's first
    delivery reads as superseded by the relayed rework 5d4a (the first task sent after its late result); memo 3 (430a) is without a verdict."""
    replay = replays("E6-s3")
    check_common_e6(replay, 3, 16)
    record = service(replay)
    assert [c["id"] for c in record["cases"]] == [D4A3E, G833B, H430A] and [c["tasks"] for c in record["cases"]] == [4, 1, 1]
    assert deliveries(service_record(replay)) == [
        (D4A3E, "20261024T171707471531-lead-74fa"), (BC02, "20261024T171705483663-lead-009a"), (R5D4A, "20261024T172216685049-lead-406b"),
        (N9A5B, "20261024T172835140743-lead-6c63"), (G833B, "20261024T173300321852-lead-faf4"), (H430A, "20261024T173746549332-lead-5f06"),
    ]
    results = [m for m in replay.org.received(ROOT) if m.reply_to == D4A3E]
    assert sorted((m.id[-4:], m.status) for m in results) == [("11cc", "blocked"), ("74fa", "done")]
    assert (record["deliveries"]["total"], record["deliveries"]["judged"]) == (6, 3)
    by_task = {d.task.id: d for d in service_record(replay).deliveries}
    assert {t: [(v.verdict, v.message.id) for v in d.counted] for t, d in by_task.items() if d.judged} == {
        BC02: [("reject", S3E6_R1)], N9A5B: [("accept", "20261024T172919420696-root-2b9e")], G833B: [("accept", "20261024T173353829949-root-24bb")],
    }
    assert [(v.verdict, v.tier) for v in by_task[R5D4A].verdicts] == [("reject", "relayed")] and by_task[R5D4A].counted == ()
    assert record["first_deliveries"] == {"accepted": 1, "rejected": 0, "no_verdict": 2, "superseded": 1, "neither": 0, "never_delivered": 0}
    assert case(record, "4a3e")["first"] == {"task": D4A3E, "outcome": "none", "superseded_by": R5D4A, "superseded_source": "relayed"}
    assert case(record, "833b")["first"]["outcome"] == "accepted" and case(record, "430a")["first"] == {
        "task": H430A, "outcome": "none", "superseded_by": None, "superseded_source": None,
    }
    assert "  first deliveries: 1 accepted, 0 rejected, 2 without a verdict (1 superseded by a rework before a verdict)" in replay.lines
    assert f'    {G833B}: accepted: "Keep it as it is. Lee\'s swap is an action item, so the table is enough."' in replay.lines
    assert f"    {D4A3E}: no verdict (superseded by your relayed rework {R5D4A})" in replay.lines and f"    {H430A}: no verdict" in replay.lines
    deliveries_ = record["deliveries"]
    assert (deliveries_["unjudged_cases"], deliveries_["relayed_only"], deliveries_["unseen_relayed"]) == ([H430A], [], [])
    assert (deliveries_["not_on_a_delivery"], deliveries_["legacy_verdicts"], deliveries_["neither"]) == ([], 0, [])
    assert f"  judged by the user: 3 of 6 deliveries; without a verdict: 1 case(s) ({H430A}): never counted as accepted; not as delivered: 0" in replay.lines


@kit_limit_e6
def test_e6s3_2(replays):
    """E6S3-2: the one escape, R1 on bc02 (its own criterion is `none`): contract-gap by the user's answer (the link names C9, which contract v1 lacks),
    signed off by lead/reviewer (not by the reviewer's later result 915f, which answers a task sent before bc02), not its; the relayed rework 5d4a was
    delivered between the delivery and the verdict."""
    replay = replays("E6-s3")
    check_escape_e6(replay, "s3", D4A3E, BC02, S3E6_R1, S3E6_LINK, "C9", R5D4A, 3, (0, 0))


@kit_limit_e6
def test_e6s3_3(replays):
    """E6S3-3: the timeline: contract v2 answers R1 and is confirmed by the link, playbook v2 adds C9's own words; the top-ups include the human reworks
    (1 run each), the relayed rework and root's grant after the user's yes; no charter or model mark. v1 has 8 criteria in s3."""
    replay = replays("E6-s3")
    check_marks_e6(
        replay, 8, "C9", S3E6_LINK, {"c1": "2026-10-24T17:09", "c2": "2026-10-24T17:24", "p1": "2026-10-24T17:09", "p2": "2026-10-24T17:26"},
        [
            "    2026-10-24 17:09 contract v1 (C1, C2, C3, C4, C5, C6, C7, C8)",
            "    2026-10-24 17:09 playbook v1 (root): written by the client (no admission needed)",
            f"    2026-10-24 17:24 contract v2 (root): adds C9: the user's answer to R1: C9 confirmed (link {S3E6_LINK})",
            f"    2026-10-24 17:26 playbook v2 (lead): admitted (c) on C9, R1, {S3E6_LINK}: 1 changed line(s): 1 the cited criteria's own words, 0 beyond them",
            f"    2026-10-24 17:14 top-up +1 run(s) to case {D4A3E}: human rework {BC02}",
            f"    2026-10-24 17:19 top-up +6 run(s) to case {D4A3E}: your relayed rework {R5D4A} (your own spend)",
            f"    2026-10-24 17:24 top-up +1 run(s) to case {D4A3E}: human rework {N9A5B}",
            f"    2026-10-24 17:25 top-up +4 run(s) to case {D4A3E}: your grant {S3E6_GRANT}",
        ],
        [
            ("2026-10-24T17:14", "bc02", "human", 1), ("2026-10-24T17:19", "5d4a", "relayed", 6), ("2026-10-24T17:24", "9a5b", "human", 1),
            ("2026-10-24T17:25", "1362", "granted", 4),
        ],
    )


@kit_limit_e6
def test_e6s3_4(replays):
    """E6S3-4: runs per case under 0a.5 A2: memo 1 used 16 of the user's runs against 16 approved (the default's 1 run in bc02 approves nothing and the
    grant reaches 15, so the ceiling stays 16; Lena's own approval was 20: a finding), the injected rework's 5 runs are the assistant's own (total 21);
    the lead run killed with its scheduler is one of the 21 charged runs and `credited` is 0; memos 2 and 3 used 5 of 16."""
    replay = replays("E6-s3")
    record = service(replay)
    assert case_figures(record) == [
        ("4a3e", 16, 16, "1.00", 5, 21, 21, 0, False, "", 16), ("833b", 5, 16, "0.31", 0, 5, 5, 0, False, "", 16),
        ("430a", 5, 16, "0.31", 0, 5, 5, 0, False, "", 16),
    ]
    assert [c["top_ups"] for c in record["cases"]] == [
        [
            {"id": BC02, "source": "human", "amount": 1}, {"id": R5D4A, "source": "relayed", "amount": 6}, {"id": N9A5B, "source": "human", "amount": 1},
            {"id": S3E6_GRANT, "source": "granted", "amount": 4},
        ], [], [],
    ]
    assert (replay.org.root / "lead" / "runs" / "20261024T171716483127.log").is_file()  # the lead run killed with its scheduler
    for line in (
        f'    {D4A3E} "Memo for the meeting of 2026-10-05": 16 of 16 approved (1.00x); top-ups: +1 human rework {BC02}, +6 your relayed rework {R5D4A}, '
        f"+1 human rework {N9A5B}, +4 your grant {S3E6_GRANT}",
        f'    {G833B} "Memo for the meeting of 2026-10-12": 5 of 16 approved (0.31x); top-ups: none',
        f'    {H430A} "Memo for the meeting of 2026-10-19": 5 of 16 approved (0.31x); top-ups: none',
        "      your relayed reworks: 5 run(s), your own spend; total 21",
    ):
        assert line in replay.lines
    assert sum("your relayed reworks:" in x for x in replay.lines) == 1


@kit_limit_e6
def test_e6s3_5(replays):
    """E6S3-5: two judged cases, below the minimum: both alarms read `n/a (2 of 3 judged cases)`, and the repeat line has no `not counted` part (R1's own
    reading is `none`)."""
    replay = replays("E6-s3")
    alarms = service(replay)["alarms"]
    assert alarms["repeat"] == {"state": "n/a", "judged": 2, "window": [], "subjects": {}, "fired": [], "not_counted": {}}
    assert alarms["cost"] == {"state": "n/a", "judged": 2, "compared": 3, "cases": [], "skipped": []}
    assert "    repeat: n/a (2 of 3 judged cases)" in replay.lines and "    cost: n/a (2 of 3 judged cases)" in replay.lines


@kit_limit_e6
def test_e6s3_6(replays):
    """E6S3-6: files not as delivered. Evidence fact: the delivered memo 1 is v4, the current file and the checked artifact of 9a5b's delivery; memo 2 equals
    the current file; memo 3 was not copied. No finding on the replay."""
    replay = replays("E6-s3")
    delivered, versions = evidence_versions_e6("s3", "memo-2026-10-05.md")
    assert md5_of(delivered) == versions[4]["md5"] == "2a906d23378ab5101c30f04ee3868d72" and max(versions) == 4
    file, listed = evidence_versions_e6("s3", "memo-2026-10-12.md")
    assert md5_of(file) == listed[max(listed)]["md5"] == "daad1ccd09bd49dc51da829ed0c7a205"
    assert not (EV6_ROOT / "s3" / "memos" / "memo-2026-10-19.md").exists()
    record = service(replay)
    assert record["deliveries"]["not_as_delivered"] == [] and record["deliveries"]["neither"] == [] and record["files_error"] == ""
    assert not [d for d in service_record(replay).deliveries if d.voided or d.edited]
    (judged_line,) = [x for x in replay.lines if x.startswith("  judged by the user:")]
    assert judged_line.endswith("not as delivered: 0") and NO_HISTORY_REMARK not in judged_line


@kit_limit_e6
def test_e6s3_7(replays):
    """E6S3-7: moved past: the lead's writer holds 4 runs (the recorded `status`, `budget=4`) behind its blocked task ece1 (memo 2), which lead's next task
    cf2b does not revise, so it is left blocked (the lead has sent the writer 1 task since) and 4.5 lists it."""
    replay = replays("E6-s3")
    (writer,) = replay.data["moved_past"]
    assert (writer["addr"], writer["held"]) == ("lead/writer", 4)
    assert [(t["id"], t["sender"], t["left_blocked"], t["sent_since"]) for t in writer["tasks"]] == [(ECE1, "lead", True, 1)]
    assert "  lead/writer holds 4 run(s):" in replay.lines
    assert f"    task {ECE1} from lead, blocked 2026-10-24 17:31: left blocked: lead has sent lead/writer 1 task(s) since" in replay.lines
    assert recorded_writer_budget("s3") == writer["held"]
    task = next(m for m in replay.org.sent("lead") if m.id == ECE1)
    (blocked,) = [m for m in replay.org.sent("lead/writer") if m.reply_to == ECE1 and m.status == "blocked"]
    assert not moved_past(task, blocked, replay.org.received("lead/writer"))
    later = sent_to(replay, "lead", "lead/writer", blocked.id)
    assert len(later) == 1 and later[0].endswith("-lead-cf2b") and not any(m.revises == ECE1 for m in replay.org.sent("lead"))


# ---------------------------------------------------------------------------------------------------------------------- all


@pytest.mark.parametrize("corpus, cases, budget", [("E6-s1", 3, 16), ("E6-s2", 2, 12), ("E6-s3", 3, 16)])
@kit_limit_e6
def test_e6_all(replays, corpus, cases, budget):
    """E6-all: no charter or model mark and the unknown history line once; `credited` 0 in every case; no one-off record and no nested service; the JSON
    conforms to 9.4 (the schema test of tests/golden also covers the three manifests)."""
    from testkit.quality_schema import problems

    replay = replays(corpus)
    check_common_e6(replay, cases, budget)
    assert replay.lines.count(f"    {NO_HISTORY}") == 1
    assert problems(replay.data) == []
