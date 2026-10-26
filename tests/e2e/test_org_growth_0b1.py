# mypy: ignore-errors
"""Phase 0b.1, end to end: the defects G0 found, replayed on the files G0 kept (design 3.6, 6).

No scheduler, no LLM, no network: ``testkit.g0_replay.materialize`` rebuilds the organization a G0 stream had at one moment from ``studies/G0-noise-baseline/
evidence``, and the product's own readers read it. A missing evidence file fails the test, never skips it.

This module holds F-G0-2 (held user grants count in the user's runs and in the total), F-G0-1 (the given-delivery tie rule, m0-s2 T4's zero case
on a history built from the kept files) and F-G0-3 (``progress`` meets a result that ``inbox`` moves between the listing and the read, m1-s3 T7). An expectation is never edited to match the product."""

import json
import shutil
from datetime import datetime, timezone

import pytest
from testkit.clocks import clock_ports
from testkit.g0_replay import EVG0, materialize
from testkit.progress_world import describe_progress
from testkit.reach.hirearchy.app import wiring

from hirearchy.core import ROOT, Org
from hirearchy.mail import MessageParser
from hirearchy.mail.testing import MovingMessageParser

SERVICE = "weekly-meeting-memo"
M0_S1_CUT = "20261026T052934311534"  # m0-s1: root's accept ...-root-00d1, the last kept message (no run log after it)
C6C7A = "20261026T051850834033-root-6c7a"
C492D = "20261026T052441602675-root-492d"
C7EA7 = "20261026T052636885352-root-7ea7"
CECE7 = "20261026T045511617097-root-ece7"
CA7EF = "20261026T051255161913-root-a7ef"
M0_S2_T4_CUT = "20261026T062340000000"  # m0-s2 turn 4: G0's quality/turn-04.json was written at 06:23:40
C6F1D = "20261026T061639840350-root-6f1d"
M1_S3_T7_CUT = "20261026T085214255000"  # m1-s3 #33: root's ``inbox`` has begun the batch (the result is in ``inflight/``) and not yet ended it
M1_S3_RESULT = "20261026T084941501890-lead-3386"
M1_S3_TASK = "20261026T084600894818-root-68a8"
M0_S2_PIN = ("memo-2026-10-05.md", "memo-2026-10-05.v2.0d07ec4.md", "2026-10-26T06:23:13.513Z", 3)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))


def sent(org, task_id):
    return next(m for m in org.sent(ROOT) if m.id == task_id)


def run_logs(stream, low, high):
    """How many run logs of ``EVG0/<stream>`` (all agents) are stamped in [low, high): the evidence the cost is built from."""
    return sum(1 for log in (EVG0 / stream / "run-logs").glob("*/*.log") if low <= log.name[:21] < high)


def the_kept_files_show_the_14_runs_and_the_held_one(stream):
    """The evidence behind the 14 (design 3.6): 9 run logs in 6c7a's interval, 3 in 492d's before the grant and 1 after it; the lead's last status line
    holds ``budget=1`` and its note ``5372`` says it holds 1 run besides the one it is using."""
    assert [run_logs(stream, C6C7A[:21], C492D[:21]), run_logs(stream, C492D[:21], C7EA7[:21]), run_logs(stream, C7EA7[:21], "9")] == [9, 3, 1]
    status = (EVG0 / stream / "final-services-progress-status-health.txt").read_text(encoding="utf-8").splitlines()
    assert any(line.strip().startswith("lead ") and "budget=1" in line for line in status)
    note = (EVG0 / stream / "msgs" / "read" / "20261026T052729578653-lead-5372.md").read_text(encoding="utf-8")
    assert "I hold 1 run besides this one" in note


