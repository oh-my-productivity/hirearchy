"""``PlainAccessWords``: what an agent may touch, in the words of the block for the user."""

from __future__ import annotations

from ._plan_texts import TOOL_WORDS
from ._protocols import AccessReport, AccessWording
from .api import Agent


class PlainAccessWords(AccessWording):
    def __init__(self, access: AccessReport) -> None:
        self._access = access

    def describe(self, a: Agent) -> str:
        """What the agent may touch, in plain words: the same facts as the ``Access:`` line (``access_facts``)."""
        f = self._access.facts(a)
        ws = a.workspace
        bits: list[str] = []
        if f["web"]:
            bits.append("can " + " and ".join(TOOL_WORDS[t] for t in f["web"]))
        if f["read"][0]:
            bases = f["read"][1]
            ins = f["inputs"]
            org = " and the organization's own files" if f["org"] else ""
            if f["write"][0] and ws:
                bits.append("can read files in " + ", ".join(bases) + (f" ({', '.join(ins)} read-only)" if ins else "") + org)
            elif bases:
                bits.append("can read files only in " + ", ".join(bases) + org)
            else:
                bits.append("can read no files outside the organization")
        elif f["inputs_via_orgmcp"]:
            bits.append("can read " + ", ".join(f["inputs"]) + " through the organization's read tool")
        if f["write"][0]:
            bits.append(f"changes files only in {ws}" if ws else "changes no files (no workspace)")
        if f["shell"][0]:
            bits.append("can run commands, which are NOT confined: it is told to stay in "
                        + (str(ws) if ws else "its own folder") + ", but nothing enforces that")
        if not f["write"][0] and not f["shell"][0]:
            bits.append("cannot change your files")
        lead = "directs the team; does not produce the work itself" if (a.kind == "manager" or a.children) else ""
        text = "; ".join(bits)
        return f"{lead}; {text}" if lead and text and text != "cannot change your files" else (lead or text)
