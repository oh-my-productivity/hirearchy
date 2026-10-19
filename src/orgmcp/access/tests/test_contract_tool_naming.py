"""Contract of ``ToolNaming``: an agent that holds the built-in ``read`` or ``write`` has the organization's tool as ``org_<name>``."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.access import ToolNaming
from orgmcp.access.testing import IMPLEMENTATIONS, AccessHarness

from ._support import make


@pytest.fixture(params=IMPLEMENTATIONS[ToolNaming], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> AccessHarness:
    made = make(request, tmp_path)
    assert isinstance(made.naming, ToolNaming)
    return made


@pytest.mark.parametrize(
    ("tools", "read", "write"),
    [
        ([], "read", "write"),
        (["shell"], "read", "write"),
        (["web", "shell"], "read", "write"),
        (["read"], "org_read", "write"),
        (["write"], "read", "org_write"),
        (["read", "write", "shell"], "org_read", "org_write"),
        (["write", "read"], "org_read", "org_write"),
    ],
)
def test_a_built_in_of_the_same_name_shadows_the_organizations_tool(h: AccessHarness, tools: list[str], read: str, write: str) -> None:
    h.put_agent("dev", {"role": "R", "tools": tools})
    assert h.naming.tool_names("dev") == {"read": read, "write": write}


def test_the_keys_are_read_then_write(h: AccessHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["write", "read"]})
    assert list(h.naming.tool_names("dev")) == ["read", "write"]


@pytest.mark.parametrize("meta", [{"role": "R"}, {"role": "R", "tools": None}, {"role": "R", "tools": []}])
def test_a_charter_without_tools_keeps_the_plain_names(h: AccessHarness, meta: dict[str, object]) -> None:
    h.put_agent("dev", meta)
    assert h.naming.tool_names("dev") == {"read": "read", "write": "write"}


def test_root_keeps_the_plain_names(h: AccessHarness) -> None:
    assert h.naming.tool_names("root") == {"read": "read", "write": "write"}


def test_a_new_dict_every_time(h: AccessHarness) -> None:
    h.put_agent("dev", {"role": "R"})
    first = h.naming.tool_names("dev")
    first["read"] = "changed"
    assert h.naming.tool_names("dev") == {"read": "read", "write": "write"}


def test_an_agent_that_does_not_exist_is_the_error_of_the_charter_reader(h: AccessHarness) -> None:
    with pytest.raises(FileNotFoundError):
        h.naming.tool_names("nobody")


def test_the_charter_is_read_again_every_time(h: AccessHarness) -> None:
    h.put_agent("dev", {"role": "R", "tools": ["read"]})
    assert h.naming.tool_names("dev")["read"] == "org_read"
    h.put_agent("dev", {"role": "R", "tools": []})
    assert h.naming.tool_names("dev")["read"] == "read"
