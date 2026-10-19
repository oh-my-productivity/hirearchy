"""Contract of ``BindingResolver``: the identity is root unless an agent is named, an agent gets its organization (pinned), and a root that is told nothing is bound to
a path whether or not an organization is there. Over the resolver of the environment (on in-memory locator and opener) and over the fixed resolver."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import ROOT
from orgmcp.mcp_server import BindingResolver, OrgBindingPort
from orgmcp.mcp_server.testing import IMPLEMENTATIONS, ResolverWorld



@pytest.fixture(params=IMPLEMENTATIONS[BindingResolver], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ResolverWorld:
    made = cast(ResolverWorld, request.param(tmp_path))
    assert isinstance(made.resolver, BindingResolver)
    return made


def test_nobody_in_particular_is_root(w: ResolverWorld) -> None:
    binding, me = w.resolver.resolve()
    assert me == ROOT and isinstance(binding, OrgBindingPort)


def test_an_agent_is_that_agent_and_its_organization_is_there(w: ResolverWorld) -> None:
    w.as_agent("ceo")
    binding, me = w.resolver.resolve()
    assert me == "ceo" and binding.peek() is not None and binding.location() == w.root


def test_root_with_an_organization_gets_it(w: ResolverWorld) -> None:
    w.as_root()
    binding, me = w.resolver.resolve()
    assert me == ROOT and binding.root == w.root and binding.location() == w.root