def test_f_g0_2_m0_s1_memo_3_holds_the_grant_run_14_of_14(tmp_path):
    """F-G0-2 (G0 m0-s1, memo 3, case 6c7a; design 3.6): the case is blocked with 14 runs approved (12, +3 the user's yes ``492d``, +2 root's grant
    ``7ea7``) and the team used 13 runs and holds 1 of the granted 2 for the user: the user's requests cost 14 of 14 approved (1.00x). G0 read 13 of 14
    (0.93x) because ``user_spend`` and ``case_spend`` left the granted run out. The other cases do not move."""
    org = Org(materialize("m0-s1", M0_S1_CUT, tmp_path))
    quality = org.runtime.quality_report
    (record,) = json.loads(json.dumps(quality.quality_data()))["services"]
    cases = {c["id"]: c for c in record["cases"]}
    keys = ("state", "runs", "relayed_runs", "user_approved", "user_cost", "spend", "ratio")
    assert {k: cases[C6C7A][k] for k in keys} == {
        "state": "blocked", "runs": 13, "relayed_runs": 0, "user_approved": 14, "user_cost": 14, "spend": 14, "ratio": "1.00",
    }
    assert cases[C6C7A]["top_ups"] == [
        {"amount": 3, "id": C492D, "source": "human"}, {"amount": 2, "id": C7EA7, "source": "granted"},
    ]
    assert "14 of 14 approved (1.00x)" in quality.quality_text()
    assert {k: cases[CECE7][k] for k in ("user_cost", "user_approved", "relayed_runs", "spend")} == {
        "user_cost": 15, "user_approved": 15, "relayed_runs": 5, "spend": 20,
    }
    assert {k: cases[CA7EF][k] for k in ("user_cost", "user_approved", "ratio")} == {"user_cost": 8, "user_approved": 12, "ratio": "0.67"}
    # the total of 492d's request: 14 is not above the 14 the user approved at that moment, so no sentence (the head leaves the grant out of M: backlog)
    assert org.runtime.service_reports.case_total(sent(org, C492D)) == "case total: 13 runs used of 15 handed down (contract: 12 per request)"
    the_kept_files_show_the_14_runs_and_the_held_one("m0-s1")


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_f_g0_1_m0_s2_t4_the_tie_without_a_verdict_is_the_latest_delivery(tmp_path):
    """F-G0-1's zero case (G0 m0-s2, T4; design 4.8): on a git history built from the kept files P3 reads v2 for both of the lead's results, ``f5df`` (the
    head 6f1d's late one) and ``e876`` (the rework 52e3's), which equal the user's copy: a tie in which neither delivery has a verdict. The rule leaves
    today's choice, the case's latest delivery, and says nothing: no finding, one case without a verdict. G0's ``turn-04.json`` read the same. A guard:
    the tie rule must not move it (green at c68ae679)."""
    org = Org(materialize("m0-s2", M0_S2_T4_CUT, tmp_path, deliverables=[M0_S2_PIN], team_files=True, history=True))
    (record,) = json.loads(json.dumps(org.runtime.quality_report.quality_data()))["services"]
    (found,) = record["cases"]
    assert found["id"] == C6F1D
    assert {k: found[k] for k in ("state", "tasks", "runs", "user_cost", "user_approved", "ratio", "spend")} == {
        "state": "done", "tasks": 2, "runs": 10, "user_cost": 10, "user_approved": 12, "ratio": "0.83", "spend": 10,
    }
    deliveries = record["deliveries"]
    assert (deliveries["total"], deliveries["judged"], deliveries["unjudged_cases"]) == (2, 0, [C6F1D])
    assert [deliveries[k] for k in ("relayed_only", "unseen_relayed", "not_as_delivered", "neither", "not_on_a_delivery")] == [[], [], [], [], []]
    assert (found["first"]["task"], found["first"]["outcome"], found["first"]["superseded_by"]) == (C6F1D, "none", None)
    assert record["history"]["known"] is True
    assert org.runtime.deliverable_checks.findings(ROOT, None, settled=True) == []
    # the evidence behind it: both sent copies are in one commit, and v2 was committed before the cut, v3 after it
    log = (EVG0 / "m0-s2" / "org-git-log.txt").read_text(encoding="utf-8")
    block = log[log.index("commit 0491b2b") :].split("\ncommit ", 1)[0]
    assert "lead/sent/20261026T062305224870-lead-e876.md" in block and "lead/sent/20261026T062307517536-lead-f5df.md" in block
    index = (EVG0 / "m0-s2" / "memos" / "versions" / "INDEX.txt").read_text(encoding="utf-8")
    assert "memo-2026-10-05.md v2 0d07ec4 2026-10-26T06:21:48Z" in index and "memo-2026-10-05.md v3 b389f15 2026-10-26T06:25:26Z" in index


def test_f_g0_3_m1_s3_t7_progress_reads_the_result_inbox_moved(tmp_path):
    """F-G0-3 (G0 m1-s3, T7; design 5.5): root's ``inbox`` moved the lead's result ``3386`` inbox -> inflight -> read and ``progress`` (1 ms later) had listed
    ``inflight/`` and then failed to open the file there: ``[Errno 2] No such file or directory``. Here the cut is the moment ``inbox`` has begun the batch (the
    result in ``inflight/``) and the move to ``read/`` is injected between the listing and the read. ``progress`` does not raise, reads the result at its new place
    once, and says what it says when the result is in ``read/`` from the start (the control): no other reader opened the file first."""
    fixed = lambda: datetime(2026, 10, 26, 8, 52, 14, 256000, tzinfo=timezone.utc)  # noqa: E731 - #33's time, 1 ms after the cut
    path = materialize("m1-s3", M1_S3_T7_CUT, tmp_path / "a", inflight={ROOT: [M1_S3_RESULT]})
    parser = MovingMessageParser({path / "inflight" / f"{M1_S3_RESULT}.md": path / "read" / f"{M1_S3_RESULT}.md"})
    assert (path / "inflight" / f"{M1_S3_RESULT}.md").is_file() and not (path / "read" / f"{M1_S3_RESULT}.md").exists()
    with wiring.overriding({**clock_ports(fixed), MessageParser: parser}):
        text = describe_progress(Org(path), M1_S3_TASK)
    assert parser.moved == [path / "inflight" / f"{M1_S3_RESULT}.md"]
    assert (path / "read" / f"{M1_S3_RESULT}.md").is_file()
    assert M1_S3_TASK in text and "done" in text
    control = materialize("m1-s3", M1_S3_T7_CUT, tmp_path / "b")
    assert (control / "read" / f"{M1_S3_RESULT}.md").is_file() and not (control / "inflight").exists()
    with wiring.overriding(clock_ports(fixed)):
        assert text == describe_progress(Org(control), M1_S3_TASK)
