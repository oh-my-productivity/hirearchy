import os

import pytest

from hirearchy.core import ROOT, Org, OrgError


def test_hierarchy_is_the_directory_tree(org):
    assert org.agents() == ["ceo", "ceo/eng"]
    assert org.parent("ceo/eng") == "ceo" and org.parent("ceo") == ROOT
    assert org.children("ceo") == ["ceo/eng"]
    assert (org.root / "ceo" / "eng" / "AGENT.md").is_file()


def test_task_lifecycle_and_derived_state(org):
    task = org.delegate(ROOT, "ceo", "Plan", "Make a plan", "A plan exists", budget=5)
    assert [t.id for t in org.open_tasks("ceo")] == [task.id]
    assert [t.id for t in org.outstanding(ROOT)] == [task.id]
    assert (org.root / "ceo" / "inbox" / f"{task.id}.md").is_file()
    assert (org.root / "sent" / f"{task.id}.md").is_file()

    batch = org.begin_run("ceo")
    assert [m.id for m in batch] == [task.id] and org.unread("ceo") == 0 and org.running("ceo")
    org.write("ceo", "ceo/work/plan.md", "the plan")
    result = org.report("ceo", task.id, "done", "Plan written.", ["work/plan.md"])  # own-dir shorthand works too
    org.end_run("ceo", ok=True)

    assert org.open_tasks("ceo") == [] and org.outstanding(ROOT) == []
    assert result.to == ROOT and result.reply_to == task.id
    assert "ceo/work/plan.md" in result.body
    assert org.unread(ROOT) == 1
    with pytest.raises(OrgError, match="already reported"):
        org.report("ceo", task.id, "done", "again")


def test_failed_run_redelivers(org):
    org.delegate(ROOT, "ceo", "T", "g", "a")
    org.begin_run("ceo")
    org.end_run("ceo", ok=False)
    assert org.unread("ceo") == 1 and not org.running("ceo")


def test_recover_returns_inflight_to_inbox(org):
    org.delegate(ROOT, "ceo", "T", "g", "a")
    org.begin_run("ceo")
    assert org.recover() == ["ceo"]
    assert org.unread("ceo") == 1


def test_budget_is_conserved(org):
    org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")
    org.start_run_log("ceo")  # the current run costs 1
    assert org.budget("ceo") == 4
    # 4 left, 1 reserved for processing the result -> at most 3 can go down
    with pytest.raises(OrgError, match="at most 3"):
        org.delegate("ceo", "ceo/eng", "Sub", "g", "a", budget=4)
    org.delegate("ceo", "ceo/eng", "Sub", "g", "a", budget=3)
    assert org.budget("ceo") == 1 and org.budget("ceo/eng") == 3
    assert org.budget(ROOT) is None


def test_routing_rules(org):
    org.hire(ROOT, "cfo", "Finance", "Money.")
    org.send("ceo", "cfo", "hello sibling")  # siblings ok
    org.send("ceo/eng", "ceo", "question")  # parent ok
    with pytest.raises(OrgError, match="cannot message"):
        org.send("ceo/eng", "cfo", "skip the chain")
    with pytest.raises(OrgError, match="direct reports"):
        org.delegate("cfo", "ceo/eng", "T", "g", "a")
    # the human can reach anyone, and anyone can answer the human
    note = org.send(ROOT, "ceo/eng", "how is it going?")
    org.send("ceo/eng", ROOT, "fine", reply_to=note.id)


