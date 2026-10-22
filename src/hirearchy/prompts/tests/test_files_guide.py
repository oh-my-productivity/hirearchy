"""``FilesGuide``: the "Files" part of the state of an agent, for every shape of tools, workspace and inputs.

The texts are written out here on purpose: they are part of the prompt (GOLDEN ``prompts/files_block_variants``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.access.testing import StaticAccess
from hirearchy.kernel import OrgPaths
from hirearchy.prompts._files import FilesGuide
from hirearchy.prompts._ports import FilesLines


WORKSPACE_LINE = (
    "  - Workspace (kiro read/write/shell): `{ws}`. kiro tools start in an empty scratch directory, not here: give them ABSOLUTE paths under "
    "`{ws}` (a relative path, and the shell's starting directory, point at the scratch directory, which is emptied before every run)."
)
SEARCH_HINT = (
    " kiro's `grep_search` and `file_search` cannot search the workspace (they are refused): find files with `list_directory` "
    "(one level at a time) and `read_file` on absolute paths"
)
NO_WORKSPACE_LINE = "  - You have no workspace: kiro tools start in an empty scratch directory and cannot write."
INPUTS_LINE = "  - Read-only inputs (kiro's `read_file` or `hirearchy::{read}`, by absolute path): `{inputs}`. Never modify them."
NEVER_LINE = "  - Never create org files (MEMORY.md, `<address>/...`) in the workspace. Report workspace artifacts by absolute path."
LIMITS_LINE = "  - kiro `write` is limited to the workspace and kiro `read` to workspace + inputs + the organization (read-only); other paths are refused."
PROTECTED_LINE = "  - kiro's file tools cannot create or change `.kiro/`, `.git/` or `.vscode/` folders or `AGENTS.md` files anywhere in the workspace (refused)."
PROTECTED_SHELL = " `git` commands run with the shell are not affected."
SHELL_LINE = (
    "  - You have `shell`, which the runtime cannot confine: use it only inside your workspace; never write to inputs, to the org directory, "
    "or anywhere else."
)


def hirearchy_line(write: str, read: str, addr: str) -> str:
    return (
        "  - hirearchy tools (load them with `tool_load`, then call them with `tool_call` and tool_id `hirearchy::<name>`, "
        f"e.g. `hirearchy::{write}`, `hirearchy::{read}`): paths are relative to the org root; your notes and memory: "
        f"`{addr}/MEMORY.md`, `{addr}/work/` (hirearchy `{write}` only)."
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
    assert s.lines("tools-only-hirearchy", tools=[]) == []


def test_shell_only(s: Shapes) -> None:
    assert s.lines("sh", tools=["shell"], workspace=str(s.ws), inputs=[str(s.inputs)]) == [
        "- Files:",
        hirearchy_line("write", "read", "sh"),
        "  - Do not mix up the two kinds of tools: kiro's built-in `shell` are not hirearchy's tools (kiro's shell tool is `execute_bash`): they "
        "work on the workspace only and never reach the org. Org files (`sh/MEMORY.md`, `sh/work/`, anything under `sh/`) are written with "
        "`hirearchy::write` and read with `hirearchy::read`, never with the shell.",
        WORKSPACE_LINE.format(ws=s.ws), INPUTS_LINE.format(read="read", inputs=s.inputs), NEVER_LINE, SHELL_LINE,
    ]


def test_read_only_names_the_hirearchy_read_tool_org_read_and_the_absolute_path_of_the_org(s: Shapes) -> None:
    assert s.lines("rd", tools=["read"], workspace=str(s.ws), inputs=[str(s.inputs)]) == [
        "- Files:",
        hirearchy_line("write", "org_read", "rd"),
        "  - Do not mix up the two kinds of tools: kiro's built-in `read` are not hirearchy's tools: they write and run only in the workspace and never "
        "change the org. Org files (`rd/MEMORY.md`, `rd/work/`, anything under `rd/`) are written with `hirearchy::write`, never with kiro's "
        f"tools. Your `read` is kiro's built-in (`read_file`, `list_directory`): it reads org files too, but only by ABSOLUTE path, `{s.root}/<path in "
        "the org>` (a relative path starts in an empty scratch directory, not in the org); the hirearchy read tool is `hirearchy::org_read` for you "
        "(relative org paths; wherever ORG.md says `@hirearchy/read`, use `hirearchy::org_read`).",
        WORKSPACE_LINE.format(ws=s.ws) + SEARCH_HINT + ".",
        INPUTS_LINE.format(read="org_read", inputs=s.inputs), NEVER_LINE, LIMITS_LINE,
    ]


def test_write_only_names_the_hirearchy_write_tool_org_write(s: Shapes) -> None:
    assert s.lines("wr", tools=["write"], workspace=str(s.ws), inputs=[str(s.inputs)]) == [
        "- Files:",
        hirearchy_line("org_write", "read", "wr"),
        "  - Do not mix up the two kinds of tools: kiro's built-in `write` are not hirearchy's tools: they work on the workspace only and never reach "
        "the org. Org files (`wr/MEMORY.md`, `wr/work/`, anything under `wr/`) are written with `hirearchy::org_write`, never with kiro's file "
        "tools: kiro's built-in file tools are `fs_write`, `str_replace`, `fs_append` and `delete_file`; the hirearchy write tool is "
        "`hirearchy::org_write` for you: use it for MEMORY.md and org files (wherever ORG.md says `@hirearchy/write`, use `hirearchy::org_write`). "
        "Read org files with `hirearchy::read`.",
        WORKSPACE_LINE.format(ws=s.ws), INPUTS_LINE.format(read="read", inputs=s.inputs), NEVER_LINE, LIMITS_LINE, PROTECTED_LINE,
    ]


def test_read_and_shell_add_the_grep_and_find_hint_to_the_search_limitation(s: Shapes) -> None:
    lines = s.lines("rs", tools=["read", "shell"], workspace=str(s.ws))
    assert WORKSPACE_LINE.format(ws=s.ws) + SEARCH_HINT + f", or with `grep -r` / `find` on `{s.ws}`." in lines
    assert PROTECTED_LINE not in lines  # no write: line 10 is only for write + workspace


def test_the_search_limitation_needs_read_and_a_workspace(s: Shapes) -> None:
    assert WORKSPACE_LINE.format(ws=s.ws) in s.lines("sh2", tools=["shell"], workspace=str(s.ws))
    assert WORKSPACE_LINE.format(ws=s.ws) in s.lines("wr2", tools=["write"], workspace=str(s.ws))
    assert not [line for line in s.lines("rd2", tools=["read"], inputs=[str(s.inputs)]) if "grep_search" in line]


def test_the_protected_folders_line_is_only_for_write_with_a_workspace_and_has_a_shell_suffix(s: Shapes) -> None:
    assert PROTECTED_LINE in s.lines("p1", tools=["write"], workspace=str(s.ws))
    assert PROTECTED_LINE + PROTECTED_SHELL in s.lines("p2", tools=["write", "shell"], workspace=str(s.ws))
    assert not [line for line in s.lines("p3", tools=["write"], inputs=[str(s.inputs)]) if ".vscode" in line]  # no workspace
    assert not [line for line in s.lines("p4", tools=["shell"], workspace=str(s.ws)) if ".vscode" in line]


def test_no_line_names_a_v2_tool_or_the_old_working_directory(s: Shapes) -> None:
    for tools in (["shell"], ["read"], ["write"], ["read", "write", "shell"]):
        text = "\n".join(s.lines("v", tools=tools, workspace=str(s.ws), inputs=[str(s.inputs)]))
        assert "@hirearchy/" not in text.replace("`@hirearchy/read`, use", "").replace("`@hirearchy/write`, use", "")
        assert "working directory of kiro tools" not in text


def test_read_and_write_say_both_and_list_the_kinds_in_name_order(s: Shapes) -> None:
    lines = s.lines("rw", tools=["write", "read", "shell"], workspace=str(s.ws), inputs=[str(s.inputs)])
    assert lines[2].startswith("  - Do not mix up the two kinds of tools: kiro's built-in `read`, `shell`, `write` are not hirearchy's tools: ")
    assert "they write and run only in the workspace and never change the org. " in lines[2]
    assert "are written with `hirearchy::org_write`, never with kiro's file tools: " in lines[2] and "ABSOLUTE path, `" + str(s.root) + "/<path in the org>`" in lines[2]
    assert lines[-3:] == [LIMITS_LINE, PROTECTED_LINE + PROTECTED_SHELL, SHELL_LINE]


def test_a_workspace_without_built_in_tools_has_no_mix_up_warning(s: Shapes) -> None:
    lines = s.lines("ws-only", tools=[], workspace=str(s.ws), inputs=[str(s.inputs)])
    assert lines == [
        "- Files:",
        hirearchy_line("write", "read", "ws-only"),
        WORKSPACE_LINE.format(ws=s.ws), INPUTS_LINE.format(read="read", inputs=s.inputs), NEVER_LINE,
    ]


def test_an_agent_without_a_workspace_is_told_that_kiro_tools_start_in_an_empty_scratch_directory_and_cannot_write(s: Shapes) -> None:
    lines = s.lines("no-ws", tools=["read"], inputs=[str(s.inputs)])
    assert NO_WORKSPACE_LINE in lines
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
