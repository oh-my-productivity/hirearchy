"""``GuardedOrgFileReader``: reads files and directories where an agent may look."""

from __future__ import annotations

from pathlib import Path

from ..access import AccessScopes
from ..agents import AgentDirectory
from ..kernel import ROOT, OrgError, OrgLayout, inside, norm, word_count
from .api import OrgFileReader, OrgFileStore


class GuardedOrgFileReader(OrgFileReader):
    def __init__(self, layout: OrgLayout, store: OrgFileStore, agents: AgentDirectory, scopes: AccessScopes) -> None:
        self._layout = layout
        self._store = store
        self._agents = agents
        self._scopes = scopes

    def resolve_read(self, path: str, actor: str | None = None) -> Path:
        """Relative paths are relative to the org root. Absolute paths must be inside the organization or, for an agent,
        inside its workspace or inputs or the workspace of an agent in its subtree. Root reads the organization only."""
        root = self._layout.root
        p = self._store.resolve(root / path.lstrip("/")) if not Path(path).is_absolute() else self._store.resolve(Path(path))
        if inside(p, root):
            return p
        who = norm(actor) if actor else ROOT
        if who != ROOT and any(inside(p, b) for b in self._scopes.readable_roots(who)):
            return p
        if who == ROOT:
            raise OrgError("you can only read inside the organization")
        raise OrgError(
            "you can only read inside the organization (paths relative to the org root), or by absolute path inside "
            "your workspace, your read-only inputs, or the workspace of an agent in your team"
        )

    def read(self, path: str, actor: str | None = None) -> str:
        p = self.resolve_read(path or ".", self._agents.require(actor) if actor else None)
        kind = self._store.kind(p)
        if kind == "dir":
            names = sorted(n for n in self._store.entries(p) if not n.startswith("."))
            entries = [f"{n}/" if self._store.kind(p / n) == "dir" else n for n in names]
            return "\n".join(entries) or "(empty directory)"
        if kind != "file":
            raise OrgError(f"not found: {path} (relative paths are relative to the org root)")
        text = self._store.read_text(p, "replace")
        modified = self._store.modified(p)
        shown = p.relative_to(self._layout.root) if inside(p, self._layout.root) else p
        head = f"[{shown}: {word_count(text)} words, {text.count(chr(10))} lines, modified {modified:%H:%M:%S} UTC]\n"
        limit = 100_000
        return head + (text if len(text) <= limit else text[:limit] + f"\n... (truncated, {len(text)} chars total)")
