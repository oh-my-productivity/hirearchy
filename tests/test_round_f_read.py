"""Round F-read: an agent with kiro's built-in ``read`` can read the organization's files.

The experiment (studies/F-read-experiment/NOTES.md, kiro-cli 2.29.1): an agent that holds the built-in ``read`` sees ONE
tool named ``read`` (kiro's); orgmcp's ``read`` is hidden behind it. The profile used to deny the org directory to the
built-in ``read``, so such an agent could not open a teammate's ``work/`` file at all (study E, F3: 85 failed calls and
a playbook that pastes the memo inline). The profile now lets the built-in ``read`` open the org (read-only: what
orgmcp ``read`` may open anyway); everything outside the org, the inputs and the workspace stays refused.
"""

import hashlib
import json
from pathlib import Path

import pytest

from orgmcp import blueprint as bpm
from orgmcp import scheduler
from orgmcp.core import ROOT, Org
from orgmcp.scheduler import ensure_kiro_profile, file_confinement, kiro_profile_name, kiro_runner


def profile_of(isolated_kiro, name):
    return json.loads((isolated_kiro / ".kiro" / "agents" / f"{name}.json").read_text())


def run_profile(org, isolated_kiro, addr):
    cmd, cwd, env = kiro_runner()(org, addr, "P")
    name = cmd[cmd.index("--agent") + 1]
    return name, profile_of(isolated_kiro, name), cwd


@pytest.fixture
def org(tmp_path):
    (tmp_path / "inputs").mkdir()
    (tmp_path / "proj").mkdir()
    o = Org.init(tmp_path / "org", "f-read", {"poll_seconds": 0.05})
    o.hire(ROOT, "lead", "Lead", "Lead.", can_hire=True, tools=["read", "write", "web_search"],
           workspace=str(tmp_path / "proj"), inputs=[str(tmp_path / "inputs")])
    o.hire("lead", "writer", "Writer", "Write.", tools=["read"], inputs=[str(tmp_path / "inputs")])
    return o


# ------------------------------------------------------------------------------------------ profiles


def test_an_agent_with_built_in_read_may_read_the_org_and_its_inputs_only(org, tmp_path, isolated_kiro):
    _, prof, _ = run_profile(org, isolated_kiro, "lead/writer")
    inputs = tmp_path / "inputs"
    assert prof["toolsSettings"]["read"] == {
        "allowedPaths": [str(inputs), f"{inputs}/**", str(org.root), f"{org.root}/**"],
        "deniedPaths": [],  # a deny on the org would beat the allow
    }
    assert prof["allowedTools"] == ["@orgmcp"]  # read stays out of allowedTools, or kiro would ignore allowedPaths
    assert prof["tools"] == ["@orgmcp", "read"]


def test_the_org_is_read_only_for_kiro_tools(org, tmp_path, isolated_kiro):
    ws = tmp_path / "proj"
    org.hire("lead", "dev", "Dev", "x", tools=["read", "write"], workspace=str(ws))
    _, prof, _ = run_profile(org, isolated_kiro, "lead/dev")
    assert prof["toolsSettings"]["write"] == {"allowedPaths": [f"{ws}/**"], "deniedPaths": [str(org.root), f"{org.root}/**"]}
    read = prof["toolsSettings"]["read"]["allowedPaths"]
    assert f"{org.root}/**" in read and f"{ws}/**" in read
    assert str(tmp_path) not in read and f"{tmp_path}/**" not in read  # nothing wider than the org, workspace, inputs


def test_nothing_else_outside_the_org_is_reachable(org, tmp_path):
    _, settings = file_confinement(org.root, ["read"], None, [tmp_path / "inputs"])
    allowed = settings["read"]["allowedPaths"]
    assert {Path(p[:-3] if p.endswith("/**") else p) for p in allowed} == {tmp_path / "inputs", org.root}


def test_an_agent_without_built_in_read_is_unchanged(org, tmp_path, isolated_kiro):
    org.hire("lead", "web", "Web", "x", tools=["web_search"])
    name, prof, _ = run_profile(org, isolated_kiro, "lead/web")
    assert name == kiro_profile_name(org.root, ["web_search"]) and "toolsSettings" not in prof
    org.hire("lead", "scribe", "Scribe", "x", tools=["write"], workspace=str(tmp_path / "proj"))
    _, prof, _ = run_profile(org, isolated_kiro, "lead/scribe")
    assert set(prof["toolsSettings"]) == {"write"}  # no read rule: it has no built-in read, orgmcp `read` serves the org


