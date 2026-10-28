"""Root's structural calls over MCP are refused in favour of the extension (design 13, 11.4; owner question Q3).

A new agent, a retire, a first definition of a service, a charter write and a change of ``max_depth`` change the organization, so the user approves them
in a plan (``propose_org(..., extend="current")``). The texts below are the design's, word for word.
"""

from __future__ import annotations

import pytest

from pathlib import Path

from hirearchy.kernel import ROOT, OrgPaths
from hirearchy.mcp_server._root_structure import RootStructureGuard
from hirearchy.mcp_server._tools_files import FileTools
from hirearchy.mcp_server._tools_hiring import HiringTools
from hirearchy.mcp_server._tools_services import ServiceTools
from hirearchy.mcp_server.testing import (
    HeldBudgets, ScriptedFiles, ScriptedHiring, ScriptedReports, ScriptedRetirement, ScriptedSteps, StaticNaming,
)
from hirearchy.settings.testing import MemoryOrgSettings
from hirearchy.services.testing import AdmittingServiceEvidence

from ._support import call, described, fails, serve
from .test_tools_services import Catalog, Commands

HERE = Path("/memory/org")
ORG_MD = "---\nmax_depth: 4\neffort: high\n---\nThe rules.\n"

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
    return HiringTools(lambda: hiring, lambda: retirement, lambda: Catalog({}), lambda: AdmittingServiceEvidence(), RootStructureGuard(lambda: Catalog({}), lambda: ScriptedFiles(HERE), lambda: MemoryOrgSettings(ORG_MD), lambda: OrgPaths(HERE)))


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


# ------------------------------------------------------------------------------------------------------------ define_service (ROOT-NEW-SERVICE)


def root_new_service(owner: str, name: str) -> str:
    return (
        f"refused: {owner} offers no service `{name}`, and a new service changes the organization, so the user approves it in a plan: "
        'propose_org(blueprint=<an extension with add_services>, extend="current"). A change to an existing service\'s criteria stays '
        "define_service with the user's words. Nothing was written."
    )


def services(offered: dict[str, list[str]]) -> tuple[ServiceTools, Commands]:
    """The service tools of root, a manager and an owner over a scripted organization where ``offered`` services exist, behind the refusing guard."""
    from pathlib import Path

    from hirearchy.mcp_server._instructions import InstructionText
    from hirearchy.mcp_server._tools_services import DirectoryServiceRoles
    from hirearchy.mcp_server.testing import MemoryBinding, agents_in

    agents, commands = agents_in("ceo", "ceo/eng", "ops"), Commands()
    roles = DirectoryServiceRoles(InstructionText(MemoryBinding(Path("/o"), exists=True)), lambda: agents, lambda: agents, lambda: Catalog(offered))
    guard = RootStructureGuard(lambda: Catalog(offered), lambda: ScriptedFiles(HERE), lambda: MemoryOrgSettings(ORG_MD), lambda: OrgPaths(HERE))
    return ServiceTools(
        roles, lambda: ScriptedReports("SERVICES"), lambda: commands, lambda: HeldBudgets({"ceo": 5}), lambda: ScriptedSteps(), guard,
    ), commands


def test_root_define_service_of_a_new_name_is_root_new_service() -> None:
    group, commands = services({"ceo": ["other"], "ops": ["brief"]})  # (`brief` exists, but at ops: ceo offers no such service)
    server = serve(group, ROOT)
    assert root_new_service("ceo", "brief") in fails(server, "define_service", owner="ceo", name="brief", description="d", acceptance=["a"], budget=3)
    assert root_new_service("ceo/eng", "x") in fails(server, "define_service", owner=" /ceo/eng/ ", name="x")
    assert commands.calls == []


def test_root_define_service_docstring_points_to_the_extension() -> None:
    group, _ = services({})
    text = " ".join(described(serve(group, ROOT))["define_service"].split())
    assert text.startswith(
        "Amend the contract of a service of a top-level agent. A new service changes the organization, so the user approves it in a plan: "
        'propose_org(blueprint=<an extension with add_services>, extend="current"); a first definition here is refused. '
        "You are the client: the contract is yours; the owner cannot change it. owner: the report. name: lowercase-dashed, "
        "unique among your reports' services. AMENDMENT (the service exists): pass only what changes, the rest stays."
    )
    assert "FIRST definition needs" not in text and "CHANGING THE CRITERIA (you, root)" in text and "words=<their request, verbatim> alone" in text
    agent = " ".join(described(serve(services({})[0], "ceo"))["define_service"].split())
    assert agent.startswith("Define a standing service of one of your direct reports (root: a top-level agent), or amend its contract.")
    assert "FIRST definition needs description (one line)" in agent


