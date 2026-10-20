# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import pytest
from testkit.blueprint_world import World, bpm

from orgmcp.kiro import ConfinementPolicy


def documents_bp(tmp_path, reviewer: dict | None = None, writer: dict | None = None):
    (tmp_path / "notes").mkdir(exist_ok=True)
    return {
        "mission": "Turn the meeting notes into a memo.",
        "needs": {"scope": "weekly memo", "kind": "writing", "inputs": [str(tmp_path / "notes")],
                  "deliverable": {"description": "memo", "format": "markdown", "max_words": 300},
                  "quality_bar": "every action item has an owner", "sources": "the notes only, no web",
                  "budget_runs": 30, "model_policy": "one model for all", "review": True, "approval": "plan",
                  "progress": "on request"},
        "agents": [{"name": "lead", "template": "manager", "children": [
            {"name": "writer", "template": "writer", "tools": ["read"], **(writer or {})},
            {"name": "reviewer", "template": "reviewer", "tools": ["read"], **(reviewer or {})}]}],
        "task": {"title": "Memo", "goal": "Write the memo", "acceptance": ["At most 300 words as counted by read", "Every action item has an owner"]},
    }


def codes(issues):
    return [i.code for i in issues]


def test_the_services_shape_validates_without_a_reviewer_blind_to_the_writers_folder(tmp_path):
    """Study E: writer and reviewer hold built-in `read` over the notes; the memo lives in `lead/writer/work/`."""
    bp = documents_bp(tmp_path)
    issues = bpm.validate(bp, allowed_roots=[tmp_path])
    assert not bpm.errors(issues) and "verifier-cannot-read" not in codes(issues)
    agents = {a.addr: a for a in bpm._resolve(bp, None, [tmp_path], [])}
    assert not any(t in agents["lead/writer"].tools for t in bpm.WRITE_TOOLS)  # its work lands in its org folder
    assert bpm.org_files_readable(agents["lead/reviewer"]) and bpm.org_files_readable(agents["lead/writer"])


@pytest.mark.parametrize("tools", [[], ["read"], ["read", "shell"], ["web_search"]])
def test_org_files_are_readable_whatever_tools_a_verifier_holds(tools):
    # shell needs a workspace (a different rule); here only the tool set matters
    a = bpm.Agent(addr="lead/rev", name="rev", parent="lead", where="agents[rev]", tools=tools, kind="verifier",
                  workspace="/ws" if "shell" in tools else None)
    assert bpm.org_files_readable(a)


def test_the_gap_cannot_come_back_the_validator_warns_when_the_profile_would_not_let_read_open_the_org(tmp_path, monkeypatch):
    bp = documents_bp(tmp_path)
    real = World().runtime().confinement_policy

    class WithoutOrgRead(ConfinementPolicy):  # the old profile: the org is denied to the built-in read
        def file_confinement(self, org_root, tools, workspace, inputs):
            allowed, settings = real.file_confinement(org_root, tools, workspace, inputs)
            if "read" in settings:
                settings["read"] = {
                    "allowedPaths": [p for p in settings["read"]["allowedPaths"] if not p.startswith(str(org_root))],
                    "deniedPaths": [str(org_root), f"{org_root}/**"],
                }
            return allowed, settings

    bpm = World({ConfinementPolicy: WithoutOrgRead()})
    issues = bpm.validate(bp, allowed_roots=[tmp_path])
    warn = [i for i in issues if i.code == "verifier-cannot-read"]
    assert len(warn) == 1 and warn[0].level == "warning" and not bpm.errors(issues)
    assert "lead/reviewer" in warn[0].message and "lead/writer" in warn[0].message and "pasted text" in warn[0].message
    # a reviewer without the built-in read opens the org with orgmcp read: no warning
    ok = documents_bp(tmp_path, reviewer={"tools": []})
    assert "verifier-cannot-read" not in codes(bpm.validate(ok, allowed_roots=[tmp_path]))
    assert "cannot read the organization's files" in bpm.plan_for_user(bp, issues, allowed_roots=[tmp_path])


def test_the_plan_says_that_read_reaches_the_organizations_files(tmp_path):
    bp = documents_bp(tmp_path)
    agents = {a.addr: a for a in bpm._resolve(bp, None, [tmp_path], [])}
    notes = str((tmp_path / "notes").resolve())
    line = bpm._agent_access(agents["lead/reviewer"])
    assert line == f"can read files only in {notes} and the organization's own files; cannot change your files"
    assert bpm._access(agents["lead/reviewer"]) == f"kiro read only in {notes} and in the organization's own files (read-only)"
    plan = bpm.plan_for_user(bp, bpm.validate(bp, allowed_roots=[tmp_path]), allowed_roots=[tmp_path])
    assert line in plan
    # no built-in read: the inputs and the org both go through orgmcp read, as the plan already says
    ok = documents_bp(tmp_path, reviewer={"tools": []})
    rev = {a.addr: a for a in bpm._resolve(ok, None, [tmp_path], [])}["lead/reviewer"]
    assert bpm._agent_access(rev) == f"can read {notes} through the organization's read tool; cannot change your files"
