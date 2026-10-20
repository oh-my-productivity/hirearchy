"""Extra regression tests for the core safety/lifecycle fixes (see QA_REPORT.md and test_qa_findings.py)."""

import pytest

from orgmcp.core import ROOT, OrgError

ENG = "ceo/eng"
CHARTER = "---\nrole: Engineer v2\n---\n# New charter\nDo more."


# ------------------------------------------------------------------- QA-1 / QA-2: write guard
@pytest.mark.parametrize(
    "path",
    [
        "ceo/AGENT.md.", "ceo/Agent.MD", "ceo/MEMORY.MD", "ceo/Memory.md", "ceo/INBOX/x.md", "ceo/Sent/x.md",
        "ceo/inflight/x.md", "ceo/Runs/x.log", "ceo/.PAUSED", "ceo/.Retired/x", "ceo/ORG.md.", "ceo/Org.md",
    ],
)
def test_protected_names_are_refused_in_any_spelling(org, path):
    with pytest.raises(OrgError):
        org.write("ceo", path, "x")


@pytest.mark.parametrize("path", ["ceo/ENG/AGENT.md", "ceo/Eng/MEMORY.md", "ceo/ENG/work/x.md", "ceo/eng/agent.md", "ceo/eng/Memory.md"])
def test_case_variants_of_a_direct_report_cannot_dodge_the_charter_only_rule(org, path):
    with pytest.raises(OrgError):
        org.write("ceo", path, CHARTER)
    assert org.charter(ENG)[0]["role"] == "Engineer"
    assert org.memory(ENG) == ""


def test_report_charter_authority_check_cannot_be_dodged_by_case(org):
    greedy = "---\nrole: Engineer\ntools: [shell]\n---\n# x"  # ceo has no tools, so it cannot grant any
    for path in ("ceo/eng/AGENT.md", "ceo/ENG/AGENT.md", "ceo/eng/agent.md"):
        with pytest.raises(OrgError):
            org.write("ceo", path, greedy)
    assert "tools" not in org.charter(ENG)[0] or not org.charter(ENG)[0]["tools"]


def test_memory_cap_cannot_be_dodged_by_case(org):
    big = "word " * (int(org.config["memory_max_words"]) + 10)
    for path in ("ceo/MEMORY.md", "ceo/memory.md", "ceo/Memory.md"):
        with pytest.raises(OrgError):
            org.write("ceo", path, big)
    assert org.memory("ceo") == ""
    org.write("ceo", "ceo/MEMORY.md", "short")  # the exact spelling still works
    assert org.memory("ceo") == "short"


def test_legitimate_writes_still_work(org):
    org.write("ceo", "ceo/work/notes.md", "n")
    org.write("ceo", "ceo/work/AnyCase/Notes.md", "n")  # case is only policed against protected/existing names
    org.write("ceo", "ceo/eng/AGENT.md", CHARTER)  # a parent edits its direct report's charter
    assert org.charter(ENG)[0]["role"] == "Engineer v2"
    org.write(ROOT, "ceo/AGENT.md", CHARTER)  # root edits a direct report's charter
    org.write(ROOT, "ORG.md", org.root.joinpath("ORG.md").read_text(encoding="utf-8"))


def test_writing_a_case_twin_of_an_existing_file_is_refused(org):
    org.write("ceo", "ceo/work/Plan.md", "a")
    with pytest.raises(OrgError, match="letter case"):
        org.write("ceo", "ceo/work/plan.md", "b")
    with pytest.raises(OrgError, match="letter case"):
        org.write("ceo", "ceo/WORK/x.md", "b")
    assert (org.dir("ceo") / "work" / "Plan.md").read_text() == "a"


def test_agent_md_cannot_create_an_agent_anywhere(org):
    charter = "---\nrole: sneaky\ncan_hire: true\nmax_children: 99\n---\n# x"
    for actor, path in (
        ("ceo", "ceo/new/AGENT.md"),
        ("ceo", "ceo/work/AGENT.md"),
        ("ceo", "ceo/new/deeper/AGENT.md"),  # would be addressable as ceo/new/deeper without a parent agent
        ("ceo", "ceo/eng/sub/AGENT.md"),
        ("ceo", "ceo/NEW/AGENT.md"),
        (ROOT, "newagent/AGENT.md"),
        (ROOT, "AGENT.md"),
    ):
        with pytest.raises(OrgError):
            org.write(actor, path, charter)
    assert org.agents() == ["ceo", ENG]
    assert not (org.dir("ceo") / "new").exists() and not (org.root / "newagent").exists()


