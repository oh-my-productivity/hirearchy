"""Golden: the kiro profiles ``ensure_kiro_profile`` writes (one per confinement shape) and the scheduler's kiro command line."""

import json
import re
from hashlib import sha1
from pathlib import Path
from types import SimpleNamespace

import pytest
from golden_support import check
from scenarios import company, dirs

from orgmcp import scheduler
from orgmcp.core import ROOT

STUB_ORG = SimpleNamespace(root=Path("/golden/org"))  # ensure_kiro_profile only reads ``org.root``: a fixed path, fixed hashes
SHAPES = {
    "shared_no_tools": dict(tools=[]),
    "shared_shell": dict(tools=["shell"]),
    "shared_read_unconfined": dict(tools=["read"]),
    "confined_read_write_shell": dict(
        tools=["read", "write", "shell"], confine=True, workspace=Path("/golden/ws"),
        inputs=[Path("/golden/in-a"), Path("/golden/in-b")]),
    "confined_write_only": dict(tools=["write"], confine=True, workspace=Path("/golden/ws")),
    "confined_write_without_workspace": dict(tools=["write"], confine=True),
    "confined_read_inputs_only": dict(tools=["read"], confine=True, inputs=[Path("/golden/in-a")]),
    "confined_read_workspace_inside_the_org": dict(tools=["read", "write"], confine=True, workspace=Path("/golden/org/ws")),
    "confined_shell_only": dict(tools=["shell"], confine=True, workspace=Path("/golden/ws")),
}


@pytest.fixture
def fixed_server(monkeypatch):
    monkeypatch.setattr(scheduler, "mcp_server_command", lambda: {"command": "<ORGMCP_BIN>", "args": ["mcp"]})


def test_kiro_profile_for_each_confinement_shape(tmp_path, fixed_server):
    out = []
    for label, kw in SHAPES.items():
        agents = tmp_path / label
        name = scheduler.ensure_kiro_profile(kw["tools"], agents, org=STUB_ORG, **{k: v for k, v in kw.items() if k != "tools"})
        text = (agents / f"{name}.json").read_text(encoding="utf-8")
        assert [p.name for p in agents.iterdir()] == [f"{name}.json"]
        out.append(f"##### {label}: {name}.json\n{text}")
    check("kiro/profiles.txt", "\n".join(out))


def test_kiro_profile_names(tmp_path):
    names = [
        scheduler.kiro_profile_name("/golden/org", []),
        scheduler.kiro_profile_name("/golden/org", ["write", "read", "read"]),
        scheduler.kiro_profile_name("/golden/Some Team/org", ["shell"]),
        scheduler.kiro_profile_name("/golden/Quarterly Review 2026 -- extra long name", ["shell"]),
        scheduler.kiro_profile_name("/org", []),
    ]
    check("kiro/profile_names.txt", "\n".join(names) + "\n")


def test_file_confinement_settings():
    out = {}
    for label, kw in SHAPES.items():
        if kw.get("confine"):
            allowed, settings = scheduler.file_confinement(
                Path("/golden/org"), sorted(kw["tools"]), kw.get("workspace"), list(kw.get("inputs", [])))
            out[label] = {"allowedTools": allowed, "toolsSettings": settings}
    check("kiro/file_confinement.json", json.dumps(out, indent=2, sort_keys=True) + "\n")


def test_mcp_server_command_is_the_venv_script(norm):
    cmd = scheduler.mcp_server_command()
    check("kiro/mcp_server_command.json", norm(json.dumps(cmd, indent=2)) + "\n")


def scrub(text: str, root: Path, norm) -> str:
    """Profile names carry a hash of the real org path (and of its access settings): placeholders for those."""
    digest = sha1(str(root.resolve()).encode("utf-8")).hexdigest()[:6]
    return re.sub(r"-x[0-9a-f]{8}\b", "-x<ACCESS_HASH>", norm(text).replace(f"-{digest}", "-<ROOT_HASH>"))


def test_scheduler_kiro_command_line(tmp_path, clock, norm):
    team = tmp_path / "golden-team"  # the profile name carries the org's directory name: a fixed one, not the test's
    team.mkdir()
    org = company(team, clock)
    ws, inputs = dirs(tmp_path)
    norm.add(ws, "<WS>")
    norm.add(inputs, "<INPUTS>")
    org.hire(ROOT, "sh", "Shell", "x", tools=["shell"], workspace=str(ws))
    org.hire(ROOT, "dev", "Dev", "x", tools=["read", "write", "shell"], workspace=str(ws), inputs=[str(inputs)])
    org.hire(ROOT, "ro", "Reader", "x", tools=["read"], inputs=[str(inputs)])
    org.hire(ROOT, "modeled", "Modeled", "x", model="claude-haiku-4.5")
    org.hire(ROOT, "legacy", "Legacy", "x", tools=["read"])
    legacy_meta = org.dir("legacy") / "AGENT.md"  # a charter written before `inputs` existed: no key, unconfined `read`
    legacy_meta.write_text(re.sub(r"^inputs:.*\n", "", legacy_meta.read_text(encoding="utf-8"), flags=re.M), encoding="utf-8")
    build = scheduler.kiro_runner()
    out = []
    for addr in ("ceo", "ceo/eng", "sh", "dev", "ro", "modeled", "legacy"):
        cmd, cwd, env = build(org, addr, "PROMPT")
        profile = next(a for i, a in enumerate(cmd) if cmd[i - 1] == "--agent")
        content = (scheduler.KIRO_AGENTS_DIR / f"{profile}.json").read_text(encoding="utf-8")
        added = {k: v for k, v in env.items() if k in ("ORG_ROOT", "ORG_AGENT")}
        out.append(f"##### {addr}\ncommand: {scrub(json.dumps(cmd), org.root, norm)}\ncwd: {norm(str(cwd))}\n"
                   f"env: {scrub(json.dumps(added, sort_keys=True), org.root, norm)}\n"
                   f"profile file: {scrub(profile, org.root, norm)}.json\n{scrub(content, org.root, norm)}")
    check("kiro/runner_command_lines.txt", "\n".join(out))
    assert sorted(p.name for p in scheduler.KIRO_AGENTS_DIR.iterdir()), "profiles were written into the sandbox, not ~/.kiro"
