"""Every path to a structural change is bounded (design 13; owner question Q3).

What this pins: (1) root's MCP ``hire``, ``retire``, ``define_service`` of a new service and ``write`` of an ``AGENT.md`` or of a change of ORG.md's
``max_depth`` raise the ``ROOT-*`` refusals, over the real server of a real organization; (2) no MCP module passes the arguments that mark a call as
approved (``approved``, ``kind``, ``approved_in``) to ``hire``, ``define_service``, ``retire_team`` or ``retire_service``: only the plan appliers do, after the
user's yes (``test_hire_approval.py`` pins the same for ``approved``); (3) the added section of a charter is written by the extension applier alone.
A new MCP tool that reaches a structural change, or a second writer of the section, fails here.
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path

import pytest

from hirearchy.app import Org

from .paths import SRC

APPROVED = {"approved", "kind", "approved_in"}


@pytest.fixture
def org(tmp_path: Path) -> Org:
    made = Org.init(tmp_path / "org", "mission")
    made.hire("root", "ceo", "Chief", "Run it.", can_hire=True, max_children=2)
    return made


def refusal(org: Org, tool: str, **arguments: object) -> str:
    from testkit.mcp_server_world import build_server

    with pytest.raises(Exception) as info:
        asyncio.run(build_server(org, "root").call_tool(tool, arguments))
    return str(info.value)


def test_roots_hire_retire_charter_write_and_new_service_raise_the_root_refusals(org: Org) -> None:
    org_md = (org.root / "ORG.md").read_text(encoding="utf-8")
    charter = (org.root / "ceo" / "AGENT.md").read_text(encoding="utf-8")
    assert refusal(org, "hire", name="eng", role="Engineer", charter="Build.").startswith("Error executing tool hire: refused: a new agent changes the organization")
    assert "refused: retiring ceo changes the organization" in refusal(org, "retire", name="ceo", reason="r")
    assert "refused: ceo offers no service `brief`, and a new service changes the organization" in refusal(
        org, "define_service", owner="ceo", name="brief", description="d", acceptance=["a"], budget=3)
    assert "refused: a charter changes through a plan the user approves" in refusal(org, "write", path="ceo/AGENT.md", content=charter + "\nMore.\n")
    deeper = org_md.replace("max_depth: 4", "max_depth: 5") if "max_depth: 4" in org_md else "---\nmax_depth: 5\n---\n" + org_md
    assert "refused: max_depth bounds the organization's structure" in refusal(org, "write", path="ORG.md", content=deeper)
    assert not (org.root / "ceo" / "eng").exists() and not (org.root / ".retired").exists() and not list(org.root.glob("**/services"))  # nothing was made
    assert org.agents() == ["ceo"] and org.service_names("ceo") == []
    assert (org.root / "ORG.md").read_text(encoding="utf-8") == org_md and (org.root / "ceo" / "AGENT.md").read_text(encoding="utf-8") == charter


def library_modules(package: str) -> list[tuple[str, ast.Module]]:
    """Every module of ``package`` outside its tests and ``testing.py`` fakes, parsed."""
    return [
        (path.relative_to(SRC).as_posix(), ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted((SRC / package).rglob("*.py")) if "tests" not in path.parts and path.name != "testing.py"
    ]


def calls_passing(tree: ast.Module, methods: set[str], keywords: set[str]) -> list[int]:
    """The lines of the calls of ``<anything>.<method>(...)`` that pass one of ``keywords``."""
    return [
        node.lineno for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in methods
        and any(k.arg in keywords for k in node.keywords)
    ]


def test_no_mcp_tool_passes_approved_kind_or_approved_in_to_hire_except_through_apply_org() -> None:
    """``apply_org`` hands the blueprint to the plan appliers (``BlueprintApplier``, ``ExtensionApplying``); no tool of ``mcp_server`` calls ``hire`` itself with
    the marks of an approved plan."""
    found = {rel: lines for rel, tree in library_modules("mcp_server") if (lines := calls_passing(tree, {"hire"}, APPROVED))}
    assert found == {}, f"an MCP module hires with the marks of an approved plan: {found}"


def test_no_mcp_tool_passes_approved_in_to_define_service_or_retire_team_except_through_apply_org() -> None:
    found = {
        rel: lines for rel, tree in library_modules("mcp_server")
        if (lines := calls_passing(tree, {"define_service", "retire_team", "retire_service", "retire"}, {"approved_in"}))
    }
    assert found == {}, f"an MCP module records the approval of a plan itself: {found}"
    for rel, tree in library_modules("mcp_server"):  # (and not positionally either: the retire tool calls retire_team(me, name, reason), three arguments)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "retire_team":
                assert len(node.args) <= 3 and not node.keywords, f"{rel}:{node.lineno} retire_team is called with more than (actor, name, reason)"


def test_only_the_extension_applier_writes_the_added_section() -> None:
    """``with_changes`` (the one function that writes the section ``## Added by your changes``) is called by the extension applier alone; a charter is
    rewritten (``rewrite_charter``) by the applier, its undo and the guarded writer of the files (an agent's rewrite, which design 6.6 forbids to touch the
    section)."""
    def called(name: str) -> set[str]:
        return {
            rel for package in sorted(p.name for p in SRC.iterdir() if p.is_dir() and p.name != "__pycache__") for rel, tree in library_modules(package)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) == name
        }

    assert called("with_changes") == {"blueprint/_extension_apply.py"}
    assert called("rewrite_charter") == {"blueprint/_extension_apply.py", "blueprint/_undo.py", "orgfiles/_writer.py"}
