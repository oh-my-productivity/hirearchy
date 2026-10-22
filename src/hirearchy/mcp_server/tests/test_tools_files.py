"""``FileTools``: read and write, called ``org_read`` / ``org_write`` for an agent that holds the built-in of the same name, with the descriptions that say so."""

from __future__ import annotations

from pathlib import Path

from hirearchy.kernel import ROOT, OrgPaths
from hirearchy.mcp_server._tools_files import FileTools
from hirearchy.mcp_server.testing import ScriptedFiles, StaticNaming

from ._support import call, described, names, serve

HERE = Path("/memory/org")


def tools(files: ScriptedFiles | None = None, shadowed: dict[str, tuple[str, str]] | None = None) -> tuple[FileTools, ScriptedFiles]:
    files = files or ScriptedFiles(HERE, text="THE TEXT")
    return FileTools(lambda: StaticNaming(shadowed), lambda: files, lambda: files, lambda: OrgPaths(HERE)), files


def test_the_plain_names_for_root_and_for_an_agent_without_the_built_ins() -> None:
    group, _ = tools()
    assert names(serve(group, ROOT)) == ["read", "write"] and names(serve(group, "ceo")) == ["read", "write"]


def test_an_agent_that_holds_a_built_in_gets_the_org_names_and_the_description_says_why() -> None:
    group, _ = tools(shadowed={"rw": ("org_read", "org_write"), "rd": ("org_read", "write")})
    server = serve(group, "rw")
    assert names(server) == ["org_read", "org_write"]
    out = described(server)
    assert "kiro's built-in file tools (`read_file`, `list_directory`) read the workspace" in out["org_read"] and "called `org_read` for you" in out["org_read"]
    assert "`delete_file`; this hirearchy tool is called `org_write` for you" in out["org_write"]
    only_read = described(serve(group, "rd"))
    assert "called `org_read` for you" in only_read["org_read"] and "called" not in only_read["write"].split("workspace).")[1][:60]


def test_root_is_never_renamed() -> None:
    group, _ = tools(shadowed={ROOT: ("org_read", "org_write")})
    assert names(serve(group, ROOT)) == ["read", "write"]


def test_read_reads_as_the_caller() -> None:
    group, files = tools()
    assert call(serve(group, "ceo"), "read", path="ceo/work/a.md") == "THE TEXT"
    assert call(serve(group, "ceo"), "read") == "THE TEXT"
    assert files.log.of("read") == [(("ceo/work/a.md", "ceo"), {}), ((".", "ceo"), {})]


def test_write_says_where_in_the_organization_it_wrote() -> None:
    group, files = tools()
    assert call(serve(group, "ceo"), "write", path="ceo/work/n.md", content="x") == "wrote ceo/work/n.md (organization file)"
    assert files.log.of("write_noted") == [(("ceo", "ceo/work/n.md", "x", False), {})]


def test_write_adds_the_note_of_a_charter_rewrite() -> None:
    group, _ = tools(ScriptedFiles(HERE, note="kept: tools"))
    out = call(serve(group, "ceo"), "write", path="ceo/eng/AGENT.md", content="x", append=True)
    assert out == "wrote ceo/eng/AGENT.md (organization file). kept: tools"
