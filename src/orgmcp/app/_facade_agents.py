"""The registry of agents: existence, tree, charters, memory (agents).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

from ..kernel import NAME_RE, OrgError, RESERVED, ROOT, split_frontmatter


class AgentsMixin:
    """The registry of agents: existence, tree, charters, memory (agents)."""

    def exists(self, addr: str) -> bool:
        a = self.norm(addr)
        if a == ROOT:
            return True
        parts = a.split("/")
        if not all(NAME_RE.fullmatch(p) and p not in RESERVED for p in parts):
            return False
        return (self.dir(a) / "AGENT.md").is_file()

    def require(self, addr: str) -> str:
        a = self.norm(addr)
        if not self.exists(a):
            raise OrgError(f"no such agent: {a}")
        return a

    def children(self, addr: str) -> list[str]:
        a = self.norm(addr)
        d = self.dir(a)
        if not d.is_dir():
            return []
        return [
            self.child_addr(a, p.name)
            for p in sorted(d.iterdir())
            if p.is_dir() and NAME_RE.fullmatch(p.name) and p.name not in RESERVED and (p / "AGENT.md").is_file()
        ]

    def agents(self) -> list[str]:
        """Every agent except root, parents before children."""
        out, stack = [], list(reversed(self.children(ROOT)))
        while stack:
            a = stack.pop()
            out.append(a)
            stack.extend(reversed(self.children(a)))
        return out

    def subtree(self, addr: str) -> list[str]:
        out, stack = [], [self.norm(addr)]
        while stack:
            a = stack.pop()
            out.append(a)
            stack.extend(self.children(a))
        return out

    def charter(self, addr: str) -> tuple[dict, str]:
        a = self.norm(addr)
        if a == ROOT:
            return {"role": "human (root of the organization)"}, ""
        meta, body = split_frontmatter((self.dir(a) / "AGENT.md").read_text(encoding="utf-8"))
        return meta, body.strip()

    def memory(self, addr: str) -> str:
        p = self.dir(addr) / "MEMORY.md"
        return p.read_text(encoding="utf-8") if p.is_file() else ""
