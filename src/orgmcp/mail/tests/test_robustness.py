# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from testkit.reach.orgmcp.core import ROOT


# ------------------------------------------------- QA-3: retire during a run
def test_end_run_is_a_noop_for_a_vanished_agent(org):
    org.retire(ROOT, "ceo", "gone")
    org.end_run("ceo", ok=False)
    org.end_run("ceo/eng", ok=True)
    assert not (org.root / "ceo").exists()
