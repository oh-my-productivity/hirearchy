import json

from orgmcp.core import ROOT
from orgmcp.scheduler import ensure_kiro_profile, kiro_profile_name, kiro_runner


def test_kiro_runner_builds_isolated_command(org, tmp_path, monkeypatch):
    monkeypatch.setattr("orgmcp.scheduler.KIRO_AGENTS_DIR", tmp_path / "agents")
    monkeypatch.setattr("orgmcp.scheduler.ensure_kiro_profile",
                        lambda tools, org: ensure_kiro_profile(tools, tmp_path / "agents", org=org))
    org.write(ROOT, "ceo/AGENT.md", "---\nrole: CEO\nmodel: claude-haiku-4.5\ntools: [read]\n---\nLead.\n")
    cmd, cwd, env = kiro_runner()(org, "ceo", "PROMPT")
    name = kiro_profile_name(org.root, ["read"])
    assert cmd[:5] == ["kiro-cli", "chat", "--no-interactive", "--agent", name]
    assert cmd[-2:] == ["--model", "claude-haiku-4.5"] and "PROMPT" not in cmd  # the prompt goes via stdin
    assert cwd == org.dir("ceo") and env["ORG_AGENT"] == "ceo" and env["ORG_ROOT"] == str(org.root)
    profile = json.loads((tmp_path / "agents" / f"{name}.json").read_text())
    assert profile["includeMcpJson"] is False  # no gmail/whatsapp/etc. inside the org
    assert profile["tools"] == ["@orgmcp", "read"] and "orgmcp" in profile["mcpServers"]
