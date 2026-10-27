"""The policy-free primitives are declared and pinned (phase 0a.2, design 5.8 and 7.5).

``Org.deliver`` and ``Org.runtime.<port>`` are the primitives every rule is built on (ARCHITECTURE.md 2.3): they apply no policy, and no surface exposes them.
What this pins: (1) no module of the MCP server or the CLI calls ``.deliver(``; (2) the MCP ``send`` tool of every identity and the CLI ``send`` command
cannot pass the fields that make a verdict, a link, a service task or a rework (``type``, ``feedback``, ``criterion``, ``service``, ``revises``,
``source``, ``acknowledges``); (3) ``Org.deliver`` says it is low level; (4) the guarded ``Org.send`` refuses the four shapes. A new surface that calls the primitive, or
widens ``send``, fails here."""

from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path

import pytest

from hirearchy.app import Org
from hirearchy.kernel import OrgError

from .paths import SRC

GUARDED = ("type", "feedback", "criterion", "service", "revises", "source", "acknowledges")
SURFACES = ("mcp_server", "cli")


def modules(package: str) -> list[Path]:
    """The modules of ``package`` outside its tests (and the in-memory fakes of ``testing.py``, which are no surface)."""
    return sorted(p for p in (SRC / package).rglob("*.py") if "tests" not in p.parts and p.name != "testing.py")


def test_no_mcp_or_cli_module_calls_deliver() -> None:
    found = [
        f"{path.relative_to(SRC)}:{number}"
        for package in SURFACES for path in modules(package)
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"\.deliver\(", line) and not line.lstrip().startswith("#")
    ]
    assert found == [], f"a surface calls the policy-free primitive Org.deliver / MessageDelivery.deliver: {found}"


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.", can_hire=True, max_children=2)
    made.hire("ceo", "eng", "Engineer", "Build.")
    return made


def tool_parameters(org: Org, identity: str) -> set[str]:
    from testkit.mcp_server_world import build_server

    tools = {t.name: t for t in asyncio.run(build_server(org, identity).list_tools())}
    return set(tools["send"].inputSchema["properties"])


@pytest.mark.parametrize("identity", ["root", "ceo", "ceo/eng"])
def test_mcp_send_and_cli_send_cannot_pass_the_guarded_fields(org: Org, identity: str) -> None:
    assert tool_parameters(org, identity) & set(GUARDED) == set()
    from hirearchy.app.wire_cli import cli_app

    send = next(a for a in cli_app().parser()._actions if isinstance(a, argparse._SubParsersAction)).choices["send"]
    dests = {a.dest for a in send._actions}
    assert dests & set(GUARDED) == set(), f"the CLI send command takes {dests & set(GUARDED)}"


def test_org_deliver_is_declared_low_level() -> None:
    assert (Org.deliver.__doc__ or "").startswith("Low level")


def test_the_guarded_org_send_refuses_the_four_shapes(org: Org) -> None:
    first = org.delegate("root", "ceo", "Work", "Do it.", "Done when it is.", budget=3)
    for fields in ({"type": "task", "service": "weekly-brief"}, {"type": "task", "revises": first.id}):
        with pytest.raises(OrgError, match="^refused: a root task for a service, or a rework"):
            org.send("root", "ceo", "again", **fields)
    for fields in ({"feedback": "reject"}, {"criterion": "C1"}):
        with pytest.raises(OrgError, match="^refused: a verdict or a link from root"):
            org.send("root", "ceo", "words", **fields)
