"""``wire_access``: the runtime has the four access ports, built from the agents, the settings and the layout of the runtime."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.access import AccessScopes, AuthorityPolicy, ModelFloorAudit, ModelResolver, ToolNaming
from hirearchy.access._floor import CharterModelFloorAudit
from hirearchy.access.testing import StaticAccess
from hirearchy.agents import CharterReader
from hirearchy.agents.testing import MemoryAgents
from hirearchy.app import wiring
from hirearchy.kernel import OrgError
from hirearchy.settings import DEFAULT_MODEL, OrgSettings
from hirearchy.settings.testing import MemoryOrgSettings


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "ORG.md").write_text("---\ndefault_model: m-org\n---\nrules\n", encoding="utf-8")
    (tmp_path / "ceo").mkdir()
    (tmp_path / "ceo" / "AGENT.md").write_text(
        f"---\nrole: R\ntools: [read]\nworkspace: {tmp_path / 'ws'}\ninputs: [{tmp_path.parent / 'in'}]\n---\nbody\n", encoding="utf-8"
    )
    return tmp_path


def test_the_runtime_has_the_access_ports(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert isinstance(runtime.access_scopes, AccessScopes) and isinstance(runtime.authority_policy, AuthorityPolicy)
    assert isinstance(runtime.tool_naming, ToolNaming) and isinstance(runtime.model_resolver, ModelResolver)


def test_the_runtime_has_a_model_floor_audit(root: Path) -> None:
    runtime = wiring.open_runtime(root)
    assert isinstance(runtime.model_floor_audit, ModelFloorAudit) and isinstance(runtime.model_floor_audit, CharterModelFloorAudit)
    assert runtime.model_floor_audit.below_floor() == [("ceo", "m-org")]  # ORG.md says default_model: m-org, and ceo names no model


def test_building_the_ports_touches_nothing(tmp_path: Path) -> None:
    wiring.open_runtime(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_the_ports_answer_from_the_files_of_the_runtime_root(root: Path) -> None:
    runtime = wiring.open_runtime(root)
    assert runtime.access_scopes.workspace_of("ceo") == (root / "ws").resolve()
    assert runtime.access_scopes.inputs_of("ceo") == [(root.parent / "in").resolve()]
    assert runtime.tool_naming.tool_names("ceo") == {"read": "org_read", "write": "write"}
    assert runtime.model_resolver.model_for("ceo") == "m-org" and runtime.model_resolver.default_model() == "m-org"


def test_the_organization_directory_of_the_authority_policy_is_the_runtime_root(root: Path) -> None:
    runtime = wiring.open_runtime(root)
    with pytest.raises(OrgError, match="must not overlap the organization directory"):
        runtime.authority_policy.check_inputs([str(root / "ceo")])
    assert runtime.authority_policy.check_inputs([str(root.parent / "elsewhere")]) == [str(root.parent / "elsewhere")]


def test_an_override_of_the_charters_changes_every_access_port(root: Path) -> None:
    charters = MemoryAgents()
    charters.put("dev/AGENT.md", "---\nrole: R\ntools: [write]\nmodel: m-dev\nworkspace: /w/dev\n---\nb\n")
    runtime = wiring.open_runtime(root, {CharterReader: charters})
    assert runtime.tool_naming.tool_names("dev") == {"read": "read", "write": "org_write"}
    assert runtime.model_resolver.model_for("dev") == "m-dev"


def test_an_override_of_the_settings_changes_the_model_resolver(root: Path) -> None:
    runtime = wiring.open_runtime(root, {OrgSettings: MemoryOrgSettings("---\ndefault_model: from-the-fake\n---\n")})
    assert runtime.model_resolver.default_model() == "from-the-fake" and runtime.model_resolver.model_for("ceo") == "from-the-fake"


def test_an_override_of_a_port_replaces_it(tmp_path: Path) -> None:
    fake = StaticAccess()
    runtime = wiring.open_runtime(tmp_path, {ModelResolver: fake, AccessScopes: fake})
    assert runtime.model_resolver is fake and runtime.access_scopes is fake
    assert runtime.tool_naming is not fake
    assert runtime.model_resolver.default_model() == DEFAULT_MODEL
