"""``HiringTools``: hire and retire."""

from __future__ import annotations

import asyncio

import pytest

from hirearchy.mcp_server._tools_hiring import HiringTools
from hirearchy.mcp_server.testing import ScriptedHiring, ScriptedRetirement
from hirearchy.services.testing import AdmittingServiceEvidence

from ._support import call, described, serve
from .test_tools_services import Catalog


def tools(hiring: ScriptedHiring, retirement: ScriptedRetirement) -> HiringTools:
    """The group over scripted hiring and retirement, for an organization whose agents offer no service."""
    return HiringTools(lambda: hiring, lambda: retirement, lambda: Catalog({}), lambda: AdmittingServiceEvidence())


def test_hire_passes_everything_and_says_the_address() -> None:
    hiring = ScriptedHiring()
    group = tools(hiring, ScriptedRetirement())
    out = call(serve(group, "ceo"), "hire", name="eng", role="Engineer", charter="Build.", model="m", tools=["read"], can_hire=True,
               max_children=3, workspace="/w", inputs=["/in"])
    assert out == "hired ceo/eng"
    ((args, kwargs),) = hiring.log.of("hire")
    assert args == ("ceo", "eng", "Engineer", "Build.")
    assert kwargs == {"model": "m", "tools": ["read"], "can_hire": True, "max_children": 3, "workspace": "/w", "inputs": ["/in"],
                      "approved": False}


def test_hire_defaults() -> None:
    hiring = ScriptedHiring()
    call(serve(tools(hiring, ScriptedRetirement()), "root"), "hire", name="ceo", role="CEO", charter="Lead.")
    assert hiring.log.of("hire")[0][1] == {"model": None, "tools": [], "can_hire": False, "max_children": 5, "workspace": None, "inputs": None,
                                          "approved": False}


def test_retire_says_who_and_what_came_back() -> None:
    retirement = ScriptedRetirement(refunded=4, to="ceo")
    group = tools(ScriptedHiring(), retirement)
    assert call(serve(group, "ceo"), "retire", name="eng", reason="done") == "retired ceo/eng; 4 unspent run(s) of budget returned to ceo"
    assert retirement.log.of("retire_team") == [(("ceo", "eng", "done"), {})]


def test_retire_without_a_refund_says_only_who() -> None:
    group = tools(ScriptedHiring(), ScriptedRetirement())
    assert call(serve(group, "ceo"), "retire", name="eng", reason="done") == "retired ceo/eng"


def test_hire_docstring_states_the_bound() -> None:
    server = serve(tools(ScriptedHiring(), ScriptedRetirement()), "ceo")
    text = " ".join(described(server)["hire"].split())
    assert "can_hire: whether the report may build its own team; only root (the user) or an approved plan can grant it." in text
    assert (
        "max_children: the most direct reports it may have (for an agent hiring: at most its own); a report without can_hire gets 0." in text
    )
    assert "can_hire: whether the report may build its own team." not in text


@pytest.mark.parametrize("me", ["root", "ceo"])
def test_no_mcp_hire_has_an_approved_parameter(me: str) -> None:
    hiring = ScriptedHiring()
    server = serve(tools(hiring, ScriptedRetirement()), me)
    (hire,) = [t for t in asyncio.run(server.list_tools()) if t.name == "hire"]
    assert "approved" not in hire.inputSchema["properties"]
    call(server, "hire", name="eng", role="Engineer", charter="Build.")
    assert hiring.log.of("hire")[0][1]["approved"] is False  # whatever a client sends, the tool never passes it