def test_write_permissions(org):
    org.write("ceo", "ceo/MEMORY.md", "remember")
    org.write("ceo", "ceo/work/a/b.md", "deep")
    for bad, why in [
        ("MEMORY.md", "start with `ceo/`"),  # the live-run bug: own-dir-relative path landing elsewhere
        ("cfo.md", "own directory"),
        ("ceo/../cfo.md", "own directory"),
        ("ceo/inbox/x.md", "runtime"),
        ("ceo/AGENT.md", "owned by your parent"),
        ("ceo/eng/MEMORY.md", "only edit its charter"),
        ("/etc/passwd", "own directory"),
    ]:
        with pytest.raises(OrgError, match=why):
            org.write("ceo", bad, "x")
    # a parent owns its report's charter, but cannot grant tools it lacks
    org.write("ceo", "ceo/eng/AGENT.md", "---\nrole: Senior engineer\n---\nBuild better things.\n")
    assert org.charter("ceo/eng")[0]["role"] == "Senior engineer"
    with pytest.raises(OrgError, match="grant tools"):
        org.write("ceo", "ceo/eng/AGENT.md", "---\nrole: x\ntools: [shell]\n---\n")


def test_report_exposes_stale_artifacts(org):
    """Live-run lesson: a worker claimed an edit it never made. Reports now carry checkable facts."""
    org.write("ceo/eng", "ceo/eng/work/brief.md", "one two three")
    stale = org.root / "ceo/eng/work/brief.md"
    os.utime(stale, (0, 0))
    task = org.delegate(ROOT, "ceo/eng", "Trim", "Trim it", "Shorter", budget=1)
    result = org.report("ceo/eng", task.id, "done", "Trimmed to 3 words.", ["ceo/eng/work/brief.md"])
    assert "3 words" in result.body and "NOT modified since this task was assigned" in result.body
    assert "[ceo/eng/work/brief.md: 3 words" in org.read("ceo/eng/work/brief.md")


def test_hire_limits(org):
    with pytest.raises(OrgError, match="does not allow hiring"):
        org.hire("ceo/eng", "intern", "Intern", "Help.")
    with pytest.raises(OrgError, match="grant tools"):
        org.hire("ceo", "ops", "Ops", "Run things.", tools=["shell"])
    org.hire("ceo", "ops", "Ops", "Run things.")
    with pytest.raises(OrgError, match="maximum of 2"):
        org.hire("ceo", "qa", "QA", "Test things.")


def test_retire_fails_open_tasks_upward(org):
    task = org.delegate(ROOT, "ceo", "T", "g", "a", budget=5)
    org.begin_run("ceo")
    sub = org.delegate("ceo", "ceo/eng", "Sub", "g", "a", budget=2)
    org.retire("ceo", "eng", "no longer needed")
    assert not org.exists("ceo/eng")
    results = [m for m in org.received("ceo") if m.type == "result"]
    assert results[0].reply_to == sub.id and results[0].status == "failed"
    assert org.outstanding("ceo") == [] and [t.id for t in org.open_tasks("ceo")] == [task.id]


def test_hop_limit_stops_loops(org):
    cfg = (org.root / "ORG.md").read_text().replace("max_hops: 40", "max_hops: 2")
    (org.root / "ORG.md").write_text(cfg)
    org.send(ROOT, "ceo", "start")
    for sender, to in [("ceo", "ceo/eng"), ("ceo/eng", "ceo")]:
        org.begin_run(sender)
        org.send(sender, to, "ping")
        org.end_run(sender, ok=True)
    org.begin_run("ceo")
    with pytest.raises(OrgError, match="loop"):
        org.send("ceo", "ceo/eng", "ping")


def test_run_prompt_contains_everything_needed(org):
    org.write("ceo", "ceo/MEMORY.md", "I was planning X.")
    task = org.delegate(ROOT, "ceo", "Plan", "Make a plan", "A plan exists", budget=3)
    batch = org.begin_run("ceo")
    prompt = org.run_prompt("ceo", batch)
    for needle in ["you are `ceo`", "Test mission", "Run the company.", "I was planning X.", task.id, "A plan exists"]:
        assert needle in prompt


def test_find_root_from_env_and_cwd(org, monkeypatch, tmp_path):
    monkeypatch.delenv("ORG_ROOT", raising=False)
    assert Org.find_root(org.root / "ceo" / "work") == org.root
    monkeypatch.setenv("ORG_ROOT", str(org.root))
    assert Org.find_root(tmp_path) == org.root
