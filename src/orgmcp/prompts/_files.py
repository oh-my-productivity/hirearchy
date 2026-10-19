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

        The orgmcp tools show up in kiro as ``@orgmcp/<tool>``; kiro's built-in ``read``/``write``/``shell`` reach the
        workspace (``read`` also the org, by absolute path). A built-in ``read``/``write`` hides the orgmcp tool of the
        same name, which is then called ``org_read``/``org_write`` (see :meth:`tool_names`): the agent is told which
        name it has. Empty for an agent with no workspace, no inputs and no built-in tools.
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
            f"  - orgmcp tools (shown as `@orgmcp/{wn}`, `@orgmcp/{rn}`, ...): paths are relative to the org root; your "
            f"notes and memory: `{addr}/MEMORY.md`, `{addr}/work/` (orgmcp `{wn}` only).",
        ]
        if builtin:
            kinds = ", ".join(f"`{t}`" for t in builtin)
            if not tools & {"read", "write"}:  # only `shell`: no name clash
                reach = "they work on the workspace only and never reach the org. "
                how = "`@orgmcp/write` and read with `@orgmcp/read`, never with the built-in `write`/`read`."
                intro = "have the same short names as orgmcp's but are not the same tools"
            else:
                reach = (
                    "they write and run only in the workspace and never change the org. " if "read" in tools
                    else "they work on the workspace only and never reach the org. "
                )
                intro = "are not orgmcp's tools"
                if "write" in tools:
                    how = (
                        f"`@orgmcp/{wn}`, never with the built-in `write`: kiro's built-in `write` has the name `write`; "
                        f"the orgmcp write tool is `@orgmcp/{wn}` for you: use it for MEMORY.md and org files "
                        "(wherever ORG.md says `@orgmcp/write`, use that name)."
                    )
                else:
                    how = "`@orgmcp/write`, never with the built-in `write`."
                if "read" in tools:
                    how += (
                        " Your `read` is kiro's built-in: it reads org files too, but only by ABSOLUTE path, "
                        f"`{self._root}/<path in the org>` (a relative path starts in your working directory); the orgmcp "
                        f"read tool is `@orgmcp/{rn}` for you (relative org paths; wherever ORG.md says `@orgmcp/read`, "
                        "use that name)."
                    )
                else:
                    how += " Read org files with `@orgmcp/read`."
            lines.append(
                f"  - Do not mix up the two kinds of tools: kiro's built-in {kinds} {intro}: {reach}"
                f"Org files (`{addr}/MEMORY.md`, `{addr}/work/`, anything under `{addr}/`) are written with " + how
            )
        if ws is not None:
            lines.append(
                f"  - Workspace (kiro read/write/shell, and the working directory of kiro tools): `{ws}`; relative "
                "paths in kiro tools resolve there."
            )
        else:
            lines.append(f"  - You have no workspace: kiro tools start in your org directory (`{addr}/`) and cannot write.")
        if inputs:
            lines.append(
                f"  - Read-only inputs (kiro `read` or orgmcp `{rn}` by absolute path): "
                + ", ".join(f"`{p}`" for p in inputs) + ". Never modify them."
            )
        lines.append(
            "  - Never create org files (MEMORY.md, `<address>/...`) in the workspace. Report workspace artifacts by "
            "absolute path."
        )
        if tools & {"read", "write"}:
            lines.append("  - kiro `write` is limited to the workspace and kiro `read` to workspace + inputs + the organization (read-only); other paths are refused.")
        if "shell" in tools:
            lines.append(
                "  - You have `shell`, which the runtime cannot confine: use it only inside your workspace; never write "
                "to inputs, to the org directory, or anywhere else."
            )
        return lines
