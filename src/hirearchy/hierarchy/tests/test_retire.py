# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import pytest
from testkit.reach.hirearchy.core import ROOT, OrgError

ENG = "ceo/eng"


# ------------------------------------------------------------------- QA-6 / QA-9: retire
def _team(org):
    """root -> ceo(20) -> mgr(10, used 2) -> w(4, used 1); ceo also keeps eng."""
    org.hire("ceo", "mgr", "Manager", "Manage.", can_hire=True, approved=True)
    org.hire("ceo/mgr", "w", "Worker", "Work.")
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=20)
    org.delegate("ceo", "ceo/mgr", "t", "g", "a", budget=10)
    org.delegate("ceo/mgr", "ceo/mgr/w", "t", "g", "a", budget=4)
    for _ in range(2):
        org.start_run_log("ceo/mgr")
    org.start_run_log("ceo/mgr/w")
    assert (org.budget("ceo"), org.budget("ceo/mgr"), org.budget("ceo/mgr/w")) == (10, 4, 3)


def test_retire_refunds_the_whole_subtrees_unspent_budget_to_the_parent(org):
    _team(org)
    result = org.retire_team("ceo", "mgr", "restructuring")
    assert (result.addr, result.refunded, result.refunded_to) == ("ceo/mgr", 7, "ceo")
    assert org.budget("ceo") == 17  # 20 granted - 3 runs actually used by the retired team
    refund = [m for m in org.messages("ceo", "inbox") if m.title.startswith("Budget returned")]
    assert len(refund) == 1 and refund[0].budget == 7 and "ceo/mgr" in refund[0].body
    assert not org.exists("ceo/mgr") and not org.exists("ceo/mgr/w")


def test_retire_refund_is_never_negative_and_skipped_when_parent_is_root(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    org.delegate("ceo", ENG, "t", "g", "a", budget=2)
    for _ in range(5):  # overspent
        org.start_run_log(ENG)
    assert org.budget(ENG) == -3
    assert org.retire_team("ceo", "eng", "x").refunded == 0
    assert org.budget("ceo") == 8 and not [m for m in org.messages("ceo", "inbox") if m.sender == "runtime"]

    org.send(ROOT, "ceo", "more", budget=3)
    assert org.retire_team(ROOT, "ceo", "x") == ("ceo", 0, None)  # root has no limit: nothing to credit
    assert not [m for m in org.messages(ROOT, "inbox") if m.sender == "runtime"]


def test_retire_counts_pending_grants_that_the_retiree_has_not_read_yet(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    org.send("ceo", ENG, "extra", budget=3)  # still in eng's inbox
    assert org.retire_team("ceo", "eng", "x").refunded == 3 and org.budget("ceo") == 10


def test_retire_accepts_short_name_and_full_address(org):
    org.hire("ceo", "ops", "Ops", "Do ops.")
    assert org.retire("ceo", "ops", "short") == "ceo/ops"
    assert org.retire("ceo", ENG, "full") == ENG
    org.hire("ceo", "eng", "Engineer", "Build things.")
    assert org.retire(ROOT, "ceo/eng", "root, full address") == ENG


def test_retire_is_still_limited_to_direct_reports(org):
    org.hire("ceo", "mgr", "Manager", "Manage.", can_hire=True, approved=True)
    org.hire("ceo/mgr", "w", "Worker", "Work.")
    for actor, name in (("ceo", "ceo/mgr/w"), ("ceo", "mgr/w"), ("ceo/eng", "ceo"), ("ceo/mgr", "ceo/eng"), ("ceo", "ceo"), ("ceo", "root")):
        with pytest.raises(OrgError):
            org.retire(actor, name, "no")
    with pytest.raises(OrgError):
        org.retire(ROOT, "root", "no")
    with pytest.raises(OrgError):
        org.retire(ROOT, "", "no")
    assert org.agents() == ["ceo", ENG, "ceo/mgr", "ceo/mgr/w"]


# ------------------------------------------------------------------- Phase 2: the record of a retire (design 4.5)
def _record(org, tree_prefix):
    from hirearchy.kernel import split_frontmatter

    (tree,) = sorted((org.root / ".retired").glob(f"{tree_prefix}-*"))
    return split_frontmatter((tree / "RETIRED.md").read_text(encoding="utf-8"))[0]


def test_a_retire_records_retired_by_reason_and_approved_in(org):
    org.runtime.retirement.retire_team(ROOT, "ceo/eng", "no longer needed", approved_in="change 0123456789ab")
    record = _record(org, "ceo.eng")
    assert list(record) == ["retired", "by", "reason", "approved_in"]
    assert (record["by"], record["reason"], record["approved_in"]) == ("root", "no longer needed", "change 0123456789ab")
    assert isinstance(record["retired"], str) and record["retired"].count(":") >= 2 and "T" in record["retired"]


def test_approved_in_is_written_only_when_given(org):
    org.retire("ceo", "eng", "done")  # the facade keeps its signature: no approval
    record = _record(org, "ceo.eng")
    assert list(record) == ["retired", "by", "reason"] and record["by"] == "ceo" and record["reason"] == "done"


def test_a_record_that_cannot_be_written_leaves_the_tree_retired_and_the_event_says_record_failed(org):
    import json

    from testkit.reach.hirearchy.app import wiring

    from hirearchy.agents import AgentRegistry

    class RecordLost(AgentRegistry):
        """The move happens; the write of RETIRED.md fails."""

        def __init__(self, inner):
            self.inner = inner

        def create(self, addr, meta, charter_text):
            self.inner.create(addr, meta, charter_text)

        def rewrite_charter(self, addr, text):
            self.inner.rewrite_charter(addr, text)

        def archive(self, addr, stamp, record=None):
            self.inner.archive(addr, stamp)
            raise OSError("disk full")

    org.runtime = wiring.open_runtime(org.root, {AgentRegistry: RecordLost(org.runtime.agent_registry)})
    result = org.runtime.retirement.retire_team(ROOT, "ceo/eng", "no longer needed", approved_in="change 0123456789ab")
    assert result.addr == "ceo/eng" and not org.exists("ceo/eng")
    (tree,) = sorted((org.root / ".retired").glob("ceo.eng-*"))
    assert not (tree / "RETIRED.md").exists()
    org.runtime.resources.reset()
    events = [json.loads(line) for f in (org.root / ".runtime" / "events").glob("*/*.jsonl") for line in f.read_text(encoding="utf-8").splitlines()]
    (retired,) = [e for e in events if e["kind"] == "agent.retire"]
    assert retired["agent"] == "ceo/eng" and retired["record"] == "failed"
