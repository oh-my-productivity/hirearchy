"""``KiroConfinementPolicy``: the V3 ``tools`` selector and permission rules of one agent's grant (docs/design/kiro-runtime-v3.md 4.2-4.4)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from ..kernel import JsonObject
from .api import CHARTER_TOOLS, Confinement, ConfinementPolicy

MAX_INPUTS = 29  # rule 5 has 1 + 2 x (workspace + inputs + org) conditions; kiro validates a policy of 64 or more separately (A7)
_ESCAPES = {"[": "[[]", "]": "[]]", "*": "[*]", "?": "[?]"}  # the characters of a glob class that a literal path may hold
_EXTGLOB = ("+", "@", "!")  # an opener when followed by "("; kiro's matcher runs with noext, but no probe ran them (A5)
_PROTECTED_NAMES = (".kiro", "AGENTS.md", ".git", ".vscode")


def _literal(path: str) -> str:
    """The pattern that matches exactly ``path``: ``[ ] * ?`` become one-character classes, everything else (spaces too) is kept."""
    return "".join(_ESCAPES.get(c, c) for c in path)


def _shown(text: str) -> str:
    """``text`` on one line: a control character is written ``\\xNN``."""
    return "".join(_hex(c) if _is_control(c) else c for c in text)


def _is_control(char: str) -> bool:
    return ord(char) < 0x20 or ord(char) == 0x7F


def _hex(char: str) -> str:
    return f"\\x{ord(char):02x}"


def _path_problem(path: str) -> str | None:
    """Why kiro's permission patterns cannot match ``path`` literally (so an agent with it cannot be confined), or ``None``."""
    for index, char in enumerate(path):
        refused = _hex(char) if _is_control(char) else None
        if char in "{}\\":
            refused = char
        elif char in _EXTGLOB and path[index + 1 : index + 2] == "(":
            refused = char + "("
        if refused is not None:
            return (
                f'the path {_shown(path)} contains "{refused}", which kiro-cli\'s permission patterns cannot match literally, '
                "so this agent's access cannot be confined; rename it"
            )
    return None


def _selector(granted: frozenset[str]) -> tuple[str, ...]:
    """``@hirearchy``, then the kiro tags of the grant in a fixed order (the two web tools are the one tag ``web``)."""
    tags = ["@hirearchy", *(t for t in ("read", "write", "shell") if t in granted)]
    if {"web_search", "web_fetch"} <= granted:
        tags.append("web")
    elif "web_fetch" in granted:
        tags.append("web_fetch")
    elif "web_search" in granted:
        tags.append("remote_web_search")
    return tuple(tags)


def _protected(workspace: str) -> list[str]:
    """The 14 patterns under which the workspace is never written (``workspace`` is already a literal)."""
    out: list[str] = []
    for name in _PROTECTED_NAMES:
        out += [f"{workspace}/{name}"]
        if name != "AGENTS.md":  # a file: its subtree would be empty
            out += [f"{workspace}/{name}/**"]
        out += [f"{workspace}/**/{name}"]
        if name != "AGENTS.md":
            out += [f"{workspace}/**/{name}/**"]
    return out


def _once(items: Iterable[Path]) -> list[Path]:
    return list(dict.fromkeys(items))


def _subtrees(bases: Iterable[Path]) -> list[str]:
    return list(dict.fromkeys(x for p in bases for x in (_literal(str(p)), _literal(str(p)) + "/**")))


class KiroConfinementPolicy(ConfinementPolicy):
    def file_confinement(
        self, org_root: Path, tools: Sequence[str], workspace: Path | None, inputs: Sequence[Path]
    ) -> Confinement:
        """The V3 ``tools`` selector and ``permissions.rules`` of this grant (design 4.2-4.4), verified against kiro-cli 2.33.0 / KAS 0.66.48.

        * ``read``: workspace, inputs and the organization, each with its subtree (the same list, as an ``exclude``, makes every other
          read a deny); a write-only agent reads nothing. ``write``: only under the workspace (nowhere without one), never the
          organization unless the workspace is inside it, and never ``.kiro``, ``AGENTS.md``, ``.git`` or ``.vscode`` in it.
        * ``shell`` and the web tools are plain allows; nothing else is exposed or approvable (no skill, no context, no other MCP server).
        * The first problem wins: tools, the organization, the workspace, the inputs in order, then their number. A workspace or input kiro
          cannot match literally is left out of the access.
        """
        problem: str | None = None
        granted: set[str] = set()
        for item in tools:
            if isinstance(item, str) and item in CHARTER_TOOLS:
                granted.add(item)
            elif problem is None:
                problem = (
                    f"the charter's tools name {item!r}, which is not one of {', '.join(CHARTER_TOOLS)} (exact, lowercase)"
                )
        org = Path(org_root).resolve()
        problem = problem or _path_problem(str(org))
        ws: Path | None = None
        if workspace is not None:
            candidate = Path(workspace).resolve()
            issue = _path_problem(str(candidate))
            problem, ws = (problem or issue), (candidate if issue is None else None)
        ins: list[Path] = []
        for given in inputs:
            candidate = Path(given).resolve()
            issue = _path_problem(str(candidate))
            problem = problem or issue
            if issue is None:
                ins.append(candidate)
        ins = _once(ins)
        can_read, can_write = "read" in granted, "write" in granted
        if can_read and len(ins) > MAX_INPUTS and problem is None:
            problem = (
                f"this agent has {len(ins)} inputs: kiro-cli compiles at most 63 path exclusions into one rule without a separate "
                f"validation step; give this agent at most {MAX_INPUTS} inputs (a common parent folder counts as one)"
            )

        read = tuple(_once(p for p in (ws, *ins, org) if p is not None)) if can_read else ()
        write = ws if can_write else None
        fs = can_read or can_write
        org_inside = ws is not None and (ws == org or org in ws.parents)
        reachable = _subtrees(read)
        wsl = _literal(str(ws)) if ws is not None else ""
        orgl = _subtrees([org])

        rules: list[JsonObject] = [{"capability": "mcp", "match": ["hirearchy/*"], "effect": "allow"}]
        if can_read:
            rules.append({"capability": "fs_read", "effect": "allow", "match": reachable})
        if write is not None:
            rules.append({"capability": "fs_write", "effect": "allow", "match": [f"{wsl}/**"]})
        if can_write and not org_inside:
            rules.append({"capability": "fs_write", "effect": "deny", "match": orgl})
        if fs:
            deny_read: JsonObject = {"capability": "fs_read", "effect": "deny", "match": ["/**"]}
            if reachable:
                deny_read["exclude"] = reachable
            deny_write: JsonObject = {"capability": "fs_write", "effect": "deny", "match": ["/**"]}
            if write is not None:
                deny_write["exclude"] = [f"{wsl}/**"]
            rules += [deny_read, deny_write]
        if write is not None:
            rules.append({"capability": "fs_write", "effect": "deny", "match": _protected(wsl)})
        if "shell" in granted:
            rules.append({"capability": "shell", "match": ["*"], "effect": "allow"})
        if "web_fetch" in granted:
            rules.append({"capability": "web_fetch", "match": ["*"], "effect": "allow"})
        if "web_search" in granted:
            rules.append({"capability": "web_search", "match": ["*"], "effect": "allow"})
        rules += [{"capability": "skill", "effect": "deny"}, {"capability": "context", "effect": "deny"}]
        return Confinement(_selector(frozenset(granted)), tuple(rules), read, write, problem)
