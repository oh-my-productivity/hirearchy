"""Contract of ``ProfileProvisioner``: the name of an organization's profile, and writing it only when it is missing or different."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kiro import ProfileProvisioner
from orgmcp.kiro.testing import IMPLEMENTATIONS, ProvisionerHarness

from ._support import make


@pytest.fixture(params=IMPLEMENTATIONS[ProfileProvisioner], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> ProvisionerHarness:
    made = make(request, tmp_path, ProvisionerHarness)
    assert isinstance(made.provisioner, ProfileProvisioner)
    return made


def digest(root: Path) -> str:
    return hashlib.sha1(str(root.resolve()).encode("utf-8")).hexdigest()[:6]


def profile(h: ProvisionerHarness, name: str) -> dict[str, object]:
    text = h.text(name)
    assert text is not None, f"no profile {name}"
    return cast(dict[str, object], json.loads(text))


# ----------------------------------------------------------------------------------------------------------------- the name


def test_the_name_of_an_organization_called_org_is_its_parents_name_and_org(h: ProvisionerHarness) -> None:
    assert h.provisioner.profile_name([]) == f"orgmcp-team-org-{digest(h.root)}"


def test_any_other_directory_name_is_the_slug(h: ProvisionerHarness) -> None:
    root = h.root.parent / "My Org!! (Ünï)"
    assert h.at(root).profile_name([]) == f"orgmcp-my-org-n-{digest(root)}"


def test_the_slug_is_cut_at_24_characters(h: ProvisionerHarness) -> None:
    root = h.root.parent / "a-very-long-organization-name-that-keeps-going"
    assert h.at(root).profile_name([]) == f"orgmcp-a-very-long-organization-{digest(root)}"


def test_a_name_without_letters_is_org(h: ProvisionerHarness) -> None:
    root = h.root.parent / "---"
    assert h.at(root).profile_name([]) == f"orgmcp-org-{digest(root)}"


def test_the_tools_are_appended_sorted_and_once(h: ProvisionerHarness) -> None:
    base = h.provisioner.profile_name([])
    assert h.provisioner.profile_name(["write", "read", "read"]) == base + "-read-write"
    assert h.provisioner.profile_name(["web_fetch", "Read"]) == base + "-read-web-fetch"


def test_a_tool_without_letters_is_left_out(h: ProvisionerHarness) -> None:
    assert h.provisioner.profile_name(["!!", "read"]) == h.provisioner.profile_name(["read"])


def test_two_organizations_with_the_same_directory_name_have_different_profiles(h: ProvisionerHarness) -> None:
    a, b = h.at(h.root.parent / "a" / "org"), h.at(h.root.parent / "b" / "org")
    assert a.profile_name([]) != b.profile_name([])
    assert re.fullmatch(r"orgmcp-a-org-[0-9a-f]{6}", a.profile_name([]))


def test_the_name_only_uses_lowercase_letters_digits_and_dashes(h: ProvisionerHarness) -> None:
    assert re.fullmatch(r"orgmcp-[a-z0-9-]+", h.provisioner.profile_name(["Web Search", "shell"]))


def test_naming_writes_nothing(h: ProvisionerHarness) -> None:
    h.provisioner.profile_name(["read"])
    assert h.names() == [] and h.writes() == []


# ----------------------------------------------------------------------------------------------------------- the profile


def test_the_shared_profile_has_the_name_of_the_tools_and_the_server_of_the_organization(h: ProvisionerHarness) -> None:
    name = h.provisioner.ensure_profile(["shell", "read"])
    assert name == h.provisioner.profile_name(["read", "shell"])
    data = profile(h, name)
    assert data["name"] == name and data["tools"] == ["@orgmcp", "read", "shell"] and data["allowedTools"] == ["@orgmcp", "read", "shell"]
    assert data["description"] == f"internal: used by the orgmcp scheduler for {h.root}; not a general-purpose agent (built-in tools: read, shell)"
    assert data["mcpServers"] == {"orgmcp": {**h.server, "env": {"ORG_ROOT": str(h.root), "ORG_REQUIRE_AGENT": "1"}}}
    assert "toolsSettings" not in data and data["includeMcpJson"] is False


def test_a_profile_without_tools_has_no_tool_list_in_its_description(h: ProvisionerHarness) -> None:
    data = profile(h, h.provisioner.ensure_profile([]))
    assert data["description"] == f"internal: used by the orgmcp scheduler for {h.root}; not a general-purpose agent"


def test_the_agent_is_not_baked_into_the_server_environment(h: ProvisionerHarness) -> None:
    servers = cast(dict[str, dict[str, dict[str, str]]], profile(h, h.provisioner.ensure_profile([]))["mcpServers"])
    assert "ORG_AGENT" not in servers["orgmcp"]["env"]


def test_a_profile_that_is_there_is_not_written_again(h: ProvisionerHarness) -> None:
    name = h.provisioner.ensure_profile(["read"])
    assert h.provisioner.ensure_profile(["read"]) == name and h.provisioner.ensure_profile(["read", "read"]) == name
    assert h.writes() == [name]


def test_a_profile_that_differs_is_replaced(h: ProvisionerHarness) -> None:
    name = h.provisioner.ensure_profile(["read"])
    text = h.text(name)
    h.put_raw(name, json.dumps({"name": name, "tools": ["@orgmcp"]}))
    assert h.provisioner.ensure_profile(["read"]) == name
    assert h.text(name) == text and h.writes() == [name, name]


@pytest.mark.parametrize("raw", ["{ not json", "[]", ""])
def test_a_profile_that_is_unreadable_is_repaired(h: ProvisionerHarness, raw: str) -> None:
    name = h.provisioner.ensure_profile([])
    text = h.text(name)
    h.put_raw(name, raw)
    assert h.provisioner.ensure_profile([]) == name and h.text(name) == text


def test_two_organizations_never_share_a_profile(h: ProvisionerHarness) -> None:
    a, b = h.at(h.root.parent / "a" / "org"), h.at(h.root.parent / "b" / "org")
    assert a.ensure_profile([]) != b.ensure_profile([])
    assert len(h.names()) == 2


# ------------------------------------------------------------------------------------------------------------ confinement


def test_a_confined_profile_has_a_hash_of_its_access_in_its_name(h: ProvisionerHarness) -> None:
    name = h.provisioner.ensure_profile(["read", "write"], workspace=Path("/golden/ws"), inputs=[Path("/golden/in-a")], confine=True)
    data = profile(h, name)
    settings = cast(dict[str, object], data["toolsSettings"])
    assert name == h.provisioner.profile_name(["read", "write"]) + "-x" + hashlib.sha1(json.dumps(settings, sort_keys=True).encode()).hexdigest()[:8]
    assert re.fullmatch(r".*-x[0-9a-f]{8}", name)
    assert data["tools"] == ["@orgmcp", "read", "write"] and data["allowedTools"] == ["@orgmcp"]


def test_the_same_access_shares_a_profile_and_different_access_never_does(h: ProvisionerHarness) -> None:
    kw = {"workspace": Path("/golden/ws"), "inputs": [Path("/golden/in-a")], "confine": True}
    name = h.provisioner.ensure_profile(["read", "write"], **kw)  # type: ignore[arg-type]
    assert h.provisioner.ensure_profile(["write", "read"], **kw) == name  # type: ignore[arg-type]
    assert h.provisioner.ensure_profile(["read", "write"], workspace=Path("/golden/ws"), inputs=[], confine=True) != name
    assert h.provisioner.ensure_profile(["read", "write"], workspace=Path("/golden/other"), inputs=[Path("/golden/in-a")], confine=True) != name
    assert h.writes().count(name) == 1


def test_confinement_is_only_applied_when_asked_for(h: ProvisionerHarness) -> None:
    unconfined = h.provisioner.ensure_profile(["read", "write"], workspace=Path("/golden/ws"))
    assert unconfined == h.provisioner.profile_name(["read", "write"]) and "toolsSettings" not in profile(h, unconfined)
    assert profile(h, unconfined)["allowedTools"] == ["@orgmcp", "read", "write"]


def test_a_confined_profile_without_file_tools_has_no_settings(h: ProvisionerHarness) -> None:
    name = h.provisioner.ensure_profile(["shell"], workspace=Path("/golden/ws"), confine=True)
    data = profile(h, name)
    assert "toolsSettings" not in data and data["allowedTools"] == ["@orgmcp", "shell"]
