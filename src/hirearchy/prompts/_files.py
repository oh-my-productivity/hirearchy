"""``FilesGuide``: the "Files" part of an agent's state (moved from ``Org._files_lines``)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import cast

from ..access import AccessScopes, ToolNaming
from ..kernel import OrgLayout
from ._ports import FilesLines


class FilesGuide(FilesLines):
    def __init__(self, scopes: AccessScopes, naming: ToolNaming, layout: OrgLayout) -> None:
        self._scopes = scopes
        self._naming = naming
        self._root = layout.root

    def lines(self, addr: str, meta: Mapping[str, object]) -> list[str]:
        """The "Files" part of an agent's state: where each kind of path points, and which tool reaches it.

        The hirearchy tools are reached through kiro's ``tool_load`` and ``tool_call`` as ``hirearchy::<tool>``; kiro's
        built-ins have their own ids (``read_file``, ``list_directory``, ``fs_write``, ``execute_bash``, ...) and reach the
        workspace (``read`` also the org, by absolute path). A built-in ``read``/``write`` hides the hirearchy tool of the
        same name, which is then called ``org_read``/``org_write`` (see :meth:`tool_names`): the agent is told which
        name it has. kiro's tools start in an empty scratch directory, so every path in them is absolute. Empty for an
        agent with no workspace, no inputs and no built-in tools.
        """
        ws, inputs = self._scopes.workspace_of(addr), self._scopes.inputs_of(addr)
        tools = set(cast("Iterable[str]", meta.get("tools") or []))
        builtin = sorted(tools & {"read", "write", "shell"})
        if ws is None and not inputs and not builtin:
            return []
        names = self._naming.tool_names(addr)
        rn, wn = names["read"], names["write"]
        lines = [
            "- Files:",
            "  - hirearchy tools (load them with `tool_load`, then call them with `tool_call` and tool_id `hirearchy::<name>`, "
            f"e.g. `hirearchy::{wn}`, `hirearchy::{rn}`): paths are relative to the org root; your notes and memory: "
            f"`{addr}/MEMORY.md`, `{addr}/work/` (hirearchy `{wn}` only).",
        ]
        if builtin:
            kinds = ", ".join(f"`{t}`" for t in builtin)
            if not tools & {"read", "write"}:  # only `shell`: no name clash
                reach = "they work on the workspace only and never reach the org. "
                how = "`hirearchy::write` and read with `hirearchy::read`, never with the shell."
                intro = "are not hirearchy's tools (kiro's shell tool is `execute_bash`)"
            else:
                reach = (
                    "they write and run only in the workspace and never change the org. " if "read" in tools
                    else "they work on the workspace only and never reach the org. "
                )
                intro = "are not hirearchy's tools"
                if "write" in tools:
                    how = (
                        f"`hirearchy::{wn}`, never with kiro's file tools: kiro's built-in file tools are `fs_write`, "
                        "`str_replace`, `fs_append` and `delete_file`; the hirearchy write tool is "
                        f"`hirearchy::{wn}` for you: use it for MEMORY.md and org files "
                        f"(wherever ORG.md says `@hirearchy/write`, use `hirearchy::{wn}`)."
                    )
                else:
                    how = "`hirearchy::write`, never with kiro's tools."
                if "read" in tools:
                    how += (
                        " Your `read` is kiro's built-in (`read_file`, `list_directory`): it reads org files too, but only by "
                        f"ABSOLUTE path, `{self._root}/<path in the org>` (a relative path starts in an empty scratch directory, "
                        f"not in the org); the hirearchy read tool is `hirearchy::{rn}` for you (relative org paths; wherever "
                        f"ORG.md says `@hirearchy/read`, use `hirearchy::{rn}`)."
                    )
                else:
                    how += " Read org files with `hirearchy::read`."
            lines.append(
                f"  - Do not mix up the two kinds of tools: kiro's built-in {kinds} {intro}: {reach}"
                f"Org files (`{addr}/MEMORY.md`, `{addr}/work/`, anything under `{addr}/`) are written with " + how
            )
        if ws is not None:
            search = ""
            if "read" in tools:
                search = (
                    " kiro's `grep_search` and `file_search` cannot search the workspace (they are refused): find files with "
                    "`list_directory` (one level at a time) and `read_file` on absolute paths"
                    + (f", or with `grep -r` / `find` on `{ws}`" if "shell" in tools else "") + "."
                )
            lines.append(
                f"  - Workspace (kiro read/write/shell): `{ws}`. kiro tools start in an empty scratch directory, not here: give "
                f"them ABSOLUTE paths under `{ws}` (a relative path, and the shell's starting directory, point at the scratch "
                "directory, which is emptied before every run)." + search
            )
        else:
            lines.append("  - You have no workspace: kiro tools start in an empty scratch directory and cannot write.")
        if inputs:
            lines.append(
                f"  - Read-only inputs (kiro's `read_file` or `hirearchy::{rn}`, by absolute path): "
                + ", ".join(f"`{p}`" for p in inputs) + ". Never modify them."
            )
        lines.append(
            "  - Never create org files (MEMORY.md, `<address>/...`) in the workspace. Report workspace artifacts by "
            "absolute path."
        )
        if tools & {"read", "write"}:
            lines.append("  - kiro `write` is limited to the workspace and kiro `read` to workspace + inputs + the organization (read-only); other paths are refused.")
        if "write" in tools and ws is not None:
            lines.append(
                "  - kiro's file tools cannot create or change `.kiro/`, `.git/` or `.vscode/` folders or `AGENTS.md` files "
                "anywhere in the workspace (refused)." + (" `git` commands run with the shell are not affected." if "shell" in tools else "")
            )
        if "shell" in tools:
            lines.append(
                "  - You have `shell`, which the runtime cannot confine: use it only inside your workspace; never write "
                "to inputs, to the org directory, or anywhere else."
            )
        return lines
