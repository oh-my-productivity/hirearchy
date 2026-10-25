# mypy: ignore-errors
"""Phase 0a.5, end to end: E7's recorded streams replayed against the new code, read from the raw evidence files (design 4.7, 5.3, 6.4, 7.3).

No scheduler, no LLM, no network: ``testkit.e7_replay.materialize`` rebuilds the organization a stream had at one moment (messages, run-log names,
agents, contract), and the product's own readers read it. A missing evidence file fails the test, never skips it.

This module holds the replays of D-E7-2 A (A2 and A1): E7 s2 memo 1, where the user's rework c671 was handed the default's 1 run while nothing was left
of the 12 runs the user approved.
"""

import pytest
from testkit.e7_replay import materialize

from hirearchy.core import ROOT, Org
from hirearchy.reflection import user_approved, user_cost

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
