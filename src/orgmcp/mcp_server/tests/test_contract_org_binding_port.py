"""Contract of ``OrgBindingPort``: a binding is bound to a path; the organization there appears behind its back and is then found, without a restart; it can be created
once; the refusals say what to do. Over the real binding (on an opener that is a set of directories) and over the binding in memory."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import OrgError
from orgmcp.mcp_server import OrgBindingPort
from orgmcp.mcp_server.testing import IMPLEMENTATIONS, BindingWorld



@pytest.fixture(params=IMPLEMENTATIONS[OrgBindingPort], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> BindingWorld:
    made = cast(BindingWorld, request.param(tmp_path))
    assert isinstance(made.binding, OrgBindingPort)
    return made


def test_a_binding_is_bound_to_its_path_and_has_no_organization_yet(w: BindingWorld) -> None:
    assert w.binding.root == w.root
    assert w.binding.peek() is None and w.binding.location() is None


def test_get_refuses_with_the_message_that_says_what_to_do(w: BindingWorld) -> None:
    with pytest.raises(OrgError) as info:
        w.binding.get()
    assert str(info.value) == w.binding.missing_message()
    assert "create_org" in w.binding.missing_message() and str(w.root) in w.binding.missing_message()


def test_an_organization_that_appears_is_found_without_a_restart(w: BindingWorld) -> None:
    w.appear()
    assert w.binding.peek() is not None and w.binding.location() == w.root
    assert w.binding.get() is not None


def test_create_makes_the_organization_at_the_bound_path(w: BindingWorld) -> None:
    w.binding.create("A mission", None, None)
    assert w.binding.peek() is not None and w.binding.location() == w.root


def test_a_second_creation_is_refused_and_says_the_organization_is_ready(w: BindingWorld) -> None:
    w.binding.create("A mission")
    with pytest.raises(OrgError, match="already exists"):
        w.binding.create("Another mission")


def test_a_mission_is_required(w: BindingWorld) -> None:
    with pytest.raises(OrgError, match="mission is required"):
        w.binding.create("   ")
    assert w.binding.peek() is None
