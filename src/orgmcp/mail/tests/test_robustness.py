# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

from testkit.legacy.orgmcp.core import ROOT


# ------------------------------------------------- QA-3: retire during a run
def test_end_run_is_a_noop_for_a_vanished_agent(org):
    org.retire(ROOT, "ceo", "gone")
    org.end_run("ceo", ok=False)
    org.end_run("ceo/eng", ok=True)
    assert not (org.root / "ceo").exists()
