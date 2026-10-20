"""``StaticAccess``, the in-memory fake: it is all four ports, and the means to prepare agents and ORG.md."""

from __future__ import annotations

from pathlib import Path

from orgmcp.access import AccessScopes, AuthorityPolicy, ModelResolver, ToolNaming
from orgmcp.access.testing import StaticAccess


def test_it_is_all_four_ports() -> None:
    fake = StaticAccess()
    assert isinstance(fake, AccessScopes) and isinstance(fake, AuthorityPolicy)
    assert isinstance(fake, ToolNaming) and isinstance(fake, ModelResolver)


def test_agents_and_the_configuration_are_prepared_in_memory() -> None:
    fake = StaticAccess(Path("/the/org"), "---\ndefault_model: m-org\n---\n")
    fake.put_agent("ceo", {"role": "R", "tools": ["read"], "workspace": "/w/ceo", "model": "m-1"})
    assert fake.root == Path("/the/org")
    assert fake.workspace_of("ceo") == Path("/w/ceo").resolve()
    assert fake.tool_names("ceo") == {"read": "org_read", "write": "write"}
    assert fake.model_for("ceo") == "m-1" and fake.default_model() == "m-org"
    fake.put_config("---\ndefault_model: m-2\n---\n")
    assert fake.default_model() == "m-2"
    assert fake.check_inputs(["/elsewhere/x"]) == ["/elsewhere/x"]


def test_it_touches_no_file(tmp_path: Path) -> None:
    fake = StaticAccess()
    fake.put_agent("ceo", {"role": "R", "workspace": str(tmp_path / "ws")})
    fake.check_authority("ceo", [], str(tmp_path / "ws" / "sub"))
    assert list(tmp_path.iterdir()) == []