def test_hire_is_the_way_to_create_agents(org):
    assert org.hire("ceo", "ops", "Ops", "Do ops.") == "ceo/ops"
    org.write("ceo", "ceo/ops/AGENT.md", CHARTER)  # and then the parent may edit the charter
    assert org.charter("ceo/ops")[0]["role"] == "Engineer v2"


# ------------------------------------------------------------------- QA-6 / QA-9: retire
def _team(org):
    """root -> ceo(20) -> mgr(10, used 2) -> w(4, used 1); ceo also keeps eng."""
    org.hire("ceo", "mgr", "Manager", "Manage.", can_hire=True)
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
    org.hire("ceo", "mgr", "Manager", "Manage.", can_hire=True)
    org.hire("ceo/mgr", "w", "Worker", "Work.")
    for actor, name in (("ceo", "ceo/mgr/w"), ("ceo", "mgr/w"), ("ceo/eng", "ceo"), ("ceo/mgr", "ceo/eng"), ("ceo", "ceo"), ("ceo", "root")):
        with pytest.raises(OrgError):
            org.retire(actor, name, "no")
    with pytest.raises(OrgError):
        org.retire(ROOT, "root", "no")
    with pytest.raises(OrgError):
        org.retire(ROOT, "", "no")
    assert org.agents() == ["ceo", ENG, "ceo/mgr", "ceo/mgr/w"]


def test_retire_tool_reports_the_refund(org):
    import asyncio

    from orgmcp.server import build_server

    org.delegate(ROOT, "ceo", "T", "g", "a", budget=10)
    org.delegate("ceo", ENG, "t", "g", "a", budget=4)
    result = asyncio.run(build_server(org, "ceo").call_tool("retire", {"name": ENG, "reason": "done"}))
    blocks = result[0] if isinstance(result, tuple) else result
    text = "\n".join(getattr(b, "text", "") for b in blocks)
    assert "retired ceo/eng" in text and "4 unspent run(s)" in text and "returned to ceo" in text


# ------------------------------------------------------------------- QA-15: artifact scope
def _task(org):
    org.send(ROOT, "ceo", "budget", budget=5)
    return org.delegate("ceo", ENG, "t", "g", "a", budget=1)


def test_report_refuses_artifacts_outside_the_org_in_every_spelling(org, tmp_path):
    outside = tmp_path / "secret.txt"
    outside.write_text("not part of the org")
    (org.dir(ENG) / "work" / "link.txt").symlink_to(outside)  # a symlink must not smuggle it in either
    task = _task(org)
    escaping = ["../" * 12 + str(outside).lstrip("/"), str(outside), "~/", "ceo/eng/work/link.txt", "/etc/hosts", "/nonexistent/xyz", "/"]
    for art in escaping:
        with pytest.raises(OrgError, match="inside the organization"):
            org.report(ENG, task.id, "done", "ok", [art])
    assert org.outstanding("ceo")[0].id == task.id  # nothing was reported


def test_report_accepts_artifacts_inside_the_org(org):
    org.write(ENG, "ceo/eng/work/out.md", "# Title\n\n- one two\n- three\n")
    task = _task(org)
    result = org.report(ENG, task.id, "done", "ok", ["work/out.md", "ceo/eng/work", str(org.dir(ENG) / "work" / "out.md")])
    assert "ceo/eng/work/out.md (4 words" in result.body and "ceo/eng/work/ (directory)" in result.body


def test_report_missing_artifact_inside_the_org_is_still_not_found(org):
    task = _task(org)
    with pytest.raises(OrgError, match="not found"):
        org.report(ENG, task.id, "done", "ok", ["work/missing.md"])


def test_read_and_report_artifacts_share_the_markup_free_count(org):
    body = "# Blurb\n\n- alpha beta\n- gamma\n1. delta\n"
    org.write(ENG, "ceo/eng/work/blurb.md", body)
    assert len(body.split()) == 9
    assert "5 words" in org.read("ceo/eng/work/blurb.md").splitlines()[0]
    task = _task(org)
    assert "(5 words" in org.report(ENG, task.id, "done", "ok", ["ceo/eng/work/blurb.md"]).body
