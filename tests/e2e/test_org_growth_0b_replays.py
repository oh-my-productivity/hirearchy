# mypy: ignore-errors
"""Phase 0b, the exit-check replays (design 19, plan FEAT-009): the quality view and health, read by the product's own code over the files the studies
kept. No scheduler, no LLM, no network, no git: ``testkit.org_replay.materialize`` builds the organization of a corpus from its kept files (design 19.1)
and ``Org`` opens it.

One test per expectation id of design 19.3, each written from the design's text before it ran. **An expectation is never edited to match the product**:
if a replay computes another value, the FEAT stops and the manager is told (19.3, "When an expectation fails"). A listed file that is missing, or a
message that does not parse, fails the test; nothing here skips.

This module holds E (E-1..E-5), E2 (E2-1..E2-6) and A5 (A5-1..A5-3); A5-4 is the golden ``quality/a5_one_off_block.txt``
(``tests/golden/test_golden_quality.py``). E3 and E4 follow in the same module.
"""

import json
from datetime import datetime, timezone
from typing import Any, NamedTuple

import pytest
from testkit.org_replay import materialize

from hirearchy.core import ROOT, Org
from hirearchy.mail import moved_past

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
