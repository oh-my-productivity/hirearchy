"""The organization's files: ``read`` and ``write``, called ``org_read`` / ``org_write`` for an agent that holds the built-in of the same name."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..access import ToolNaming
from ..kernel import ROOT, OrgLayout, Provider
from ..orgfiles import OrgFileReader, OrgFileWriter
from ._ports import ToolGroup

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


class FileTools(ToolGroup):
    def __init__(
        self, naming: Provider[ToolNaming], reader: Provider[OrgFileReader], writer: Provider[OrgFileWriter], layout: Provider[OrgLayout],
    ) -> None:
        self._naming = naming
        self._reader = reader
        self._writer = writer
        self._layout = layout

    def register(self, mcp: FastMCP, me: str) -> None:
        # kiro exposes MCP tools by their plain names, so a built-in `read`/`write` in the agent's charter would shadow
        # orgmcp's tool of the same name: such an agent gets them as `org_read` / `org_write` (studies/F2-tool-names).
        names = self._naming().tool_names(me) if me != ROOT else {"read": "read", "write": "write"}

        def read(path: str = ".") -> str:
            return self._reader().read(path, me)

        def write(path: str, content: str, append: bool = False) -> str:
            p, note = self._writer().write_noted(me, path, content, append=append)
            return f"wrote {self._layout().rel(p)} (organization file)" + (f". {note}" if note else "")

        rn, wn = names["read"], names["write"]
        hide_read = (
            " kiro's built-in `read` has the name `read` (it reads the workspace, inputs and, by absolute path, the "
            f"organization); this tool is the organization's relative-path reader, called `{rn}` for you." if rn != "read" else ""
        )
        hide_write = (
            f" kiro's built-in `write` has the name `write`; this orgmcp tool is called `{wn}` for you." if wn != "write" else ""
        )
        mcp.tool(name=rn, description=f"""The ORGANIZATION's read tool (kiro shows it as @orgmcp/{rn}; not kiro's built-in `read`, which reads the
        workspace).{hide_read} Reads a file (with word count and modification time) or lists a directory in the organization. Paths
        are relative to the org root, e.g. "ceo/writer/work/brief.md". Outside the organization only ABSOLUTE paths work,
        and only inside your workspace, your read-only inputs, or the workspace of an agent in your team (to verify
        what your reports made); anything else is refused.""")(read)
        mcp.tool(name=wn, description=f"""Write an ORGANIZATION file (kiro shows this tool as @orgmcp/{wn}; it is NOT kiro's built-in `write`, which
        writes the workspace).{hide_write} Use it for your memory, notes and artifacts inside your own org directory. Paths are
        relative to the org root, like every path here, so they start with your address: e.g. "<you>/MEMORY.md" or
        "<you>/work/plan.md".

        You may also rewrite a direct report's charter ("<you>/<name>/AGENT.md"). Inboxes, logs and your own
        charter are managed by the runtime; use send/delegate/report to communicate. A charter rewrite keeps every
        frontmatter key (tools, inputs, model, ...) that your new text does not set; the reply lists what was kept
        and what changed.
        """)(write)
