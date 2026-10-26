# mypy: ignore-errors
"""Phase 0b.1, end to end: the defects G0 found, replayed on the files G0 kept (design 3.6, 6).

No scheduler, no LLM, no network: ``testkit.g0_replay.materialize`` rebuilds the organization a G0 stream had at one moment from ``studies/G0-noise-baseline/
evidence``, and the product's own readers read it. A missing evidence file fails the test, never skips it.

This module holds F-G0-2 (held user grants count in the user's runs and in the total). An expectation is never edited to match the product."""

import json

import pytest
from testkit.g0_replay import EVG0, materialize

from hirearchy.core import ROOT, Org

SERVICE = "weekly-meeting-memo"
M0_S1_CUT = "20261026T052934311534"  # m0-s1: root's accept ...-root-00d1, the last kept message (no run log after it)
C6C7A = "20261026T051850834033-root-6c7a"
C492D = "20261026T052441602675-root-492d"
C7EA7 = "20261026T052636885352-root-7ea7"
CECE7 = "20261026T045511617097-root-ece7"
CA7EF = "20261026T051255161913-root-a7ef"


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
