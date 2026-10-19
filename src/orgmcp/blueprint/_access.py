"""``PolicyAccessReport``: what the runtime lets an agent reach with kiro's file tools, asked of the same policy that writes the profile."""

from __future__ import annotations

from collections.abc import Collection, Iterable
from pathlib import Path
from typing import cast

from ..kiro import ConfinementPolicy
from ._protocols import AccessReport
from ._shapes import AccessFacts
from ._view import mapping_or_empty
from .api import Agent

ORG_PLACEHOLDER = Path("/orgmcp-org-root")  # stands for the org directory, which does not exist at plan time


class PolicyAccessReport(AccessReport):
    def __init__(self, policy: ConfinementPolicy) -> None:
        self._policy = policy

    def org_files_readable(self, a: Agent) -> bool:
        """Can this agent open files in the organization (its own and its teammates' ``work/``) with the tools it holds?

        Without built-in ``read`` it uses orgmcp's ``read``. With it, the built-in ``read`` is the only ``read`` the model
        sees (it hides orgmcp's, same short name), so the answer comes from what the runtime really allows it: the same
        confinement policy that writes the profile, asked about a stand-in org directory.
        """
        if "read" not in a.tools:
            return True
        ws = Path(a.workspace) if a.workspace else None
        _, settings = self._policy.file_confinement(ORG_PLACEHOLDER, list(a.tools), ws, [Path(p) for p in a.inputs])
        rule = mapping_or_empty(settings.get("read"))
        root = str(ORG_PLACEHOLDER)
        denied = any(root == d or root.startswith(d.removesuffix("/**").rstrip("/") + "/") for d in cast("Iterable[str]", rule.get("deniedPaths", [])))
        return f"{root}/**" in cast("Collection[str]", rule.get("allowedPaths", [])) and not denied

    def facts(self, a: Agent) -> AccessFacts:
        """What the runtime lets this agent reach with kiro's file tools: the ONE computation behind both the technical
        ``Access:`` line (``line``, in the details and each agent's prompt) and the plain-words line of the PLAN FOR YOU,
        so the user is shown exactly what is enforced. Mirrors the confinement policy: ``write`` only under the workspace,
        ``read`` in workspace + inputs + the organization (read-only), ``shell`` not confined.
        """
        read = "read" in a.tools
        return {
            "write": ("write" in a.tools, a.workspace),                 # (granted, the only folder it may change)
            "read": (read, [b for b in (a.workspace, *a.inputs) if b]),  # (granted, every folder kiro lets it read)
            "org": self.org_files_readable(a),                           # can open the organization's own files (any tool)
            "inputs": list(a.inputs),                                    # read-only folders
            "inputs_via_orgmcp": bool(a.inputs) and not read,            # inputs it can only open with orgmcp `read`
            "shell": ("shell" in a.tools, a.workspace),                  # (granted, where it is told to stay; not enforced)
            "web": [t for t in a.tools if t in ("web_search", "web_fetch")],
        }

    def line(self, a: Agent) -> str:
        """One line on what the runtime lets this agent reach with kiro's file tools (and what it only instructs)."""
        f = self.facts(a)
        bits = []
        if f["write"][0]:
            bits.append(f"kiro write only in {a.workspace}" if a.workspace else "kiro write nowhere")
        if f["read"][0]:
            bases = f["read"][1]
            org = " and in the organization's own files (read-only)" if f["org"] else ""
            bits.append("kiro read only in " + ", ".join(bases) + org if bases else ("kiro read only in the organization's own files (read-only)" if f["org"] else "kiro read nowhere"))
        if f["inputs_via_orgmcp"]:
            bits.append("read-only inputs (orgmcp read): " + ", ".join(f["inputs"]))
        if f["shell"][0]:
            bits.append("shell NOT confined (instructed only)")
        return "; ".join(bits)