def test_root_amendments_are_unchanged() -> None:
    """GREEN when written: a service the owner offers is amended as before, with the user's words."""
    group, commands = services({"ceo": ["brief"]})
    assert call(serve(group, ROOT), "define_service", owner="ceo", name="brief", add_acceptance=["Cite"], answers="m1", about="C1", words="yes") == "defined brief"
    ((kind, args, fields),) = commands.calls
    assert kind == "define_service" and args == (ROOT, "ceo", "brief") and fields["words"] == "yes" and fields["add_acceptance"] == ["Cite"]


def test_an_agents_define_service_of_a_new_name_is_unchanged() -> None:
    """GREEN when written: an agent client's first definition for its own report (nested) is not refused (design 13)."""
    group, commands = services({})
    assert call(serve(group, "ceo"), "define_service", owner="ceo/eng", name="brief", description="d") == "defined brief"
    assert len(commands.calls) == 1


# ------------------------------------------------------------------------------------------------------------ write (ROOT-CHARTER, ROOT-DEPTH)

ROOT_CHARTER = (
    "refused: a charter changes through a plan the user approves: one line with add_charter_lines, hiring limits with limits, in "
    'propose_org(blueprint=<an extension>, extend="current"). Nothing was written.'
)
ROOT_DEPTH = (
    "refused: max_depth bounds the organization's structure, so the user approves a change of it in a plan: limits: [{org: max_depth, value: N}] in "
    'propose_org(blueprint=<an extension>, extend="current"). Nothing was written.'
)


def files(org_md: str = ORG_MD) -> tuple[FileTools, ScriptedFiles]:
    """The file tools over scripted files, with ORG.md holding ``org_md``, behind the refusing guard."""
    written = ScriptedFiles(HERE)
    guard = RootStructureGuard(lambda: Catalog({}), lambda: written, lambda: MemoryOrgSettings(org_md), lambda: OrgPaths(HERE))
    return FileTools(lambda: StaticNaming(), lambda: written, lambda: written, lambda: OrgPaths(HERE), guard), written


def test_root_write_of_an_agent_md_is_root_charter() -> None:
    group, written = files()
    server = serve(group, ROOT)
    for path in ("ceo/AGENT.md", str(HERE / "ceo" / "AGENT.md")):
        assert ROOT_CHARTER in fails(server, "write", path=path, content="---\nrole: Chief\n---\nNew body.\n")
    assert ROOT_CHARTER in fails(server, "write", path="ceo/AGENT.md", content="One more line.\n", append=True)
    assert written.log.of("write_noted") == []


def test_root_write_of_org_md_changing_max_depth_is_root_depth() -> None:
    group, written = files()
    server = serve(group, ROOT)
    assert ROOT_DEPTH in fails(server, "write", path="ORG.md", content="---\nmax_depth: 6\neffort: high\n---\nThe rules.\n")
    assert ROOT_DEPTH in fails(server, "write", path="ORG.md", content="---\nmax_depth: 3\n---\nThe rules.\n")
    deeper, written_deeper = files("---\nmax_depth: 6\n---\nThe rules.\n")
    assert ROOT_DEPTH in fails(serve(deeper, ROOT), "write", path="ORG.md", content="---\neffort: high\n---\nThe rules.\n")  # (a missing key is the default, 4)
    assert written.log.of("write_noted") == [] == written_deeper.log.of("write_noted")


def test_root_write_of_org_md_changing_nothing_structural_keeps_todays_floor_check() -> None:
    """GREEN when written: ORG.md's other settings and its rules are root's to write (the writer's floor check stays the only one)."""
    group, written = files()
    server = serve(group, ROOT)
    same = "---\nmax_depth: 4\neffort: xhigh\n---\nNew rules.\n"
    assert call(server, "write", path="ORG.md", content=same) == "wrote ORG.md (organization file)"
    assert call(server, "write", path="ORG.md", content="\nA line of rules.\n", append=True) == "wrote ORG.md (organization file)"
    assert call(server, "write", path="notes/a.md", content="x") == "wrote notes/a.md (organization file)"
    broken, written_broken = files("---\nmax_depth: [unclosed\n---\n")  # (ORG.md that cannot be parsed: root can still repair it)
    assert call(serve(broken, ROOT), "write", path="ORG.md", content="---\nmax_depth: 9\n---\nRepaired.\n") == "wrote ORG.md (organization file)"
    assert len(written.log.of("write_noted")) == 3 and len(written_broken.log.of("write_noted")) == 1


def test_an_agents_write_of_a_charter_is_unchanged() -> None:
    """GREEN when written: an agent's charter writes keep the writer's rules (design 6.6 adds CHARTER-PLAN and CHARTER-ADDED there)."""
    group, written = files()
    assert call(serve(group, "ceo"), "write", path="ceo/eng/AGENT.md", content="---\nrole: E\n---\nB.\n") == "wrote ceo/eng/AGENT.md (organization file)"
    assert len(written.log.of("write_noted")) == 1
