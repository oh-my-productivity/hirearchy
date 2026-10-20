# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

import json
import re

import pytest
from testkit.legacy.orgmcp.cli import main
from testkit.legacy.orgmcp.scheduler import ensure_kiro_profile, kiro_profile_name, kiro_runner


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("ORG_ROOT", "ORG_AGENT", "ORG_REQUIRE_AGENT"):
        monkeypatch.delenv(var, raising=False)


# --------------------------------------------------------- isolated profiles
def test_profile_name_is_per_org_lowercase_and_stable(tmp_path):
    a, b = tmp_path / "a" / "org", tmp_path / "b" / "org"
    names = {kiro_profile_name(a, []), kiro_profile_name(b, [])}
    assert len(names) == 2  # same directory name, different org: different profiles
    assert kiro_profile_name(a, []) == kiro_profile_name(str(a), [])
    for name in (*names, kiro_profile_name(a, ["web_fetch", "Read"])):
        assert re.fullmatch(r"orgmcp-[a-z0-9-]+", name), name
    assert re.fullmatch(r"orgmcp-a-org-[0-9a-f]{6}", kiro_profile_name(a, []))
    assert kiro_profile_name(a, ["write", "read"]) == kiro_profile_name(a, ["read", "write"]) == \
        kiro_profile_name(a, []) + "-read-write"
    weird = tmp_path / "My Org!! (Ünï)"
    assert re.fullmatch(r"orgmcp-[a-z0-9-]+-[0-9a-f]{6}", kiro_profile_name(weird, []))


def test_profile_is_internal_and_bound_to_its_org(org, tmp_path):
    agents = tmp_path / "agents"
    agents.mkdir()
    legacy = agents / "orgmcp.json"
    legacy.write_text('{"name": "orgmcp", "legacy": true}')
    name = ensure_kiro_profile(["read", "shell"], agents, org=org)
    assert name == kiro_profile_name(org.root, ["read", "shell"])
    profile = json.loads((agents / f"{name}.json").read_text())
    assert profile["name"] == name
    assert profile["description"].startswith(f"internal: used by the orgmcp scheduler for {org.root}; not a general-purpose agent")
    server = profile["mcpServers"]["orgmcp"]
    assert server["env"] == {"ORG_ROOT": str(org.root), "ORG_REQUIRE_AGENT": "1"}
    assert "ORG_AGENT" not in server["env"]  # identity comes from the scheduler's process environment
    assert server["args"][-1] == "mcp"
    assert profile["tools"] == ["@orgmcp", "read", "shell"] and profile["includeMcpJson"] is False
    assert legacy.read_text() == '{"name": "orgmcp", "legacy": true}'  # the global profile is never touched
    assert sorted(p.name for p in agents.iterdir()) == sorted(["orgmcp.json", f"{name}.json"])


def test_kiro_runner_uses_the_per_org_profile_and_keeps_the_scheduler_env(org, isolated_kiro):
    cmd, _, env = kiro_runner()(org, "ceo", "P")
    name = kiro_profile_name(org.root, [])
    assert cmd[:5] == ["kiro-cli", "chat", "--no-interactive", "--agent", name]
    assert env["ORG_AGENT"] == "ceo" and env["ORG_ROOT"] == str(org.root)
    assert (isolated_kiro / ".kiro" / "agents" / f"{name}.json").is_file()
    assert not (isolated_kiro / ".kiro" / "agents" / "orgmcp.json").exists()


def test_cli_kiro_profile_writes_the_org_profile(org, isolated_kiro, capsys):
    main(["--root", str(org.root), "kiro-profile", "--tools", "read"])
    name = kiro_profile_name(org.root, ["read"])
    assert (isolated_kiro / ".kiro" / "agents" / f"{name}.json").is_file()
    assert f"wrote ~/.kiro/agents/{name}.json" in capsys.readouterr().out
