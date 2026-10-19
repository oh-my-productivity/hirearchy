"""``HiringTools``: hire and retire."""

from __future__ import annotations

from orgmcp.mcp_server._tools_hiring import HiringTools
from orgmcp.mcp_server.testing import ScriptedHiring, ScriptedRetirement

from ._support import call, red, serve

pytestmark = red


def test_hire_passes_everything_and_says_the_address() -> None:
    hiring = ScriptedHiring()
    group = HiringTools(lambda: hiring, lambda: ScriptedRetirement())
    out = call(serve(group, "ceo"), "hire", name="eng", role="Engineer", charter="Build.", model="m", tools=["read"], can_hire=True,
               max_children=3, workspace="/w", inputs=["/in"])
    assert out == "hired ceo/eng"
    ((args, kwargs),) = hiring.log.of("hire")
    assert args == ("ceo", "eng", "Engineer", "Build.")
    assert kwargs == {"model": "m", "tools": ["read"], "can_hire": True, "max_children": 3, "workspace": "/w", "inputs": ["/in"]}


def test_hire_defaults() -> None:
    hiring = ScriptedHiring()
    call(serve(HiringTools(lambda: hiring, lambda: ScriptedRetirement()), "root"), "hire", name="ceo", role="CEO", charter="Lead.")
    assert hiring.log.of("hire")[0][1] == {"model": None, "tools": [], "can_hire": False, "max_children": 5, "workspace": None, "inputs": None}


def test_retire_says_who_and_what_came_back() -> None:
    retirement = ScriptedRetirement(refunded=4, to="ceo")
    group = HiringTools(lambda: ScriptedHiring(), lambda: retirement)
    assert call(serve(group, "ceo"), "retire", name="eng", reason="done") == "retired ceo/eng; 4 unspent run(s) of budget returned to ceo"
    assert retirement.log.of("retire_team") == [(("ceo", "eng", "done"), {})]


def test_retire_without_a_refund_says_only_who() -> None:
    group = HiringTools(lambda: ScriptedHiring(), lambda: ScriptedRetirement())
    assert call(serve(group, "ceo"), "retire", name="eng", reason="done") == "retired ceo/eng"
