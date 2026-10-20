# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.reach.orgmcp.core import ROOT

from orgmcp.kernel import RUNTIME


def ceo_with_funded_report(org, budget=20, grant=5):
    """ceo has handled its task; it has a report ``ops`` holding ``grant`` unspent runs."""
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=budget)
    org.begin_run("ceo")
    org.end_run("ceo", ok=True)
    org.hire("ceo", "ops", "Ops", "Do ops.")
    org.send("ceo", "ceo/ops", "grant", budget=grant)


def test_retire_refund_is_non_waking_and_counts_immediately(org):
    ceo_with_funded_report(org)
    before = org.budget("ceo")
    ret = org.retire_team("ceo", "ops", "done")
    assert ret.refunded == 5
    (note,) = org.messages("ceo", "inbox")
    assert note.wake is False and note.budget == 5 and note.sender == RUNTIME
    assert org.unread("ceo") == 0 and org.state("ceo") == "idle"
    assert org.budget("ceo") == before + 5  # budget is derived from files, wake or not
