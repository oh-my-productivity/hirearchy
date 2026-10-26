# mypy: ignore-errors
"""Phase 0b, OQ-2's main path and P3's ``relayed`` finding on a REAL git history (design 4.3, 19.3 E5 "kit limit").

The exit-check replays of E5 (``test_org_growth_0b_replays.py``) have no org git history, so P3 cannot tell what the team had checked when a past
delivery was made: they never take the ``relayed`` path and the given delivery is always the latest one. Here one small synthetic organization in
``tmp_path`` makes real ``git`` commits, so both run end to end: the user's file equals the checked artifact of an earlier delivery (E5 s1's shape: the
human rework ``B`` was delivered and copied, then the assistant's relayed rework ``C`` changed the team's copy), P3 finds it ``relayed`` and not as
delivered 0, and the case's given delivery is ``B``. The same file read with no git history is ``differs`` against ``C``: the replays' reading.

No scheduler, no LLM, no network: the team's runs are the test's own calls."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from hirearchy.core import ROOT, Org

SERVICE = "weekly-memo"
MEMO = "lead/work/memo.md"
V1, V2, V3 = "Summary: v1\n", "Summary: v2\n", "Summary: v3, the assistant's relayed rework\n"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HIREARCHY_WORKSPACE_ROOTS", str(tmp_path))
    monkeypatch.setenv("GIT_AUTHOR_NAME", "t")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "t@t")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "t")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "t@t")


def commit_all(org: Org, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=org.root, check=True, capture_output=True, env=os.environ)
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", message], cwd=org.root, check=True, capture_output=True, env=os.environ)


def deliver(org: Org, task, text: str, status: str = "done", commit: bool = True):
    """The lead writes the team's file as ``text`` and reports ``task`` with ``status`` and the file listed; then the org's snapshot is committed (the
    commit holds the file as the team reported it, and the result's sent copy). With ``commit=False`` the result is reported and nothing is committed, so
    that two results can share one commit."""
    file = org.root / MEMO
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")
    org.begin_run("lead")
    org.start_run_log("lead")
    result = org.report("lead", task.id, status, "Delivered.", artifacts=[MEMO], lessons="Worked.")
    org.end_run("lead", ok=True)
    if commit:
        commit_all(org, f"lead: run ok [{task.id[-4:]}]")
    return result


@pytest.fixture
def world(tmp_path):
    """A git organization with one service; the case ``A`` -> human rework ``B`` -> relayed rework ``C``, each delivered with its own version of the
    team's file; the user's copy ``deliverables/memo.md`` is written afterwards, and the user's verdicts follow it."""
    org = Org.init(tmp_path / "org", "Mission.", {"poll_seconds": 0.05})
    org.hire(ROOT, "lead", "Lead", "Run the memos.", can_hire=True, max_children=2)
    folder = tmp_path / "deliverables"
    org.define_service(
        ROOT, "lead", SERVICE, description="A memo.", inputs=[{"name": "topic", "description": "what it is about", "required": True}],
        acceptance=["A Summary line first"], deliverable={"description": "one markdown file", "path": str(folder)}, budget=10,
        playbook="# Memo\n\n1. Write it.\n",
    )
    commit_all(org, "the org as hired")
    a = org.request(ROOT, SERVICE, {"topic": "memo"})
    deliver(org, a, V1)
    b = org.request(ROOT, SERVICE, {"topic": "memo"}, revises=a.id, source="human")
    deliver(org, b, V2)
    c = org.request(ROOT, SERVICE, {"topic": "memo"}, revises=b.id, source="relayed")
    deliver(org, c, V3)
    folder.mkdir()
    return org, folder, a, b, c


def judge(org: Org, b, c) -> None:
    """After the user's file was written: she accepts B (the version she was given); the assistant rejects C on its own reading."""
    org.feedback(ROOT, b.id, "accept", "That one is right - keep it.", source="human")
    org.feedback(ROOT, c.id, "reject", "Not requested by the user.", source="relayed")


def record_of(org: Org) -> dict:
    (record,) = json.loads(json.dumps(org.runtime.quality_report.quality_data()))["services"]
    return record


def test_a_file_equal_to_the_checked_artifact_of_an_earlier_delivery_is_relayed_and_the_user_was_given_that_delivery(world):
    """With real git: the user's copy equals what the team had checked when B was delivered (V2), and root's relayed rework C changed the team's copy
    afterwards (V3). P3's finding is `relayed`, naming B and listing C; B is the given delivery, which the user judged, so the case is not
    `without a verdict`, C is a later relayed delivery the user was not given, and nothing is not as delivered (F-E5-5, OQ-2, OQ-3)."""
    org, folder, a, b, c = world
    (folder / "memo.md").write_text(V2, encoding="utf-8")  # the copy the user was given
    judge(org, b, c)
    (found,) = org.runtime.deliverable_checks.findings(ROOT, SERVICE, settled=True)
    assert (found.name, found.kind, found.task, found.relayed) == ("memo.md", "relayed", b.id, (c.id,))
    record = record_of(org)
    deliveries = record["deliveries"]
    assert deliveries["not_as_delivered"] == [] and deliveries["neither"] == [] and record["files_error"] == ""
    assert (deliveries["total"], deliveries["judged"]) == (3, 1)
    assert deliveries["unjudged_cases"] == [] and deliveries["relayed_only"] == []  # the given delivery B has the user's accept
    assert deliveries["unseen_relayed"] == [a.id]  # C is a later relayed delivery the user was not given
    text = org.runtime.quality_report.quality_text()
    assert "without a verdict: 0 case(s)" in text and "1 later relayed delivery(ies) the user was not given (" in text
    assert "not as delivered: 0" in text and "no org history" not in text
    assert record["history"]["known"] is True


def test_the_same_file_with_no_git_history_is_not_as_delivered_against_the_latest_delivery(world):
    """The replays' reading (the kit limit): with no org git history P3 compares with the team's current file (V3), so the same V2 copy is `differs`
    against C, the given delivery is the latest one (C, with only the assistant's relayed reject), and the case reads `without a verdict (relayed only)`."""
    org, folder, a, b, c = world
    shutil.rmtree(org.root / ".git")
    (folder / "memo.md").write_text(V2, encoding="utf-8")
    judge(org, b, c)
    (found,) = org.runtime.deliverable_checks.findings(ROOT, SERVICE, settled=True)
    assert (found.name, found.kind, found.task, found.relayed) == ("memo.md", "differs", c.id, ())
    record = record_of(org)
    deliveries = record["deliveries"]
    assert deliveries["not_as_delivered"] == [{"case": a.id, "task": c.id}]
    assert deliveries["unjudged_cases"] == [a.id] and deliveries["relayed_only"] == [a.id] and deliveries["unseen_relayed"] == []
    text = org.runtime.quality_report.quality_text()
    assert "(1 with only your own relayed verdict)" in text and "(compared with the team's current files: no org history)" in text


def test_a_file_no_delivery_checked_is_not_as_delivered_even_with_git(world):
    """A copy that equals no version the team checked (a hand edit, or a file the team never had reviewed: E5 s3) is `differs`, naming the newest
    delivery that lists the file, with git too; the label is `not as delivered` and the given delivery stays the latest one."""
    org, folder, a, b, c = world
    (folder / "memo.md").write_text("Summary: edited by hand\n", encoding="utf-8")
    judge(org, b, c)
    (found,) = org.runtime.deliverable_checks.findings(ROOT, SERVICE, settled=True)
    assert (found.name, found.kind, found.task, found.relayed) == ("memo.md", "differs", c.id, ())
    deliveries = record_of(org)["deliveries"]
    assert deliveries["not_as_delivered"] == [{"case": a.id, "task": c.id}]
    assert deliveries["unjudged_cases"] == [a.id] and deliveries["unseen_relayed"] == []
    assert "no org history" not in org.runtime.quality_report.quality_text()


# ------------------------------------------------------------------------------------------------------------------------ the tie (F-G0-1)


@pytest.fixture
def tie(tmp_path):
    """E7 s2's shape (design 4.8): the head ``a`` is reported ``blocked``; the user's own rework ``b`` (revises ``a``) is delivered with V2; the lead
    then reports ``a`` ``done`` listing the same file, unchanged (the head's late result); the assistant's relayed rework ``c`` (revises ``b``) is
    delivered with V3. Every delivery is committed. The user's copy is written by each test."""
    org = Org.init(tmp_path / "org", "Mission.", {"poll_seconds": 0.05})
    org.hire(ROOT, "lead", "Lead", "Run the memos.", can_hire=True, max_children=2)
    folder = tmp_path / "deliverables"
    org.define_service(
        ROOT, "lead", SERVICE, description="A memo.", inputs=[{"name": "topic", "description": "what it is about", "required": True}],
        acceptance=["A Summary line first"], deliverable={"description": "one markdown file", "path": str(folder)}, budget=10,
        playbook="# Memo\n\n1. Write it.\n",
    )
    commit_all(org, "the org as hired")
    a = org.request(ROOT, SERVICE, {"topic": "memo"})
    deliver(org, a, V1, status="blocked")
    b = org.request(ROOT, SERVICE, {"topic": "memo"}, revises=a.id, source="human")
    deliver(org, b, V2)
    deliver(org, a, V2)  # the head's late result: the same file, unchanged
    c = org.request(ROOT, SERVICE, {"topic": "memo"}, revises=b.id, source="relayed")
    deliver(org, c, V3)
    folder.mkdir()
    return org, folder, a, b, c


def test_the_head_s_late_result_ties_with_the_rework_the_user_judged_and_her_verdict_decides(tie):
    """F-G0-1 (E7 s2's `3ca4`; design 4.1, 4.8): the head `a`'s late result and the user's rework `b` both list the file the team checked as V2, which
    equals the user's copy: a tie. Lena judged `b` (her reject, then her accept); `a` has no verdict. The tie goes to the delivery she judged: the
    finding names `b` (not the newer result `a`), and the given delivery is `b`, so the case is not without a verdict."""
    org, folder, a, b, c = tie
    (folder / "memo.md").write_text(V2, encoding="utf-8")  # the copy the user was given
    org.feedback(ROOT, b.id, "reject", "Not quite.", source="human")
    org.feedback(ROOT, b.id, "accept", "That one is right - keep it.", source="human")
    org.feedback(ROOT, c.id, "reject", "Not requested by the user.", source="relayed")
    (found,) = org.runtime.deliverable_checks.findings(ROOT, SERVICE, settled=True)
    assert (found.name, found.kind, found.task, found.relayed) == ("memo.md", "relayed", b.id, (c.id,))
    deliveries = record_of(org)["deliveries"]
    assert (deliveries["total"], deliveries["judged"]) == (3, 1)
    assert deliveries["unjudged_cases"] == [] and deliveries["relayed_only"] == [] and deliveries["unseen_relayed"] == [a.id]
    assert deliveries["not_as_delivered"] == [] and deliveries["neither"] == []


def test_the_head_s_late_result_ties_with_the_rework_and_with_no_human_verdict_the_newest_result_is_named(tie):
    """Guard: the same tie with no verdict of the user's (only the assistant's relayed reject of `c`): today's choice, the newest result among the equal
    ones, the head's late result `a`; the case is without a verdict (relayed only)."""
    org, folder, a, b, c = tie
    (folder / "memo.md").write_text(V2, encoding="utf-8")
    org.feedback(ROOT, c.id, "reject", "Not requested by the user.", source="relayed")
    (found,) = org.runtime.deliverable_checks.findings(ROOT, SERVICE, settled=True)
    assert (found.name, found.kind, found.task, found.relayed) == ("memo.md", "relayed", a.id, (c.id,))
    assert record_of(org)["deliveries"]["unjudged_cases"] == [a.id]
