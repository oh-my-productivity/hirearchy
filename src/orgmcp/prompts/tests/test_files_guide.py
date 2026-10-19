"""``FilesGuide``: the "Files" part of the state of an agent, for every shape of tools, workspace and inputs.

The texts are written out here on purpose: they are part of the prompt (GOLDEN ``prompts/files_block_variants``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.access.testing import StaticAccess
from orgmcp.kernel import OrgPaths
from orgmcp.prompts._files import FilesGuide
from orgmcp.prompts._ports import FilesLines

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-prompts")

WORKSPACE_LINE = "  - Workspace (kiro read/write/shell, and the working directory of kiro tools): `{ws}`; relative paths in kiro tools resolve there."
INPUTS_LINE = "  - Read-only inputs (kiro `read` or orgmcp `{read}` by absolute path): `{inputs}`. Never modify them."
NEVER_LINE = "  - Never create org files (MEMORY.md, `<address>/...`) in the workspace. Report workspace artifacts by absolute path."
LIMITS_LINE = "  - kiro `write` is limited to the workspace and kiro `read` to workspace + inputs + the organization (read-only); other paths are refused."
SHELL_LINE = (
    "  - You have `shell`, which the runtime cannot confine: use it only inside your workspace; never write to inputs, to the org directory, "
    "or anywhere else."
)


class Shapes:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.ws, self.inputs = self.root / "ws", self.root / "in"
        self.ws.mkdir()
        self.inputs.mkdir()
        self.access = StaticAccess(self.root)
        self.guide: FilesLines = FilesGuide(self.access, self.access, OrgPaths(self.root))

    def lines(self, addr: str, **meta: object) -> list[str]:
        full = {"role": "Worker", **meta}
        self.access.put_agent(addr, full)
        return self.guide.lines(addr, full)


@pytest.fixture
def s(tmp_path: Path) -> Shapes:
    return Shapes(tmp_path)


def test_an_agent_with_no_workspace_no_inputs_and_no_built_in_tools_has_no_files_part(s: Shapes) -> None:
    assert s.lines("bare") == []
    assert s.lines("tools-only-orgmcp", tools=[]) == []


def test_shell_only(s: Shapes) -> None:
    assert s.lines("sh", tools=["shell"], workspace=str(s.ws), inputs=[str(s.inputs)]) == [
        "- Files:",
        "  - orgmcp tools (shown as `@orgmcp/write`, `@orgmcp/read`, ...): paths are relative to the org root; your notes and memory: "
        "`sh/MEMORY.md`, `sh/work/` (orgmcp `write` only).",
        "  - Do not mix up the two kinds of tools: kiro's built-in `shell` have the same short names as orgmcp's but are not the same tools: they "
        "work on the workspace only and never reach the org. Org files (`sh/MEMORY.md`, `sh/work/`, anything under `sh/`) are written with "
        "`@orgmcp/write` and read with `@orgmcp/read`, never with the built-in `write`/`read`.",
        WORKSPACE_LINE.format(ws=s.ws), INPUTS_LINE.format(read="read", inputs=s.inputs), NEVER_LINE, SHELL_LINE,
    ]


def test_read_only_names_the_orgmcp_read_tool_org_read_and_the_absolute_path_of_the_org(s: Shapes) -> None:
    assert s.lines("rd", tools=["read"], workspace=str(s.ws), inputs=[str(s.inputs)]) == [
        "- Files:",
        "  - orgmcp tools (shown as `@orgmcp/write`, `@orgmcp/org_read`, ...): paths are relative to the org root; your notes and memory: "
        "`rd/MEMORY.md`, `rd/work/` (orgmcp `write` only).",
        "  - Do not mix up the two kinds of tools: kiro's built-in `read` are not orgmcp's tools: they write and run only in the workspace and never "
        "change the org. Org files (`rd/MEMORY.md`, `rd/work/`, anything under `rd/`) are written with `@orgmcp/write`, never with the built-in "
        f"`write`. Your `read` is kiro's built-in: it reads org files too, but only by ABSOLUTE path, `{s.root}/<path in the org>` (a relative "
        "path starts in your working directory); the orgmcp read tool is `@orgmcp/org_read` for you (relative org paths; wherever ORG.md says "
        "`@orgmcp/read`, use that name).",
        WORKSPACE_LINE.format(ws=s.ws), INPUTS_LINE.format(read="org_read", inputs=s.inputs), NEVER_LINE, LIMITS_LINE,
    ]


def test_write_only_names_the_orgmcp_write_tool_org_write(s: Shapes) -> None:
    assert s.lines("wr", tools=["write"], workspace=str(s.ws), inputs=[str(s.inputs)]) == [
        "- Files:",
        "  - orgmcp tools (shown as `@orgmcp/org_write`, `@orgmcp/read`, ...): paths are relative to the org root; your notes and memory: "
        "`wr/MEMORY.md`, `wr/work/` (orgmcp `org_write` only).",
        "  - Do not mix up the two kinds of tools: kiro's built-in `write` are not orgmcp's tools: they work on the workspace only and never reach "
        "the org. Org files (`wr/MEMORY.md`, `wr/work/`, anything under `wr/`) are written with `@orgmcp/org_write`, never with the built-in "
        "`write`: kiro's built-in `write` has the name `write`; the orgmcp write tool is `@orgmcp/org_write` for you: use it for MEMORY.md and org "
        "files (wherever ORG.md says `@orgmcp/write`, use that name). Read org files with `@orgmcp/read`.",
        WORKSPACE_LINE.format(ws=s.ws), INPUTS_LINE.format(read="read", inputs=s.inputs), NEVER_LINE, LIMITS_LINE,
    ]


def test_read_and_write_say_both_and_list_the_kinds_in_name_order(s: Shapes) -> None:
    lines = s.lines("rw", tools=["write", "read", "shell"], workspace=str(s.ws), inputs=[str(s.inputs)])
    assert lines[2].startswith("  - Do not mix up the two kinds of tools: kiro's built-in `read`, `shell`, `write` are not orgmcp's tools: ")
    assert "they write and run only in the workspace and never change the org. " in lines[2]
    assert "are written with `@orgmcp/org_write`, never with the built-in `write`: " in lines[2] and "ABSOLUTE path, `" + str(s.root) + "/<path in the org>`" in lines[2]
    assert lines[-2:] == [LIMITS_LINE, SHELL_LINE]


def test_a_workspace_without_built_in_tools_has_no_mix_up_warning(s: Shapes) -> None:
    lines = s.lines("ws-only", tools=[], workspace=str(s.ws), inputs=[str(s.inputs)])
    assert lines == [
        "- Files:",
        "  - orgmcp tools (shown as `@orgmcp/write`, `@orgmcp/read`, ...): paths are relative to the org root; your notes and memory: "
        "`ws-only/MEMORY.md`, `ws-only/work/` (orgmcp `write` only).",
        WORKSPACE_LINE.format(ws=s.ws), INPUTS_LINE.format(read="read", inputs=s.inputs), NEVER_LINE,
    ]


def test_an_agent_without_a_workspace_is_told_that_kiro_tools_start_in_its_directory_and_cannot_write(s: Shapes) -> None:
    lines = s.lines("no-ws", tools=["read"], inputs=[str(s.inputs)])
    assert "  - You have no workspace: kiro tools start in your org directory (`no-ws/`) and cannot write." in lines
    assert not [line for line in lines if line.startswith("  - Workspace")]


def test_inputs_alone_make_the_part_and_several_inputs_are_comma_separated(s: Shapes) -> None:
    other = s.root / "more"
    other.mkdir()
    lines = s.lines("in-only", inputs=[str(s.inputs), str(other)])
    assert lines[-2] == INPUTS_LINE.format(read="read", inputs=f"{s.inputs}`, `{other}")
    assert lines[-1] == NEVER_LINE


def test_a_charter_with_a_tools_entry_that_is_not_a_list_is_an_agent_with_none(s: Shapes) -> None:
    assert FilesGuide(s.access, s.access, OrgPaths(s.root)).lines("bare", {"tools": None}) == []


def test_the_meta_it_is_given_decides_not_the_charter_on_disk(s: Shapes) -> None:
    s.access.put_agent("x", {"role": "Worker", "tools": ["shell"], "workspace": str(s.ws)})
    assert s.guide.lines("x", {"role": "Worker"})[0:1] == ["- Files:"]  # the workspace comes from the access port...
    assert not [line for line in s.guide.lines("x", {"role": "Worker"}) if "cannot confine" in line]  # ...the tools from the meta
