"""Root's structural calls over MCP are refused in favour of the extension (design 13, 11.4; owner question Q3).

A new agent, a retire, a first definition of a service, a charter write and a change of ``max_depth`` change the organization, so the user approves them
in a plan (``propose_org(..., extend="current")``). The texts below are the design's, word for word.
"""

from __future__ import annotations

import pytest

from hirearchy.kernel import ROOT
from hirearchy.mcp_server._root_structure import RootStructureGuard
from hirearchy.mcp_server._tools_hiring import HiringTools
from hirearchy.mcp_server.testing import ScriptedHiring, ScriptedRetirement
from hirearchy.services.testing import AdmittingServiceEvidence

from ._support import call, described, fails, serve
from .test_tools_services import Catalog

ROOT_HIRE = (
    'refused: a new agent changes the organization, so the user approves it in a plan: propose_org(blueprint=<an extension with add_agents>, '
    'extend="current"), show its PLAN FOR YOU block, then apply_org(..., approved=True, plan_id=...). (At the terminal the user can run '
    "hirearchy hire.) Nothing was created."
)


def root_retire(addr: str) -> str:
    return (
        f"refused: retiring {addr} changes the organization, so the user approves it in a plan: propose_org(blueprint=<an extension with retire: "
        f'[{{agent: {addr}, reason: ...}}]>, extend="current"), show its PLAN FOR YOU block, then apply it after their approval. Nothing was retired.'
    )


def group(hiring: ScriptedHiring, retirement: ScriptedRetirement) -> HiringTools:
    return HiringTools(lambda: hiring, lambda: retirement, lambda: Catalog({}), lambda: AdmittingServiceEvidence(), RootStructureGuard())


def test_root_hire_is_root_hire_word_for_word_and_creates_nothing() -> None:
    hiring = ScriptedHiring()
    refusal = fails(serve(group(hiring, ScriptedRetirement()), ROOT), "hire", name="eng", role="Engineer", charter="Build.")
    assert ROOT_HIRE in refusal
    assert hiring.log.of("hire") == []


def test_root_retire_is_root_retire_naming_the_agent_and_retires_nothing() -> None:
    retirement = ScriptedRetirement()
    refusal = fails(serve(group(ScriptedHiring(), retirement), ROOT), "retire", name="ceo/eng", reason="done")
    assert root_retire("ceo/eng") in refusal
    assert root_retire("ceo") in fails(serve(group(ScriptedHiring(), retirement), ROOT), "retire", name=" /ceo/ ", reason="done")
    assert retirement.log.of("retire_team") == []


def test_root_hire_docstring_points_to_the_extension() -> None:
    text = " ".join(described(serve(group(ScriptedHiring(), ScriptedRetirement()), ROOT))["hire"].split())
    assert text.startswith(
        "Root's hire is refused: a new agent changes the organization, so the user approves it in a plan: propose_org(blueprint=<an extension "
        'with add_agents>, extend="current"), show its PLAN FOR YOU block, then apply_org after their approval. (Your agents use hire for their '
        "own reports; at the terminal the user can run hirearchy hire.)"
    )
    assert "name: lowercase-dashed (becomes the address <you>/<name>)." in text and "A new report has no budget until you delegate a task to it." in text


@pytest.mark.parametrize("me", ["ceo", "ceo/mgr"])
def test_an_agents_hire_and_retire_are_unchanged(me: str) -> None:
    hiring, retirement = ScriptedHiring(), ScriptedRetirement(refunded=2, to=me)
    server = serve(group(hiring, retirement), me)
    assert call(server, "hire", name="eng", role="Engineer", charter="Build.") == f"hired {me}/eng"
    assert call(server, "retire", name="eng", reason="done") == f"retired {me}/eng; 2 unspent run(s) of budget returned to {me}"
    assert " ".join(described(server)["hire"].split()).startswith("Create a direct report (only if your charter allows hiring).")
