# mypy: ignore-errors
"""Phase 0a.3, end to end: E5's recorded streams replayed against the new code, read from the raw evidence files (design 4.7).

No scheduler, no LLM, no network: ``testkit.e5_replay.materialize`` rebuilds the organization a stream had at one moment (messages, run-log names,
agents, contract), and the product's own ``case_total`` and ``user_*`` functions read it. A missing evidence file fails the test, never skips it.

This module holds the replays of proposal A (D-E5-1): the case total of E5 s1 at T6 and of E5 s2 at T5; and those of D-E5-5 (F-E5-7): the tier of the
rework delegations of E5 s3 memo 2.
"""

import pytest
from testkit.e5_replay import materialize

from hirearchy.core import ROOT, Org
from hirearchy.reflection import user_approved, user_spend

SERVICE = "weekly-meeting-memo"
OWN = "report them to the user as yours, and never ask the user to fund them."


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))


def replay(tmp_path, stream, cut, task_id):
    """The organization of ``stream`` at ``cut``, the task ``task_id`` root sent in it and the case that holds it."""
    org = Org(materialize(stream, cut, tmp_path / "org"))
    task = next(m for m in org.sent(ROOT) if m.id == task_id)
    (case,) = [c for c in org.runtime.case_history.cases("lead", SERVICE) if task.id in {t.id for t in c.tasks}]
    return org, task, case


def test_e5_s1_t6_the_case_reads_ten_user_runs_and_five_relayed_without_exceeds(tmp_path):
    """D-E5-1, the decision's replay of s1 T6 (call #28): 15 runs, 10 by the user's requests and 5 by root's relayed rework 963a; the user approved 17
    (12, then 12 more with 7 returned and 5 used). 0a.2 printed "exceeds the per-request budget of 12: tell the user" here, and the assistant asked
    the user to fund runs of its own rework."""
    relayed = "20261024T031317713451-root-963a"
    org, task, case = replay(tmp_path, "s1", "20261024T031704521000", relayed)
    total = org.runtime.service_reports.case_total(task)
    assert total == (
        f"case total: 15 runs used: 10 by the user's requests, 5 by your relayed rework {relayed}; 30 handed down (contract: 12 per request). "
        f"The runs of your relayed rework are your own spend, not the user's: {OWN}"
    )
    assert "exceeds" not in total and "tell the user" not in total
    assert user_spend(case) == 10 and case.relayed_runs == 5 and user_approved(case, 12) == 17


@pytest.mark.parametrize(
    "cut, runs",
    [("20261024T034308207974", 9), ("20261024T034512547000", 14)],
    ids=["#21: the user's rework just sent", "#23: the rework delivered"],
)
def test_e5_s2_t5_the_rework_lena_funded_does_not_exceed(tmp_path, cut, runs):
    """D-E5-1, s2 T5: Lena approved "5 more" runs for the rework 6c4f (12 + 5 = 17 handed down, 14 committed). 0a.2 said "exceeds" at both moments;
    the user's requests cost 9 + 5 = 14 at #21 and 14 at #23, within the 14 she approved."""
    org, task, case = replay(tmp_path, "s2", cut, "20261024T034308207974-root-6c4f")
    assert org.runtime.service_reports.case_total(task) == f"case total: {runs} runs used of 17 handed down (contract: 12 per request)"
    assert user_spend(case) == 14 and user_approved(case, 12) == 14 and case.relayed_runs == 0


def test_e5_s3_the_rework_delegation_of_memo_2_inherits_the_human_tier(tmp_path):
    """F-E5-7, D-E5-5: the writer delegation 0a56 of memo 2 has no trace (the lead also held memo 1's blocked task). The lead's run 04:31:38 sent the
    rework df89 that revises it; the batch of that run was root's human rework 57b3 (trace dd39). 0a.2 gave df89 no ``source``; the tier is now looked
    up through the run's batch."""
    org = Org(materialize("s3", "20261024T043138264197", tmp_path / "org", inflight={"lead": ["20261024T043106950333-root-57b3"]}))
    assert org.runtime.rework_context.fields_for("lead", "20261024T042806761805-lead-0a56") == {"source": "human"}


def test_e5_s3_the_re_check_delegation_of_memo_2_inherits_the_human_tier(tmp_path):
    """F-E5-7, D-E5-5: the reviewer delegation 16f9 of memo 2 has no trace either. The run 04:32:31 that sent the rework caa9 had the writer's result
    d2ef as its batch (trace dd39): a result, not a task, and the stamper's batch rule takes its trace all the same."""
    org = Org(materialize("s3", "20261024T043231631185", tmp_path / "org", inflight={"lead": ["20261024T043159758365-lead.writer-d2ef"]}))
    assert org.runtime.rework_context.fields_for("lead", "20261024T042855998356-lead-16f9") == {"source": "human"}
