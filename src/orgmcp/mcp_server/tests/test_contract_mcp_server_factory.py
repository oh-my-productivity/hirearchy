"""Contract of ``McpServerFactory``: a server for a known agent and for root; an agent that does not exist is refused; the server is named ``orgmcp`` and carries
instructions. Over the factory of the groups (on a binding and a directory in memory) and over the fixed factory."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from mcp.server.fastmcp import FastMCP

from orgmcp.kernel import ROOT, OrgError
from orgmcp.mcp_server import McpServerFactory
from orgmcp.mcp_server.testing import IMPLEMENTATIONS, FactoryWorld



@pytest.fixture(params=IMPLEMENTATIONS[McpServerFactory], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> FactoryWorld:
    made = cast(FactoryWorld, request.param(tmp_path))
    assert isinstance(made.factory, McpServerFactory)
    return made


def test_a_server_for_a_known_agent(w: FactoryWorld) -> None:
    server = cast(FastMCP, w.factory.build(w.known))
    assert server.name == "orgmcp" and server.instructions


def test_a_server_for_root(w: FactoryWorld) -> None:
    server = cast(FastMCP, w.factory.build(ROOT))
    assert server.name == "orgmcp" and server.instructions


def test_an_agent_that_does_not_exist_is_refused(w: FactoryWorld) -> None:
    with pytest.raises(OrgError):
        w.factory.build(w.unknown)
