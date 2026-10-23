# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

import json
import re

from testkit.kiro_world import kiro_part, kiro_profile_name, kiro_runner, profiles_in
from testkit.reach.hirearchy.core import ROOT


def test_kiro_runner_builds_isolated_command(org, tmp_path, monkeypatch):
    profiles_in(org, tmp_path / "agents")
    org.write(ROOT, "ceo/AGENT.md", "---\nrole: CEO\nmodel: claude-opus-5.5\ntools: [read]\n---\nLead.\n")
    argv, cwd, env = kiro_runner()(org, "ceo", "PROMPT")
    cmd = kiro_part(argv)
    name = cmd[4]
    assert re.fullmatch(rf"{re.escape(kiro_profile_name(org.root, ['read']))}-x[0-9a-f]{{8}}", name)  # built-in read: confined to the org
    assert cmd[:4] == ["kiro-cli", "chat", "--no-interactive", "--agent"]
    assert cmd[5:9] == ["--model", "claude-opus-5.5", "--effort", "high"]
    assert cmd[9:] == ["--v3", "--require-mcp-startup", "--output-format", "stream-json"]
    assert "PROMPT" not in argv  # the prompt goes via stdin
    assert cwd == org.runtime.kiro_places.scratch("ceo") and env["ORG_AGENT"] == "ceo" and env["ORG_ROOT"] == str(org.root)  # kiro starts in an empty scratch directory
    profile = json.loads((tmp_path / "agents" / f"{name}.json").read_text())
    assert profile["includeMcpJson"] is False  # no gmail/whatsapp/etc. inside the org
    assert profile["tools"] == ["@hirearchy", "read"] and "hirearchy" in profile["mcpServers"]