def test_a_legacy_read_only_charter_keeps_its_unconfined_profile(org, isolated_kiro):
    (org.dir("lead") / "old").mkdir()
    (org.dir("lead") / "old" / "AGENT.md").write_text("---\nrole: Old\ntools: [read]\n---\nOld.\n")
    name, prof, _ = run_profile(org, isolated_kiro, "lead/old")
    assert name == kiro_profile_name(org.root, ["read"])
    assert prof["allowedTools"] == ["@orgmcp", "read"] and "toolsSettings" not in prof


def test_a_workspace_inside_the_org_still_works(org, isolated_kiro):
    ws = org.dir("lead") / "work" / "site"
    ws.mkdir(parents=True)
    org.hire(ROOT, "inorg", "In", "x", tools=["read", "write"], workspace=str(ws))
    _, prof, _ = run_profile(org, isolated_kiro, "inorg")
    assert prof["toolsSettings"]["write"]["deniedPaths"] == [] and prof["toolsSettings"]["read"]["deniedPaths"] == []
    assert f"{org.root}/**" in prof["toolsSettings"]["read"]["allowedPaths"]


# --------------------------------------------------------------------------------- existing profiles


def old_read_settings(org, tmp_path):
    """What the profile of `lead/writer` said before: workspace + inputs, the org denied."""
    p = tmp_path / "inputs"
    return {"read": {"allowedPaths": [str(p), f"{p}/**"], "deniedPaths": [str(org.root), f"{org.root}/**"]}}


def test_an_existing_per_org_profile_is_replaced_by_one_with_the_new_access(org, tmp_path, isolated_kiro):
    agents = isolated_kiro / ".kiro" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    old = old_read_settings(org, tmp_path)
    old_name = kiro_profile_name(org.root, ["read"]) + "-x" + hashlib.sha1(json.dumps(old, sort_keys=True).encode()).hexdigest()[:8]
    old_text = json.dumps({"name": old_name, "toolsSettings": old}) + "\n"
    (agents / f"{old_name}.json").write_text(old_text)
    legacy = agents / "orgmcp-read.json"  # the legacy global profile: never touched
    legacy.write_text('{"name": "orgmcp-read"}\n')
    name, prof, _ = run_profile(org, isolated_kiro, "lead/writer")
    assert name != old_name  # the profile name carries a hash of the access, so new access = new profile
    assert prof["toolsSettings"]["read"]["deniedPaths"] == [] and f"{org.root}/**" in prof["toolsSettings"]["read"]["allowedPaths"]
    assert (agents / f"{old_name}.json").read_text() == old_text and legacy.read_text() == '{"name": "orgmcp-read"}\n'


def test_a_profile_file_with_stale_content_is_rewritten(org, tmp_path, isolated_kiro):
    d = tmp_path / "agents"
    kw = dict(org=org, workspace=None, inputs=[tmp_path / "inputs"], confine=True)
    name = ensure_kiro_profile(["read"], d, **kw)
    path = d / f"{name}.json"
    stale = json.loads(path.read_text())
    stale["toolsSettings"]["read"] = old_read_settings(org, tmp_path)["read"]  # same file name, the old rule inside
    path.write_text(json.dumps(stale))
    assert ensure_kiro_profile(["read"], d, **kw) == name
    assert json.loads(path.read_text())["toolsSettings"]["read"]["deniedPaths"] == []
    assert f"{org.root}/**" in json.loads(path.read_text())["toolsSettings"]["read"]["allowedPaths"]


# ------------------------------------------------------------------------------------ prompt and plan


def test_the_prompt_tells_a_built_in_read_agent_to_read_org_files_by_absolute_path(org):
    files = org.run_prompt("lead/writer", []).split("- Files:")[1].split("# New messages")[0]
    assert "Your `read` is kiro's built-in (it hides `@orgmcp/read`)" in files
    assert f"`{org.root}/<path in the org>`" in files and "ABSOLUTE" in files
    assert "never with the built-in `write`/`read`" not in files
    assert "kiro `read` to workspace + inputs + the organization (read-only)" in files


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
    real = scheduler.file_confinement

    def without_org(org_root, tools, workspace, inputs):  # the old profile: the org is denied to the built-in read
        allowed, settings = real(org_root, tools, workspace, inputs)
        if "read" in settings:
            settings["read"] = {
                "allowedPaths": [p for p in settings["read"]["allowedPaths"] if not p.startswith(str(org_root))],
                "deniedPaths": [str(org_root), f"{org_root}/**"],
            }
        return allowed, settings

    monkeypatch.setattr(scheduler, "file_confinement", without_org)
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
