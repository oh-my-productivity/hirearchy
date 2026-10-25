# mypy: ignore-errors
"""Phase 0a.5, end to end: E7's recorded streams replayed against the new code, read from the raw evidence files (design 4.7, 5.3, 6.4, 7.3).

No scheduler, no LLM, no network: ``testkit.e7_replay.materialize`` rebuilds the organization a stream had at one moment (messages, run-log names,
agents, contract), and the product's own readers read it. A missing evidence file fails the test, never skips it.

This module holds the replays of D-E7-2 A (A2 and A1): E7 s2 memo 1, where the user's rework c671 was handed the default's 1 run while nothing was left
of the 12 runs the user approved; those of D-E7-2 C (E7 s1 6920: only the user's verdict settles the questions for the client) and F-E7-7 (E7 s3 d9bc: a blocked task
its assigner moved past is no longer open work).
"""

import pytest
from testkit.e7_replay import materialize

from hirearchy.core import ROOT, Org
from hirearchy.kernel import latest_results
from hirearchy.mail import still_open
from hirearchy.progress import progress
from hirearchy.reflection import questions_open, user_approved, user_cost

SERVICE = "weekly-meeting-memo"
THREE_CA4 = "20261025T074451197103-root-3ca4"
C671 = "20261025T075038845671-root-c671"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))


def the_case(org, task_id):
    """The case of ``lead``'s service that holds the task ``task_id``."""
    (case,) = [c for c in org.runtime.case_history.cases("lead", SERVICE) if task_id in {t.id for t in c.tasks}]
    return case


def sent(org, task_id):
    return next(m for m in org.sent(ROOT) if m.id == task_id)


def test_a2_e7_s2_20_c671_is_the_default_with_nothing_left_and_the_approval_stays_12(tmp_path):
    """A2 (E7 s2 #20, D-E7-2, design 4.7): 3ca4 had 12 runs, 9 used and 3 held, so nothing was left when c671 (the user's rework, no ``budget``) was
    handed the default's 1 run. That run is no approval of the user's: the case's approval stays 12 (it read 13), and its cost is 13."""
    org = Org(materialize("s2", "20261025T075038845671", tmp_path / "org"))
    case = the_case(org, C671)
    assert case.unapproved_reworks == (C671,)
    assert user_approved(case, 12) == 12
    assert org.runtime.service_reports.case_total(sent(org, C671)) == (
        "case total: 9 runs used of 13 handed down (contract: 12 per request). This case now exceeds the per-request budget of 12: tell the user."
    )
    before = Org(materialize("s2", "20261025T075038845670", tmp_path / "before"))
    assert before.runtime.case_allowance.left("lead", SERVICE, THREE_CA4) == 0  # nothing was left: the default handed 1


def test_a2_e7_s2_the_grant_68df_approves_13(tmp_path):
    """A2 (E7 s2, D-E7-2): Lena said yes to one more run and root granted it (68df, 1 run). The approval is 13, as she approved it (it read 14), and
    the case costs 13: no overspend sentence."""
    org = Org(materialize("s2", "20261025T075138446837", tmp_path / "org"))
    case = the_case(org, C671)
    assert user_approved(case, 12) == 13 and user_cost(case) == 13
    total = org.runtime.service_reports.case_total(sent(org, C671))
    assert "exceeds" not in total and "more than" not in total


def test_a2_e7_s2_24_the_case_total_says_14_is_more_than_the_13_approved(tmp_path):
    """A2 (E7 s2 #24, D-E7-2): c671 is answered (64cb) and the team used 14 runs for the user's requests: 1 more than the 13 the user approved. It
    printed no sentence at 18a4531 (the approval read 14)."""
    org = Org(materialize("s2", "20261025T075347939000", tmp_path / "org"))
    case = the_case(org, C671)
    assert user_approved(case, 12) == case.user_ceiling == 13 and user_cost(case) == 14
    assert org.runtime.service_reports.case_total(sent(org, C671)) == (
        "case total: 14 runs used of 13 handed down (contract: 12 per request). The user's requests now cost 14 runs, more than the 13 the user "
        "approved for this case (contract: 12 per request, plus 1 approved beyond it): tell the user."
    )


def test_a1_e7_s2_20_the_top_up_asks_for_2_and_names_the_default_run(tmp_path):
    """A1 (E7 s2 #20, D-E7-2, design 4.4 and 4.7, DR-0a5-7): the top-up asked for 1 run at 18a4531 and Lena's yes to 1 was an approval of 13. Now the
    default's own run is in the ask and the grant: 5 - 1 - 0 - 3 held + 1 = 2, and the reply says that nothing else was left of the approval."""
    org = Org(materialize("s2", "20261025T075038845671", tmp_path / "org"))
    assert org.runtime.service_steps.rework_step(sent(org, C671)) == (
        "This rework has 1 run(s), and a rework of this team needs about 5 (1, plus 2 for each agent below lead). The team still holds 3 of the user's "
        f"runs for {THREE_CA4}; the rework can use them. Nothing else was left of the runs the user approved for this case when this rework was sent: "
        "its own run is beyond them, and the ask includes it. Ask the user now for 2 more run(s), with that number; on yes, grant 2: "
        'send(to="lead", budget=2, body=<why>) (CLI: hirearchy send lead "<why>" --budget 2).'
    )


