"""What every implementation of the agent tree shares: the name rules, the text of a charter and the two walks of the tree."""

from __future__ import annotations

from collections.abc import Callable

from ..kernel import NAME_RE, RESERVED, ROOT, JsonObject, OrgError, norm, split_frontmatter
from .api import AgentDirectory

ROOT_ROLE = "human (root of the organization)"


def valid_address(addr: str) -> bool:
    """Every part of the address is a valid name that is not reserved (``NAME_RE.fullmatch``: ``"ops\\n"`` is not a name)."""
    return all(NAME_RE.fullmatch(part) and part not in RESERVED for part in addr.split("/"))


def root_charter() -> tuple[JsonObject, str]:
    """The charter of root, which has no file: the human."""
    return {"role": ROOT_ROLE}, ""


def parse_charter(text: str) -> tuple[JsonObject, str]:
    """``(frontmatter, body stripped)`` of the text of an ``AGENT.md``."""
    meta, body = split_frontmatter(text)
    return meta, body.strip()


def walk_agents(children: Callable[[str], list[str]]) -> list[str]:
    """Every agent below root, each before its descendants, siblings in the order ``children`` gives them."""
    out, stack = [], list(reversed(children(ROOT)))
    while stack:
        a = stack.pop()
        out.append(a)
        stack.extend(reversed(children(a)))
    return out


def walk_subtree(addr: str, children: Callable[[str], list[str]]) -> list[str]:
    """``addr`` and everything below it: each before its descendants, the last child of a parent first."""
    out, stack = [], [norm(addr)]
    while stack:
        a = stack.pop()
        out.append(a)
        stack.extend(children(a))
    return out


class TreeDirectory(AgentDirectory):
    """The part of an agent directory that follows from ``exists`` and ``children``."""

    def require(self, addr: str) -> str:
        a = norm(addr)
        if not self.exists(a):
            raise OrgError(f"no such agent: {a}")
        return a

    def agents(self) -> list[str]:
        return walk_agents(self.children)

    def subtree(self, addr: str) -> list[str]:
        return walk_subtree(addr, self.children)