S1_6920 = "20261025T071152630842-root-6920"


def s1_6920(tmp_path, cut):
    """E7 s1 at ``cut``: the questions still open on 6920's result c3d0, and 6920's own line (the first line of its progress)."""
    org = Org(materialize("s1", cut, tmp_path / "org"))
    task = sent(org, S1_6920)
    result = next(m for box in ("read", "inbox") for m in org.messages(ROOT, box) if m.id.endswith("-lead-c3d0"))
    case = the_case(org, S1_6920)
    return questions_open(task, result, case, org.sent(ROOT)), progress(org, task_id=S1_6920).splitlines()[0]


def test_c_e7_s1_6920_a_relayed_reject_leaves_the_4_questions_open_and_the_path_withheld(tmp_path):
    """C (E7 s1 after #39, D-E7-2, design 5.3): the assistant's own reject 1b8f of 6920 (relayed) settled the 4 questions of c3d0 at 18a4531 and the
    path was shown. Now they stay open: the path is withheld and the flag is there. A relayed verdict still counts as feedback (no ``no feedback yet``)."""
    open_questions, line = s1_6920(tmp_path, "20261025T071711763028")
    assert open_questions == 4
    assert "artifacts withheld (ask first). 4 questions for the client: ask the user before you copy or deliver." in line
    assert "no feedback yet" not in line


def test_c_e7_s1_6920_the_human_accept_settles_them(tmp_path):
    """C (E7 s1 after #47, D-E7-2, design 5.3): the user's own accept 9496 (of 066f, the rework of the chain) settles the questions: the path returns."""
    open_questions, line = s1_6920(tmp_path, "20261025T072107513137")
    assert open_questions == 0
    assert "artifacts: lead/writer/work/memo-2026-10-05.md, lead/reviewer/work/review-memo-2026-10-05.md" in line
    assert "questions for the client" not in line


S3_DD46 = "20261025T084326230467-root-dd46"
S3_A443 = "20261025T084326297193-root-a443"
S3_D9BC = "20261025T083808500876-root-d9bc"
S3_9838 = "20261025T084354396141-lead-9838"
S3_E4C7 = "20261025T084422364417-lead.writer-e4c7"


def test_f7_e7_s3_d9bc_accepted_after_its_block_is_no_longer_open_work_of_the_lead(tmp_path):
    """F7 (E7 s3, D-E7-2 F-E7-7, design 6.4): Lena accepted d9bc (dd46) after the lead reported it blocked (da3c). The budget already read it as moved
    past; the stamper did not, so the lead held two open traces and its delegations got ``ambiguous``. Now only a443 is open and the record is untouched:
    d9bc's latest result is still the lead's ``blocked`` one and memo 1's case stays ``blocked``."""
    org = Org(materialize("s3", "20261025T084354396140", tmp_path / "org", inflight={"lead": [S3_DD46, S3_A443]}))
    runtime = org.runtime
    assert runtime.trace_lookup.open_task_traces("lead") == [S3_A443]
    assert runtime.trace_lookup.context_trace("lead") == (S3_A443, "open-task", [])
    received = org.messages("lead", "inbox", "inflight", "read")
    d9bc = next(m for m in received if m.id == S3_D9BC)
    latest = latest_results(org.sent("lead"))[S3_D9BC]
    assert latest.id.endswith("-lead-da3c") and latest.status == "blocked"  # the record stays the lead's
    assert not still_open(d9bc, latest, received)
    assert runtime.rework_context.work_tier("lead") is None  # a443 carries no tier: the gate's "they lost no tier"
    assert the_case(org, S3_D9BC).state == "blocked"
    line = progress(org, task_id=S3_D9BC).splitlines()[0]
    assert line.startswith('"Memo for 2026-10-05: add Summary line (C9)" [service weekly-meeting-memo v1]: blocked: Questions for the client:.')


def test_f7_e7_s3_9838_the_upstream_hint_names_a443_once_d9bc_was_moved_past(tmp_path):
    """F7 (E7 s3, D-E7-2 F-E7-7, design 6.4): 9838 was sent after dd46 and a443. d9bc, blocked and moved past, is no candidate, so the one task the
    delegation serves is a443 (it was None, two candidates) and the writer's result e4c7 is rendered with the hint."""
    org = Org(materialize("s3", "20261025T084422364417", tmp_path / "org"))
    runtime = org.runtime
    delegated = next(m for m in org.sent("lead") if m.id == S3_9838)
    found = runtime.upstream_tasks.upstream("lead", delegated)
    assert found is not None and found[0].id == S3_A443 and found[1] is None
    e4c7 = next(m for box in ("inbox", "inflight", "read") for m in org.messages("lead", box) if m.id == S3_E4C7)
    assert (
        "[It was the only task assigned to you before you delegated this, so it probably serves your open task "
        f'{S3_A443} "Memo for 2026-10-12 meeting": the result must also satisfy that task\'s criteria (shown in full in this prompt).]'
    ) in runtime.context_renderer.render("lead", e4c7)
